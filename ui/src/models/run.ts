import { Temporal } from "temporal-polyfill";
import { currentLocale, distanceAbbr, distanceConvert, durationFormatter, parseUtcDateTime, type DistanceUnit } from "../utils";

export interface Weather {
    temp_c: number | null;
    apparent_temp_c: number | null;
    humidity_pct: number | null;
    rain_mm: number | null;
    cloud_cover_pct: number | null;
}

interface RunDTO {
    id: number;
    start_time: string;
    active_duration: number;
    calories: number | null;
    distance_millimeters: number;
    average_pace_seconds_per_meter: number;
    weather: Weather;
}


export interface Run extends Omit<RunDTO, "start_time" | "active_duration"> {
    start_time: Temporal.ZonedDateTime;
    active_duration: Temporal.Duration;
}

export interface RunStats {
    run: Run;
    date_str: string;
    dist_abbr: string;
    distance: number;
    duration_str: string;
}

export const toRun = (dto: RunDTO): Run => ({
    ...dto,
    start_time: parseUtcDateTime(dto.start_time)!,
    active_duration: Temporal.Duration.from(`PT${dto.active_duration}S`).round({ largestUnit: 'hour' })
})

export function toRunStats(run: Run, distUnit: DistanceUnit): RunStats {
    //const today = Temporal.Now.plainDateISO();
    //const daysTotal = goal.start_date.until(goal.end_date).days + 1;
    //const daysRemaining = today.until(goal.end_date).days;

    const distance = (v: number) => distanceConvert(v, "meters", distUnit);

    return {
        run: run,
        date_str: run.start_time.toLocaleString(currentLocale, { dateStyle: "full" }),
        dist_abbr: distanceAbbr(distUnit),
        distance: distanceConvert(run.distance_millimeters, "millimeters", distUnit),
        duration_str: durationFormatter.format(run.active_duration)
    }
};