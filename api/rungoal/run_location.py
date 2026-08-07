import math
from collections.abc import Sequence

import httpx
from httpx_retries import RetryTransport
from sqlmodel import Session, select

from .geometry import BoundingBox, MultiPolygon
from .models import CachedArea, Run, RunLocation, RunLocationWithBoundary
from .utils import ProgressProtocol

GRID_SIZE = 0.05


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

            boundary = MultiPolygon([p for p in polys if len(p) > 2])
            if boundary.polygons:
                run_locations.append(
                    RunLocationWithBoundary(
                        osm_id=f"{element['type'][0]}{element['id']}",
                        name=name,
                        boundary=boundary,
                        boundary_text=boundary.to_wkt(),
                    )
                )
        return run_locations


def sync_locations(
    db: Session, client: OverpassClient, progress: ProgressProtocol, runs: Sequence[Run]
):
    task = "Syncing run locations"

    progress.start_task(task, total=len(runs))

    # Load the bounding boxes previously searched
    cached_areas = [BoundingBox.from_wkt(ca.bbox_text) for ca in db.exec(select(CachedArea)).all()]
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

            db.add(CachedArea(bbox_text=search_bbox.to_wkt()))
            db.commit()

        run_locations = [
            RunLocationWithBoundary(
                **rl.model_dump(), boundary=MultiPolygon.from_wkt(rl.boundary_text)
            )
            for rl in db.exec(select(RunLocation)).all()
        ]

        possible_locations: list[RunLocationWithBoundary] = []
        run_bbox = BoundingBox.from_points([(tp.lat_deg, tp.lon_deg) for tp in run.track_points])

        for rl in run_locations:
            points = [p for poly in rl.boundary.polygons for p in poly]
            rl_bbox = BoundingBox.from_points(points)
            if rl_bbox.intersects(run_bbox):
                possible_locations.append(rl)

        if len(possible_locations) == 1:
            run.location_id = possible_locations[0].osm_id
        elif len(possible_locations) > 1:
            trackpoints = [(tp.lat_deg, tp.lon_deg) for tp in run.track_points]
            location = max(
                possible_locations,
                key=lambda loc: loc.boundary.count_points_inside(trackpoints),
            )
            run.location_id = location.osm_id
        else:
            print("NO location determined for run", run.start_time)

        progress.advance(task)

    db.commit()
