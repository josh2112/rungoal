import json
import math
from collections.abc import Sequence

import httpx
from httpx_retries import RetryTransport
from sqlmodel import Session, select

from rungoal.utils import ProgressProtocol

from .models import CachedArea, Run, RunLocation, RunLocationWithBoundary

GRID_SIZE = 0.05


class BoundingBox:
    def __init__(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float):
        self.min_lat, self.min_lon, self.max_lat, self.max_lon = min_lat, min_lon, max_lat, max_lon

    @classmethod
    def from_json(cls, json_str: str) -> "BoundingBox":
        return BoundingBox(*json.loads(json_str))

    @classmethod
    def from_points(cls, points: Sequence[tuple[float, float]]) -> "BoundingBox":
        lats, lons = [p[0] for p in points], [p[1] for p in points]
        return BoundingBox(
            min_lat=min(lats), min_lon=min(lons), max_lat=max(lats), max_lon=max(lons)
        )

    @classmethod
    def from_run_location(cls, run_location: RunLocationWithBoundary) -> "BoundingBox":
        points = [p for poly in run_location.boundary for p in poly]
        return BoundingBox.from_points(points)

    def to_json(self) -> str:
        return json.dumps([self.min_lat, self.min_lon, self.max_lat, self.max_lon])

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon

    def intersects(self, other: "BoundingBox") -> bool:
        return (
            (self.min_lat < other.min_lat < self.max_lat)
            or (self.min_lat < other.max_lat < self.max_lat)
        ) and (
            (self.min_lon < other.min_lon < self.max_lon)
            or (self.min_lon < other.max_lon < self.max_lon)
        )


class OverpassClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_url", "https://overpass-api.de/api")
        kwargs.setdefault("transport", RetryTransport())
        kwargs.setdefault("timeout", httpx.Timeout(120.0, connect=30.0))
        kwargs.setdefault("headers", {"user-agent": "rungoal/1.0.0"})
        super().__init__(*args, **kwargs)

    def fetch_run_locations(self, bbox: BoundingBox) -> list[RunLocationWithBoundary]:
        query = f"""
            [out:json][bbox:{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon}];
            (
            way["leisure"~"^(park|nature_reserve|track)$"];
            relation["leisure"~"^(park|nature_reserve|track)$"];
            );
            out geom;
            """
        response = self.post("/interpreter", content=query)
        response.raise_for_status()

        return self.parse(response.json())

    def parse(self, content: dict) -> list[RunLocationWithBoundary]:
        run_locations = []
        for element in content.get("elements", []):
            tags = element.get("tags", {})
            if not (name := tags.get("name")):
                continue

            polys = []
            if element["type"] == "way" and "geometry" in element:
                polys.append([(node["lat"], node["lon"]) for node in element["geometry"]])
            elif element["type"] == "relation" and "members" in element:
                for member in element["members"]:
                    if member.get("role") == "outer" and "geometry" in member:
                        polys.append([(node["lat"], node["lon"]) for node in member["geometry"]])

            polys = [p for p in polys if len(p) > 2]
            if polys:
                run_locations.append(
                    RunLocationWithBoundary(
                        osm_id=f"{element['type'][0]}{element['id']}",
                        name=name,
                        boundary=polys,
                        boundary_text=json.dumps(polys),
                    )
                )
        return run_locations


def is_point_in_poly(point: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(poly) - 1
    x, y = point
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[j]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside


def count_trackpoints_inside(run: Run, run_location: RunLocationWithBoundary):
    # Raycast each trackpoint on each polygon,
    # counting the trackpoints that are inside one of the polygons.
    cnt = 0
    for tp in run.track_points:
        if any(is_point_in_poly((tp.lat_deg, tp.lon_deg), poly) for poly in run_location.boundary):
            cnt += 1
    return cnt


def sync_locations(
    db: Session, client: OverpassClient, progress: ProgressProtocol, runs: Sequence[Run]
):
    task = "Syncing run locations"

    progress.start_task(task, total=len(runs))

    # Load the bounding boxes previously searched
    cached_areas = [BoundingBox.from_json(ca.bbox_text) for ca in db.exec(select(CachedArea)).all()]
    for run in runs:
        # Is any point in the run outside these areas?
        all_contained = len(cached_areas) > 0
        for tp in run.track_points:
            if not any(box.contains(tp.lat_deg, tp.lon_deg) for box in cached_areas):
                all_contained = False
                break

        if not all_contained:
            # Get the run's quantized bounding box
            # TODO: This will have problems if a run crosses the international date line :-/
            lats, lons = (
                [tp.lat_deg for tp in run.track_points],
                [tp.lon_deg for tp in run.track_points],
            )
            search_bbox = BoundingBox(
                min_lat=math.floor(min(lats) / GRID_SIZE) * GRID_SIZE,
                min_lon=math.floor(min(lons) / GRID_SIZE) * GRID_SIZE,
                max_lat=math.ceil(max(lats) / GRID_SIZE) * GRID_SIZE,
                max_lon=math.ceil(max(lons) / GRID_SIZE) * GRID_SIZE,
            )

            # Fetch list of likely running places from OpenStreetMap. Exclude point features and those without names.
            run_locations = client.fetch_run_locations(search_bbox)

            existing_osm_ids = db.exec(select(RunLocation.osm_id)).all()

            # Store the ones we don't already have
            for rl in run_locations:
                if rl.osm_id not in existing_osm_ids:
                    db.add(RunLocation(**rl.model_dump()))

            cached_areas.append(search_bbox)

            db.add(CachedArea(bbox_text=search_bbox.to_json()))
            db.commit()

        run_locations = [
            RunLocationWithBoundary(**rl.model_dump(), boundary=json.loads(rl.boundary_text))
            for rl in db.exec(select(RunLocation)).all()
        ]

        possible_locations: list[RunLocationWithBoundary] = []
        run_bbox = BoundingBox.from_points([(tp.lat_deg, tp.lon_deg) for tp in run.track_points])

        for rl in run_locations:
            rl_bbox = BoundingBox.from_run_location(rl)
            if rl_bbox.intersects(run_bbox):
                possible_locations.append(rl)

        print(f"possible locations: {[rl.name for rl in possible_locations]}")

        if len(possible_locations) == 1:
            run.location_id = possible_locations[0].osm_id
        elif len(possible_locations) > 1:
            run.location_id = max(
                possible_locations,
                key=lambda rl: count_trackpoints_inside(run, rl),
            ).osm_id

        progress.advance(task)

    db.commit()
