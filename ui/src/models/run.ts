import { Temporal } from "temporal-polyfill";
import {
    distanceAbbr,
    distanceConvert,
    normalizeValues,
    parseUtcDateTime,
    type DistanceUnit,
    type Range,
} from "../utils";
import type { Settings } from "./misc";

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

interface RunLocation {
    osm_id: number;
    name: string;
}

interface RunDTO {
    id: string;
    start_time: string;
    utc_offset_seconds: number;
    active_duration: number;
    calories?: number;
    distance_millimeters: number;
    average_pace_seconds_per_meter: number;
    weather?: Weather;
    split_stats: RunSplitStats[];
    device_type?: "WATCH" | "PHONE";
    location?: RunLocation;
}

export interface Run extends Omit<RunDTO, "start_time" | "active_duration"> {
    start_time: Temporal.ZonedDateTime;
    active_duration: Temporal.Duration;
    distance: number;
    average_pace: Temporal.Duration;
}

export const toRun = (dto: RunDTO, distUnit: DistanceUnit): Run => ({
    ...dto,
    start_time: parseUtcDateTime(dto.start_time, dto.utc_offset_seconds)!,
    active_duration: Temporal.Duration.from(`PT${dto.active_duration}S`).round({
        largestUnit: "hour",
        smallestUnit: "second",
    }),
    distance: distanceConvert(dto.distance_millimeters, "millimeters", distUnit),
    average_pace: Temporal.Duration.from(
        `PT${Math.round(1.0 / distanceConvert(1.0 / dto.average_pace_seconds_per_meter, "meters", distUnit))}S`,
    ).round({
        largestUnit: "minute",
    }),
});

type NotableType =
    | "HOTTEST"
    | "COLDEST"
    | "WETTEST"
    | "EARLIEST"
    | "LATEST"
    | "LONGEST"
    | "FASTEST"
    | "MOST_EFFICIENT";

interface NotableRunsDTO {
    runs: Record<NotableType, RunDTO>;
}

export interface NotableRuns {
    runs: Record<NotableType, Run>;
}

export const toNotableRuns = (dto: NotableRunsDTO, distUnit: DistanceUnit): NotableRuns =>
    ({
        runs: Object.fromEntries(
            Object.entries(dto.runs).map(([type, run]) => [type, toRun(run, distUnit)]),
        ) as Record<NotableType, Run>,
    }) as NotableRuns;

export interface StatsRanges {
    efficiency?: Range;
}

export interface RunStats {
    run: Run;
    distAbbr: string;
    name: string;
    weatherIcon?: string;
    weatherIconColor?: string;
    deviceTypeIcon?: string;
    normalizedSplitEfficiencies: number[];
    includeYearInDate: boolean;
}

const runName = (hour: number) => {
    if (hour < 11) return "Morning Run";
    if (hour < 14) return "Midday Run";
    if (hour < 17) return "Afternoon Run";
    return "Evening Run";
};

const weatherIcon = (wx?: Weather) => {
    if (!wx) return undefined;

    const r = wx.rain_mm;
    if (r !== undefined) {
        if (r > 2.5) return "bi-cloud-rain-fill";
        if (r > 0) return "bi-cloud-drizzle-fill";
    }

    const c = wx.cloud_cover_pct;
    if (c !== undefined) {
        if (c > 75) return "bi-clouds-fill";
        if (c > 50) return "bi-cloud-fill";
        if (c > 25) return "bi-cloud-sun-fill";
        return "bi-sun-fill";
    }
};

const weatherIconColor = (wx?: Weather) => {
    if (!wx) return undefined;
    const r = wx?.rain_mm ?? 0;
    const c = wx?.cloud_cover_pct ?? -1;

    if (r > 0) return "dodgerblue";
    if (c > 25) return "gray";
    if (c >= 0) return "gold";
};

const deviceTypeIcon = (deviceType?: string) => {
    if (deviceType == "WATCH") return "bi-watch";
    else if (deviceType == "PHONE") return "bi-phone";
};

const currentYear = Temporal.Now.plainDateISO().year;

export function toRunStats(run: Run, settings: Settings, efficiencyRange?: Range): RunStats {
    return {
        run: run,
        distAbbr: distanceAbbr(settings.distance_unit),
        name: runName(run.start_time.hour),
        weatherIcon: weatherIcon(run.weather),
        weatherIconColor: weatherIconColor(run.weather),
        deviceTypeIcon: deviceTypeIcon(run.device_type),
        normalizedSplitEfficiencies: efficiencyRange
            ? normalizeValues(
                  run.split_stats.map((ss) => ss.efficiency),
                  efficiencyRange,
              )
            : [],
        includeYearInDate: run.start_time.year < currentYear,
    } as RunStats;
}
