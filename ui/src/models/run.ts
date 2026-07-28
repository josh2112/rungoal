import { Temporal } from "temporal-polyfill";
import { distanceConvert, parseUtcDateTime, type DistanceUnit } from "../utils";

export interface Weather {
    temp_c?: number;
    apparent_temp_c?: number;
    humidity_pct?: number;
    rain_mm?: number;
    cloud_cover_pct?: number;
}

export interface RunSplitStats {
    split_secs: number;
    dist_meters: number;
    gad_meters: number;
    hr_avg?: number;
    efficiency?: number;
}

interface RunDTO {
    id: number;
    start_time: string;
    active_duration: number;
    calories?: number;
    distance_millimeters: number;
    average_pace_seconds_per_meter: number;
    weather?: Weather;
    split_stats: RunSplitStats[];
    device_type?: "WATCH" | "PHONE";
}

export interface Run extends Omit<RunDTO, "start_time" | "active_duration"> {
    start_time: Temporal.ZonedDateTime;
    active_duration: Temporal.Duration;
    distance: number;
    average_pace: Temporal.Duration;
}

export const toRun = (dto: RunDTO, distUnit: DistanceUnit): Run => ({
    ...dto,
    start_time: parseUtcDateTime(dto.start_time)!,
    active_duration: Temporal.Duration.from(`PT${dto.active_duration}S`).round({
        largestUnit: "hour",
        smallestUnit: "second",
    }),
    distance: distanceConvert(dto.distance_millimeters, "millimeters", distUnit),
    average_pace: Temporal.Duration.from(
        `PT${Math.round(
            1.0 / distanceConvert(1.0 / dto.average_pace_seconds_per_meter, "meters", distUnit),
        )}S`,
    ).round({
        largestUnit: "minute",
    }),
});

interface Range {
    min: number;
    max: number;
    range: number;
}

export interface StatsRanges {
    efficiency?: Range;
}
