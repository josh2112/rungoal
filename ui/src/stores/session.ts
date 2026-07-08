import { fetchEventSource } from "@microsoft/fetch-event-source";
import { defineStore } from "pinia";
import { onMounted, ref } from "vue";
import type { Run, SyncState, User } from "../models";
import { useApi } from "./api";

export const useSession = defineStore("session", () => {
    const api = useApi();

    const user = ref<User>();
    const syncState = ref<SyncState>();

    const runs = ref<Run[]>([]);

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
        syncState.value = undefined;
        runs.value = [];
        user.value = undefined;
    }

    async function getMe() {
        user.value = (await api.get("/user/me")).data;
        updateSyncState();
    }

    async function updateSyncState() {
        syncState.value = (await api.get("/sync/status")).data as SyncState;
        if (syncState.value.is_syncing) {
            streamSyncEvents();
        }
    }

    async function startSync(from?: Date, to?: Date, include_runtracker: boolean = false) {
        await api.post("/sync", {
            from: from?.toISOString(),
            to: to?.toISOString(),
            include_runtracker
        });
        streamSyncEvents();
    }

    function streamSyncEvents() {
        fetchEventSource(api.syncEventStreamUrl, {
            headers: {
                Authorization: `Bearer ${api.accessToken}`,
            },
            onmessage(msg) {
                syncState.value = JSON.parse(msg.data);
                if (!syncState.value!.is_syncing) {
                    console.log(`Sync complete: ${syncState.value?.synced_from} -> ${syncState.value?.synced_to}`)

                }
            },
            onerror(err) {
                console.error("Error in sync event source:", err);
            }
        });
    }

    async function getRuns(from: Date, to: Date) {
        let newRuns = (await api.get("/runs", {
            params: {
                from: from?.toISOString(),
                to: to?.toISOString(),
            }
        })).data as Run[];

        // Lump all runs rogether and remove dupes
        const dates = new Set<Date>();
        newRuns = newRuns.concat(runs.value).filter(r => {
            if (dates.has(r.start_time)) {
                return false;
            }
            dates.add(r.start_time);
            return true;
        });

        newRuns.sort((a: Run, b: Run) => {
            return b.start_time.getTime() - a.start_time.getTime()
        });

        runs.value = newRuns;
    }

    return { user, runs, logIn, logOut, startSync, syncState, getRuns };
});
