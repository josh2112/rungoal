import { defineStore } from "pinia";
import { onMounted, ref } from "vue";
import type { SyncState, User } from "../models";
import { useApi } from "./api";

export const useSession = defineStore("session", () => {
    const api = useApi();

    const user = ref<User | null>(null);

    onMounted(async () => {
        await getMe();
    });

    async function logIn(google_access_code?: string) {
        await api.post(
            `/auth/${google_access_code ? "google" : "dev"}`,
            google_access_code ? { google_access_code } : undefined,
        );

        getMe();
    }

    function logOut() {
        api.get("/auth/logout");
        api.accessToken = null;
        user.value = null;
    }

    async function getMe() {
        user.value = (await api.get("/user/me")).data;
    }

    async function getSyncStatus(): Promise<SyncState> {
        return (await api.get("/sync/status")).data as SyncState;
    }

    async function startSync() {
        await api.post("/sync");
    }

    return { user, logIn, logOut, getSyncStatus, startSync };
});
