export interface ErrorResponse {
    title: string;
    detail: string;
    source: string;
}

export interface User {
    name: string;
    email: string;
    avatar_uri: string;
}

export interface SyncState {
    is_complete: boolean;
    tasks: {
        task: string;
        value: number;
        total: number | null;
    }[];
}
