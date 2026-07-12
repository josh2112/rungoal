import { Temporal } from "temporal-polyfill";
import { parseUtcDateTime, type DistanceUnit } from "./utils";

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
    distance_unit: DistanceUnit;
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
    synced_to: dto.synced_to ? parseUtcDateTime(dto.synced_to) : undefined,
});
