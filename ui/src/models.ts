import { Temporal } from "temporal-polyfill";
import type { DistanceUnit } from "./conversion";

const parseUtcDateTime = (str: string): Temporal.ZonedDateTime => Temporal.Instant.from(str).toZonedDateTimeISO("UTC");

export interface ErrorResponse {
    title: string;
    detail: string;
    source: string;
}

export interface User {
    name: string;
    email: string;
    avatar_uri: string;
    is_onboarded: boolean;
}

export interface Settings {
    distance_unit: DistanceUnit
}

interface SyncStateDTO {
    is_syncing: boolean;
    tasks: {
        task: string;
        value: number;
        total: number | null;
    }[];
    synced_from?: string;
    synced_to?: string;
}

export interface SyncState extends Omit<SyncStateDTO, "synced_from" | "synced_to"> {
    synced_from?: Temporal.ZonedDateTime;
    synced_to?: Temporal.ZonedDateTime;
}

export const toSyncState = (dto: SyncStateDTO): SyncState => ({
    ...dto,
    synced_from: dto.synced_from ? parseUtcDateTime(dto.synced_from) : undefined,
    synced_to: dto.synced_from ? parseUtcDateTime(dto.synced_from) : undefined,
})

interface GoalDTO {
    id: number;
    distance_meters: number;
    start_date: string;
    end_date: string;
    current_distance_meters: number;
}

export interface Goal extends Omit<GoalDTO, "start_date" | "end_date"> {
    start_date: Temporal.PlainDate;
    end_date: Temporal.PlainDate;
}

export const toGoal = (dto: GoalDTO): Goal => ({
    ...dto,
    start_date: Temporal.PlainDate.from(dto.start_date),
    end_date: Temporal.PlainDate.from(dto.end_date)
    // TODO: Cclulate & 8insert stats here
})

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
    end_time: string;
    calories: number | null;
    distance_millimeters: number | null;
    average_pace_seconds_per_meter: number | null;
    weather: Weather;
}


export interface Run extends Omit<RunDTO, "start_time" | "end_time"> {
    start_time: Temporal.ZonedDateTime;
    end_time: Temporal.ZonedDateTime;
}

export const toRun = (dto: RunDTO): Run => ({
    ...dto,
    start_time: parseUtcDateTime(dto.start_time)!,
    end_time: parseUtcDateTime(dto.end_time)!
})