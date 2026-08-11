import xml.etree.ElementTree as ET


def get_subel_text(el: ET.Element, name: str) -> str | None:
    text = subel.text if (subel := el.find(f"./tcx:{name}", ns)) is not None else None
    return text or None


FILENAME = "../tcx/1119963355120964920.tcx"
# FILENAME = "../tcx/7189662828809116472.tcx"
FILENAME = "../tcx/4934410547619668136.tcx"

ns = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}


def get_gaps(trackpoints, path):
    last_idx = 0
    gaps = []
    for i, tp in enumerate(trackpoints):
        if get_subel_text(tp, path):
            if last_idx < i - 1:
                gaps.append((last_idx + 1, i - 1))
            last_idx = i
    return gaps


with open(FILENAME, "r") as f:
    trackpoints = ET.fromstring(f.read()).findall(".//tcx:Trackpoint", ns)

dist_gaps = get_gaps(trackpoints, "DistanceMeters")
alt_gaps = get_gaps(trackpoints, "AltitudeMeters")
hr_gaps = get_gaps(trackpoints, "HeartRateBpm/tcx:Value")

for g in ((hr_gaps, "hr"),):  # (dist_gaps, "dist"), (alt_gaps, "alt ")):
    print(g[1], sorted(x[1] - x[0] + 1 for x in g[0]))
