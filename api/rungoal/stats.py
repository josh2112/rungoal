from typing import cast

from sqlmodel import Session, col, select

from .models import RunSplitStats, TrackPoint


class StatsCalcException(Exception):
    pass


N = 5


def _identify_gaps(is_gap: list[bool], values: list[float | int | None]):
    # Mark is_gap[x] = True for any gap of size N or larger values
    gap_start, gap_count = 0, 0
    for i, v in enumerate(values):
        if v is None:
            if not gap_count:
                gap_start = i
            gap_count += 1
        else:
            if gap_count >= N:
                for j in range(gap_start, i):
                    is_gap[j] = True
            gap_count = 0

    if gap_count >= N:
        for j in range(gap_start, len(values)):
            is_gap[j] = True


def _trim_boundary_nulls(group: list[TrackPoint], values: list[tuple[float | int | None, ...]]):
    first_idx = next(i for i, v in enumerate(values) if all(x is not None for x in v))
    last_idx = len(values) - next(
        i for i, v in enumerate(reversed(values)) if all(x is not None for x in v)
    )
    return group[first_idx:last_idx]


def calc_split_stats(db: Session, run_id: int, split_secs: int) -> list[RunSplitStats]:
    trackpoints = db.exec(
        select(TrackPoint).where(TrackPoint.run_id == run_id).order_by(col(TrackPoint.elapsed_secs))
    ).all()

    # Detach trackpoint instances from the DB. When we extrapolate values later, we don't want to commit those changes
    # back!
    for tp in trackpoints:
        db.expunge(tp)

    # Flag gaps of size N or larger in distance or heart rate by marking them in is_gap
    is_gap = [False] * len(trackpoints)
    _identify_gaps(is_gap, [tp.distance_meters for tp in trackpoints])
    _identify_gaps(is_gap, [tp.heart_rate_bpm for tp in trackpoints])

    groups: list[list[TrackPoint]] = []
    group: list[TrackPoint] = []

    for i, tp in enumerate(trackpoints):
        if is_gap[i]:
            if group:
                groups.append(group)
                group = []
            continue

        if group and tp.elapsed_secs - group[-1].elapsed_secs - 1 > N:
            groups.append(group)
            group = []

        group.append(tp)

    if group:
        groups.append(group)

    interpolated_groups = []
    for group in groups:
        group = _trim_boundary_nulls(
            group, [(tp.distance_meters, tp.heart_rate_bpm) for tp in group]
        )

        if len(group) < 30:
            # This split is not large enough to consider
            continue

        last_hr, last_dist = 0, 0
        for i, tp in enumerate(group):
            if tp.heart_rate_bpm:
                if i - last_hr > 1:
                    gap_size = i - last_hr
                    start = cast(int, group[last_hr].heart_rate_bpm)
                    delta = cast(int, tp.heart_rate_bpm) - start
                    for j in range(last_hr + 1, i):
                        group[j].heart_rate_bpm = round(start + (j - last_hr) / gap_size * delta)
                last_hr = i
            if tp.distance_meters:
                if i - last_dist > 1:
                    # Since distance and altitude are always recorded together, interpolate them together.
                    gap_size = i - last_dist
                    start_dist = cast(int, group[last_dist].distance_meters)
                    delta_dist = cast(int, tp.distance_meters) - start_dist
                    start_alt = cast(int, group[last_dist].alt_meters)
                    delta_alt = cast(int, tp.alt_meters) - start_alt
                    for j in range(last_dist + 1, i):
                        group[j].distance_meters = round(
                            start_dist + (j - last_dist) / gap_size * delta_dist
                        )
                        group[j].alt_meters = round(
                            start_alt + (j - last_dist) / gap_size * delta_alt
                        )

                last_dist = i

        interpolated_groups.append(group)

    # Break the active periods into splits of around [split_secs] seconds each. Avoid small splits (< 1 min) by
    # appending them to the previous split.
    split_groups: list[list[TrackPoint]] = []
    for g in interpolated_groups:
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

    # Now do the stats!
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
