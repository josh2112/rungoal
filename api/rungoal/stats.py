from typing import cast

from sqlmodel import Session, col, select

from .models import RunSplitStats, TrackPoint


class StatsCalcException(Exception):
    pass


def calc_split_stats(db: Session, run_id: int, split_secs: int) -> list[RunSplitStats]:
    trackpoints = db.exec(
        select(TrackPoint).where(TrackPoint.run_id == run_id).order_by(col(TrackPoint.elapsed_secs))
    ).all()

    # Detach trackpoint instances from the DB. When we extrapolate values later, we don't want to commit those changes
    # back!
    for tp in trackpoints:
        db.expunge(tp)

    # First, characterize heart rate data. Either it will all be missing, or there will be gaps of no more than
    # 1 to 2 trackpoints which we can easily interpolate (heart rate continues to be tracked during a pause
    # apparently). If all missing, return immediately.
    # ** If we see a gap of more than 2, Fitbit has changed something again -- throw an exception so we can look at
    # it later.
    last_hr, largest_gap = -1, 0
    for i, tp in enumerate(trackpoints):
        if tp.heart_rate_bpm:
            if i - last_hr - 1 > 0:
                largest_gap = max(largest_gap, i - last_hr - 1)
            last_hr = i

    if last_hr == -1:
        return []
    elif largest_gap > 2:
        raise StatsCalcException("Gap of 3 or larger found in heart rate tracking!")

    # Next, we need to separate pauses from data hiccups by looking at distances (distance and altitude gaps always
    # go together). Gaps have been seen with sizes varying from 1 TP to 160 or more. If the gap is more than 5 TP
    # (about 10 seconds since data collection slows to once every 2 seconds during an auto-pause), start a new group;
    # we don't want stat splits extending over a pause.

    active_groups: list[list[TrackPoint]] = []
    group = []
    last_dist = -1
    for i, tp in enumerate(trackpoints):
        if tp.distance_meters:
            if i - last_dist - 1 > 5:
                active_groups.append(group)
                group = []
            group.append(tp)
            last_dist = i
    active_groups.append(group)

    # Elminate groups of 30 or less trackpoints between pauses. We were probably still stationary but GPS location
    # drifted.
    active_groups = [g for g in active_groups if len(g) > 30]

    # Next, extrapolate heart rates
    for group in active_groups:
        # The first and last few heart rates in this group may in fact be null. If so, set then to the first and last
        # valid heart rate.
        group[0].heart_rate_bpm = next(tp.heart_rate_bpm for tp in group if tp.heart_rate_bpm)
        group[-1].heart_rate_bpm = next(
            tp.heart_rate_bpm for tp in reversed(group) if tp.heart_rate_bpm
        )
        last_hr = 0
        for i, tp in enumerate(group):
            if tp.heart_rate_bpm:
                if i - last_hr > 1:
                    # We have a gap between last_dist[0]+1 and i-1.
                    gap_size = i - last_hr
                    start = cast(int, group[last_hr].heart_rate_bpm)
                    delta = cast(int, tp.heart_rate_bpm) - start
                    for j in range(last_hr + 1, i):
                        group[j].heart_rate_bpm = round(start + (j - last_hr) / gap_size * delta)

                last_hr = i

    # Break the active periods into splits of around [split_secs] seconds each. Avoid small splits (< 1 min) by
    # appending them to the previous split.
    split_groups: list[list[TrackPoint]] = []
    for g in active_groups:
        # Avoid small splits (< 1 min).
        i, i_prev = 0, 0
        while i < len(g):
            start = g[i].elapsed_secs
            i_prev = i
            i = next(
                (i for i, tp in enumerate(g) if tp.elapsed_secs - start > split_secs),
                len(g),
            )
            # If this would leave a small end split, just take the rest of the array
            if i < len(g) and g[-1].elapsed_secs - g[i].elapsed_secs < 60:
                i = len(g)
            split_groups.append(g[i_prev:i])

    split_stats: list[RunSplitStats] = []

    for group in split_groups:
        gad_split, dist_split = 0, 0
        for i in range(1, len(group)):
            # Distance
            d = cast(float, group[i].distance_meters) - cast(float, group[i - 1].distance_meters)
            # Grade (change in alt / change in distance)
            g = (
                0
                if not d
                else (cast(float, group[i].alt_meters) - cast(float, group[i - 1].alt_meters)) / d
            )
            # Discard super-steep outlier grades
            g = min(0.5, max(-0.5, g))
            # GAP Factor (using Minetti polynomial)
            gf = (((((155.4 * g - 30.4) * g - 43.3) * g + 46.3) * g + 19.5) * g + 3.6) / 3.6
            # Grade-adjusted distance
            dist_split += d
            gad_split += d * gf

        ngs_split = gad_split / (group[-1].elapsed_secs - group[0].elapsed_secs)

        hr_avg = sum(cast(int, tp.heart_rate_bpm) for tp in group) / len(group)

        # sec/min * m/sec / beats/min ==> m/beat ==> meters per heartbeat
        eff_split = 60 * ngs_split / hr_avg

        split_stats.append(
            RunSplitStats(
                run_id=run_id,
                start_secs=round(group[0].elapsed_secs),
                end_secs=round(group[-1].elapsed_secs),
                dist_meters=dist_split,
                gad_meters=gad_split,
                hr_avg=hr_avg,
                efficiency=eff_split,
            )
        )

    return split_stats
