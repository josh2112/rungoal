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

export interface SyncProgress {
    is_complete: boolean;
    progress: Record<string, number>;
}
