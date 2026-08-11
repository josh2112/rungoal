import re
from collections.abc import Sequence
from dataclasses import dataclass

GRID_SIZE = 0.05


@dataclass
class LatLon:
    lat: float
    lon: float


class MultiPolygon:
    def __init__(self, points: list[list[LatLon]]):
        self.polygons = points

    def contains_point(self, p: LatLon) -> bool:
        for poly in self.polygons:
            inside = False
            j = len(poly) - 1

            for i in range(len(poly)):
                lat1, lon1 = poly[i].lat, poly[i].lon
                lat2, lon2 = poly[j].lat, poly[j].lon

                if ((lon1 > p.lon) != (lon2 > p.lon)) and (
                    p.lat < (lat2 - lat1) * (p.lon - lon1) / (lon2 - lon1) + lat1
                ):
                    inside = not inside

                j = i

            if inside:
                return True

        return False

    def count_points_inside(self, points: Sequence[LatLon]):
        return sum(1 for p in points if self.contains_point(p))

    @classmethod
    def from_wkt(cls, wkt_string: str):
        if "EMPTY" in wkt_string:
            return MultiPolygon([])

        polygons: list[list[LatLon]] = []
        for ring_str in re.findall(r"\(([^()]+)\)", wkt_string):
            ring: list[LatLon] = []
            for pair in ring_str.split(","):
                parts = pair.strip().split()
                ring.append(LatLon(float(parts[1]), float(parts[0])))
            polygons.append(ring)

        return MultiPolygon(polygons)

    def to_wkt(self) -> str:
        if not self.polygons:
            return "MULTIPOLYGON EMPTY"

        wkt_polygons = [
            f"(({', '.join(f'{p.lon} {p.lat}' for p in poly)}))" for poly in self.polygons
        ]
        return f"MULTIPOLYGON ({', '.join(wkt_polygons)})"


class BoundingBox:
    def __init__(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float):
        self.min_lat, self.min_lon, self.max_lat, self.max_lon = min_lat, min_lon, max_lat, max_lon

    @classmethod
    def from_points(cls, points: Sequence[LatLon]) -> "BoundingBox":
        lats, lons = [p.lat for p in points], [p.lon for p in points]
        return BoundingBox(
            min_lat=min(lats), min_lon=min(lons), max_lat=max(lats), max_lon=max(lons)
        )

    @classmethod
    def from_wkt(cls, wkt_string: str) -> "BoundingBox":
        ring_match = re.search(r"\(([^()]+)\)", wkt_string)

        if "EMPTY" in wkt_string or not ring_match:
            return BoundingBox(0, 0, 0, 0)

        lats, lons = [], []
        for pair in ring_match.group(1).split(","):
            lon_str, lat_str = pair.strip().split()
            lons.append(float(lon_str))
            lats.append(float(lat_str))

        return BoundingBox(min(lats), min(lons), max(lats), max(lons))

    def to_wkt(self) -> str:
        return (
            f"POLYGON (({self.min_lon} {self.min_lat}, "
            f"{self.max_lon} {self.min_lat}, "
            f"{self.max_lon} {self.max_lat}, "
            f"{self.min_lon} {self.max_lat}, "
            f"{self.min_lon} {self.min_lat}))"
        )

    def contains(self, position: LatLon) -> bool:
        return (
            self.min_lat <= position.lat <= self.max_lat
            and self.min_lon <= position.lon <= self.max_lon
        )

    def intersects(self, other: "BoundingBox") -> bool:
        lat_ix = (self.min_lat <= other.max_lat) and (self.max_lat >= other.min_lat)
        lon_ix = (self.min_lon <= other.max_lon) and (self.max_lon >= other.min_lon)
        return lat_ix and lon_ix

    def __str__(self):
        return f"{self.min_lat}..{self.max_lat}, {self.min_lon}..{self.max_lon}"
