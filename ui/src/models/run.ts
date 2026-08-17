import { wktToGeoJSON } from "betterknown";
import { type Polygon } from "geojson";
import { Temporal } from "temporal-polyfill";
import {
    distanceAbbr,
    distanceConvert,
    parseUtcDateTime,
    type DistanceUnit,
    type Range,
} from "../utils";

export interface Weather {
    temp_c?: number;
    apparent_temp_c?: number;
    humidity_pct?: number;
    rain_mm?: number;
    cloud_cover_pct?: number;
}

export interface RunSplitStats {
    start_secs: number;
    end_secs: number;
    dist_meters: number;
    gad_meters: number;
    hr_avg: number;
    efficiency: number;
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
    bbox_text?: string;
}

export interface Run extends Omit<RunDTO, "start_time" | "active_duration" | "bbox_text"> {
    start_time: Temporal.ZonedDateTime;
    active_duration: Temporal.Duration;
    distance: number;
    average_pace: Temporal.Duration;
    bbox?: [number, number, number, number] | undefined;
}

function bboxFromPolygonWKT(wkt: string | undefined): [number, number, number, number] | undefined {
    const poly = (wkt ? (wktToGeoJSON(wkt) ?? undefined) : undefined) as Polygon | undefined;
    if (!poly || !poly.coordinates?.[0]) return undefined;

    const boundary = poly.coordinates[0];

    const lons = boundary.map((c) => c[0]);
    const lats = boundary.map((c) => c[1]);

    return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
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
    bbox: bboxFromPolygonWKT(dto.bbox_text),
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
    avgEff?: number;
    paddedSplitStats: RunSplitStats[];
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

export function toRunStats(run: Run, dist_unit: DistanceUnit): RunStats {
    let avgEff: number | undefined = 0;
    let totalSecs = 0;
    let paddedSplitStats = [run.split_stats[0]];

    for (let i = 1; i < run.split_stats.length; ++i) {
        const split = run.split_stats[i];
        const time = split.end_secs - split.start_secs;
        totalSecs += time;
        avgEff += split.efficiency * time;

        const delta = split.start_secs - run.split_stats[i - 1].end_secs;
        if (delta > 1) {
            paddedSplitStats.push({
                start_secs: run.split_stats[i - 1].end_secs + 1,
                end_secs: split.start_secs - 1,
                dist_meters: 0,
                gad_meters: 0,
                hr_avg: 0,
                efficiency: -1,
            } as RunSplitStats);
        }
        paddedSplitStats.push(split);
    }
    avgEff = totalSecs > 0 ? avgEff / totalSecs : undefined;

    return {
        run: run,
        distAbbr: distanceAbbr(dist_unit),
        name: runName(run.start_time.hour),
        weatherIcon: weatherIcon(run.weather),
        weatherIconColor: weatherIconColor(run.weather),
        deviceTypeIcon: deviceTypeIcon(run.device_type),
        includeYearInDate: run.start_time.year < currentYear,
        paddedSplitStats,
        avgEff,
    } as RunStats;
}
