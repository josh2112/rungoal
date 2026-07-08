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

export interface SyncState {
    is_syncing: boolean;
    tasks: {
        task: string;
        value: number;
        total: number | null;
    }[];
    synced_from?: Date
    synced_to?: Date
}

export interface Weather {
    temp_c: number | null;
    apparent_temp_c: number | null;
    humidity_pct: number | null;
    rain_mm: number | null;
    cloud_cover_pct: number | null;
}

export interface Run {
    id: number;
    start_time: Date;
    end_time: Date;
    calories: number | null;
    distance_millimeters: number | null;
    average_pace_seconds_per_meter: number | null;
    weather: Weather;
}
