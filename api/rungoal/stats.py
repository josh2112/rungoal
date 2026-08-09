from sqlmodel import Session, col, select

from .models import RunSplitStats, TrackPoint


def calc_split_stats(db: Session, run_id: int, split_secs: int) -> list[RunSplitStats]:
    trackpoints = db.exec(
        select(TrackPoint).where(TrackPoint.run_id == run_id).order_by(col(TrackPoint.elapsed_secs))
    ).all()

    # Eliminate trackpoints that don't have all 3 metrics we need to calculate efficiency
    trackpoints = [tp for tp in trackpoints if tp.distance_meters and tp.alt_meters]

    # Divide the trackpoints into X-second-long splits
    markers, end_time = [], split_secs
    for i, tp in enumerate(trackpoints):
        if tp.elapsed_secs > end_time:
            markers.append(i)
            end_time += split_secs

    split_stats: list[RunSplitStats] = []

    start = 0
    for end in markers:
        # If we don't have enough trackpoints for this split (maybe a long pause?)
        # just combine it with the next
        if end - start < 30:
            continue

        gad_split, dist_split = 0, 0
        for i in range(start + 1, end + 1):
            # Distance
            d = trackpoints[i].distance_meters - trackpoints[i - 1].distance_meters
            # Grade (change in alt / change in distance)
            g = 0 if not d else (trackpoints[i].alt_meters - trackpoints[i - 1].alt_meters) / d
            # Discard super-steep outlier grades
            g = min(0.5, max(-0.5, g))
            # GAP Factor (using Minetti polynomial)
            gf = (((((155.4 * g - 30.4) * g - 43.3) * g + 46.3) * g + 19.5) * g + 3.6) / 3.6
            # Grade-adjusted distance
            dist_split += d
            gad_split += d * gf

        # We can't count on having heart rates for all trackpoints. I've seen at least one run where my Pixel Watch 3
        # only recorded heart rates for 1 out of every 2 or 3 trackpoints.
        hrs = [
            tp.heart_rate_bpm
            for tp in trackpoints[start + 1 : end + 1]
            if tp.heart_rate_bpm is not None
        ]
        hr_split = sum(hrs) / len(hrs) if hrs else None

        ngs_split = gad_split / (trackpoints[end].elapsed_secs - trackpoints[start].elapsed_secs)

        # sec/min * m/sec / beats/min ==> m/beat ==> meters per heartbeat
        eff_split = 60 * ngs_split / hr_split if hr_split else 0

        split_stats.append(
            RunSplitStats(
                run_id=run_id,
                split_secs=round(trackpoints[end].elapsed_secs),
                dist_meters=dist_split,
                gad_meters=gad_split,
                hr_avg=hr_split if hr_split else None,
                efficiency=eff_split if eff_split else None,
            )
        )

        start = end

    return split_stats
