import json
import math
from collections.abc import Sequence

import httpx
from sqlmodel import Session, select

from rungoal.utils import ProgressProtocol

from .models import CachedArea, Run, RunLocation, RunLocationWithBoundary

GRID_SIZE = 0.05


class BoundingBox:
    def __init__(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float):
        self.min_lat, self.min_lon, self.max_lat, self.max_lon = min_lat, min_lon, max_lat, max_lon

    @classmethod
    def from_json(cls, json_str: str):
        return BoundingBox(**json.loads(json_str))

    def to_json(self):
        return json.dumps([self.min_lat, self.min_lon, self.max_lat, self.max_lon])

    def contains(self, lat: float, lon: float):
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


class OverpassClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_url", "https://overpass-api.de/api/")  # "interpreter/"
        kwargs.setdefault("transport", httpx.HTTPTransport(retries=10))
        kwargs.setdefault("timeout", httpx.Timeout(120.0, connect=5.0))
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
            run_locations.append(
                RunLocationWithBoundary(
                    osm_id=f"{element['type'][0]}{element['id']}",
                    name=name,
                    boundary=polys,
                    boundary_text=json.dumps(polys),
                )
            )
        return run_locations


def sync_locations(
    db: Session, client: OverpassClient, progress: ProgressProtocol, runs: Sequence[Run]
):
    task = "Syncing run locations"

    progress.start_task(task, total=len(runs))

    for run in runs:
        # Load the bounding boxes previously searched
        cached_areas = [
            BoundingBox.from_json(ca.bbox_text) for ca in db.exec(select(CachedArea)).all()
        ]

        # Is any point in the run outside these areas?
        all_contained = True
        for tp in run.track_points:
            if not any(box.contains(tp.lat_deg, tp.lon_deg) for box in cached_areas):
                all_contained = False
                break

        if all_contained:
            # Get the run's quantized bounding box
            # TODO: This will have problems if a run crosses the international date line :-/
            lats, lons = (
                [tp.lat_deg for tp in run.track_points],
                [tp.lon_deg for tp in run.track_points],
            )
            bbox = BoundingBox(
                min_lat=math.floor(min(lats) / GRID_SIZE) * GRID_SIZE,
                min_lon=math.floor(min(lons) / GRID_SIZE) * GRID_SIZE,
                max_lat=math.ceil(max(lats) / GRID_SIZE) * GRID_SIZE,
                max_lon=math.ceil(max(lons) / GRID_SIZE) * GRID_SIZE,
            )

            # Fetch list of likely running places from OpenStreetMap. Exclude point features and those without names.
            run_locations = client.fetch_run_locations(bbox)

            existing_osm_ids = db.exec(select(RunLocation.osm_id)).all()

            # Store the ones we don't already have
            for rl in run_locations:
                if rl.osm_id not in existing_osm_ids:
                    db.add(RunLocation(**rl.model_dump()))

            db.add(CachedArea(bbox_text=bbox.to_json()))

        run_locations = [
            RunLocationWithBoundary(**rl.model_dump(), boundary=json.loads(rl.boundary_text))
            for rl in db.exec(select(RunLocation)).all()
        ]

        # TODO:
        # - We have the run, which is a polyline
        # - We have a list of run locations, each a list of polygons
        # - First pass:
        #   - Treat the run and each run location as a bigass bounding box.
        #   - Find the run locations whose bouding box overlaps the run bounding box
        # - Second pass:
        #   - For each run location in first pass, raycast on each trackpoint on each polygon,
        #     counting the trackpoints that are inside one of the polygons.
        #   - The run location with the most trackpoints inside wins.

        location = _spatial_index.locate_track(run.track_points)

        if location:
            run.location_id = location.osm_id
            db.add(run)

        progress.advance(task)

    db.commit()
