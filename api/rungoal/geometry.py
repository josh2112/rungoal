import re
from collections.abc import Sequence

GRID_SIZE = 0.05


class MultiPolygon:
    def __init__(self, points: list[list[tuple[float, float]]]):
        self.polygons = points

    def contains_point(self, point: tuple[float, float]) -> bool:
        for poly in self.polygons:
            inside = False
            j = len(poly) - 1
            lat, lon = point

            for i in range(len(poly)):
                lat1, lon1 = poly[i]
                lat2, lon2 = poly[j]

                if ((lon1 > lon) != (lon2 > lon)) and (
                    lat < (lat2 - lat1) * (lon - lon1) / (lon2 - lon1) + lat1
                ):
                    inside = not inside

                j = i

            if inside:
                return True

        return False

    def count_points_inside(self, points: list[tuple[float, float]]):
        return sum(1 for p in points if self.contains_point(p))

    @classmethod
    def from_wkt(cls, wkt_string: str):
        if "EMPTY" in wkt_string:
            return MultiPolygon([])

        polygons = []
        for ring_str in re.findall(r"\(([^()]+)\)", wkt_string):
            ring = []
            for pair in ring_str.split(","):
                parts = pair.strip().split()
                ring.append((float(parts[1]), float(parts[0])))
            polygons.append(ring)

        return MultiPolygon(polygons)

    def to_wkt(self) -> str:
        if not self.polygons:
            return "MULTIPOLYGON EMPTY"

        wkt_polygons = [
            f"(({', '.join(f'{lon} {lat}' for lat, lon in poly)}))" for poly in self.polygons
        ]
        return f"MULTIPOLYGON ({', '.join(wkt_polygons)})"


class BoundingBox:
    def __init__(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float):
        self.min_lat, self.min_lon, self.max_lat, self.max_lon = min_lat, min_lon, max_lat, max_lon

    @classmethod
    def from_points(cls, points: Sequence[tuple[float, float]]) -> "BoundingBox":
        lats, lons = [p[0] for p in points], [p[1] for p in points]
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

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon

    def intersects(self, other: "BoundingBox") -> bool:
        lat_ix = (self.min_lat <= other.max_lat) and (self.max_lat >= other.min_lat)
        lon_ix = (self.min_lon <= other.max_lon) and (self.max_lon >= other.min_lon)
        return lat_ix and lon_ix

    def __str__(self):
        return f"{self.min_lat}..{self.max_lat}, {self.min_lon}..{self.max_lon}"
