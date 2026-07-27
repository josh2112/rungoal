import { Temporal } from "temporal-polyfill";
import {
    currentLocale,
    distanceAbbr,
    distanceConvert,
    durationFormatter,
    parseUtcDateTime,
    type DistanceUnit,
} from "../utils";

export interface Weather {
    temp_c: number | null;
    apparent_temp_c: number | null;
    humidity_pct: number | null;
    rain_mm: number | null;
    cloud_cover_pct: number | null;
}

export interface RunSplitStats {
    split_secs: number;
    dist_meters: number;
    gad_meters: number;
    hr_avg: number | null;
    efficiency: number | null;
}

interface RunDTO {
    id: number;
    start_time: string;
    active_duration: number;
    calories: number | null;
    distance_millimeters: number;
    average_pace_seconds_per_meter: number;
    weather?: Weather;
    split_stats: RunSplitStats[];
    device_type: string;
}

export interface Run extends Omit<RunDTO, "start_time" | "active_duration"> {
    start_time: Temporal.ZonedDateTime;
    active_duration: Temporal.Duration;
}

interface RelativeSplitStats {
    efficiency?: number | undefined;
}

export interface RunStats {
    run: Run;
    date_str: string;
    dist_abbr: string;
    distance: number;
    duration_str: string;
    pace_str: string;
    relative_split_stats: RelativeSplitStats[];
}

export const toRun = (dto: RunDTO): Run => ({
    ...dto,
    start_time: parseUtcDateTime(dto.start_time)!,
    active_duration: Temporal.Duration.from(`PT${dto.active_duration}S`).round({
        largestUnit: "hour",
    }),
});

export function toRunStats(run: Run, statRanges: StatRanges, distUnit: DistanceUnit): RunStats {
    // s/m -> m/s -> mi/s -> s/mi
    const pace_per_min = Math.round(
        1.0 / distanceConvert(1.0 / run.average_pace_seconds_per_meter, "meters", distUnit),
    );
    const pace = Temporal.Duration.from(`PT${pace_per_min}S`).round({
        largestUnit: "minute",
    });

    const effRange = statRanges.efficiency
        ? statRanges.efficiency?.max - statRanges.efficiency?.min
        : undefined;

    const relativeStats: RelativeSplitStats[] = run.split_stats.map(
        (ss) =>
            ({
                efficiency:
                    ss.efficiency && effRange
                        ? (ss.efficiency - statRanges.efficiency!.min) / effRange
                        : undefined,
            }) as RelativeSplitStats,
    );

    return {
        run: run,
        date_str: run.start_time.toLocaleString(currentLocale, { dateStyle: "full" }),
        dist_abbr: distanceAbbr(distUnit),
        distance: distanceConvert(run.distance_millimeters, "millimeters", distUnit),
        duration_str: durationFormatter.format(
            run.active_duration.round({ smallestUnit: "second" }),
        ),
        pace_str: durationFormatter.format(pace),
        relative_split_stats: relativeStats,
    };
}

interface MinMax {
    min: number;
    max: number;
    span: number;
}

export interface StatRanges {
    efficiency?: MinMax;
}

export function calcStatRanges(runs: Run[]): StatRanges {
    const efficiency = runs.reduce(
        (acc, run) => {
            for (const stat of run.split_stats) {
                const val = stat.efficiency;

                // Filter out undefined, null, or NaN values
                if (val !== undefined && val !== null && !isNaN(val)) {
                    if (val < acc.min) acc.min = val;
                    if (val > acc.max) acc.max = val;
                }
            }
            return acc;
        },
        { min: Infinity, max: -Infinity },
    );

    return {
        efficiency:
            efficiency.min === Infinity
                ? undefined
                : {
                      min: efficiency.min,
                      max: efficiency.max,
                      span: efficiency.max - efficiency.min,
                  },
    } as StatRanges;
}
