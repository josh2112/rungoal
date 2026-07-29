import math
from typing import Sequence, cast

import osmnx as ox
from shapely import LineString, STRtree, box, unary_union, wkt
from sqlmodel import Session, select

from rungoal.utils import ProgressProtocol

from .models import CachedArea, Run, RunLocation, RunLocationWithBoundary, TrackPoint


class SpatialIndex:
    def __init__(self, run_locations: list[RunLocation]):
        self.run_locations = [
            RunLocationWithBoundary(**rl.model_dump(), boundary=wkt.loads(rl.boundary_text))
            for rl in run_locations
        ]
        self.tree = STRtree([rl.boundary for rl in self.run_locations])

    def add(self, run_location: RunLocation):
        self.run_locations.append(
            RunLocationWithBoundary(
                **run_location.model_dump(), boundary=wkt.loads(run_location.boundary_text)
            )
        )
        self.tree = STRtree([rl.boundary for rl in self.run_locations])

    def locate_track(self, trackpoints: list[TrackPoint]) -> RunLocationWithBoundary | None:
        track = LineString((tp.lon_deg, tp.lat_deg) for tp in trackpoints)
        matches = self.tree.query(track)
        matches_by_length = {
            rl.boundary.intersection(track).length: rl
            for i, rl in enumerate(self.run_locations)
            if i in matches and rl.boundary.intersects(track)
        }
        return matches_by_length[max(matches_by_length.keys())] if matches_by_length else None


_spatial_index: SpatialIndex | None = None

GRID_SIZE = 0.05


def sync_locations(db: Session, progress: ProgressProtocol, runs: Sequence[Run]):
    global _spatial_index
    if not _spatial_index:
        _spatial_index = SpatialIndex(list(db.exec(select(RunLocation)).all()))

    task = "Syncing run locations"

    progress.start_task(task, total=len(runs))

    for run in runs:
        # Get the run's quantized bounding box
        # This will have problems if a run crosses the international date line :-/
        bbox = box(
            math.floor(min(tp.lon_deg for tp in run.track_points) / GRID_SIZE) * GRID_SIZE,
            math.floor(min(tp.lat_deg for tp in run.track_points) / GRID_SIZE) * GRID_SIZE,
            math.ceil(max(tp.lon_deg for tp in run.track_points) / GRID_SIZE) * GRID_SIZE,
            math.ceil(max(tp.lat_deg for tp in run.track_points) / GRID_SIZE) * GRID_SIZE,
        )

        # Combine all previously-searched areas and get the bounds
        cached_areas = [wkt.loads(ca.bbox_text) for ca in db.exec(select(CachedArea)).all()]
        cached_area = unary_union(cached_areas) if cached_areas else box(0, 0, 0, 0)

        if not cached_area.contains(bbox):
            # Fetch list of likely running places from OpenStreetMap. Exclude point features and those without names.
            places = ox.features_from_polygon(
                bbox, {"leisure": ["park", "nature_reserve", "track"]}
            )
            places = places[places.geometry.type.isin(["Polygon"])]
            if "name" in places.columns:
                places = places[places["name"].notna()]
            else:
                places.iloc[0:0]

            existing_osm_ids = db.exec(select(RunLocation.osm_id)).all()

            for id_, row in places.iterrows():
                osm_id = cast(int, id_[1] if isinstance(id_, tuple) else id_)

                if osm_id not in existing_osm_ids:
                    run_location = RunLocation(
                        osm_id=osm_id, name=row["name"], boundary_text=row.geometry.wkt
                    )
                    db.add(run_location)
                    _spatial_index.add(run_location)

            db.add(CachedArea(bbox_text=bbox.wkt))

        location = _spatial_index.locate_track(run.track_points)

        if location:
            run.location_id = location.osm_id
            db.add(run)

        progress.advance(task)

    db.commit()
