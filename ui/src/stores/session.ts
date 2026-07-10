import { fetchEventSource } from "@microsoft/fetch-event-source";
import { defineStore } from "pinia";
import { Temporal } from "temporal-polyfill";
import { onMounted, ref } from "vue";
import { toSyncState, type Settings, type SyncState, type User } from "../misc";
import { toGoal, type Goal } from "../models/goal";
import { toRun, type Run } from "../models/run";
import { useApi } from "./api";

const SYNC_DAYS = 28;
const DEV_NO_AUTO_SYNC = true;

export const useSession = defineStore("session", () => {
    const api = useApi();

    const user = ref<User>();
    const settings = ref<Settings>();
    const syncState = ref<SyncState>();

    const goals = ref<Goal[]>([]);
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
        await updateSyncState();

        settings.value = { distance_unit: "miles" } as Settings; // TODO

        if (user.value?.is_onboarded === true) {
            goals.value = ((await api.get("/goals")).data as []).map(g => toGoal(g));

            // If user is not onboarded yet, Account.vue will handle it. Otherwise, grab initial set of runs
            const to = Temporal.Now.zonedDateTimeISO("UTC");
            const from = to.subtract({ days: SYNC_DAYS });
            await getRuns(from, to);

            if (syncState.value?.is_syncing === false && (!import.meta.env.DEV || !DEV_NO_AUTO_SYNC)) {
                startSync();
            }
        }
    }

    async function updateSyncState() {
        syncState.value = toSyncState((await api.get("/sync/status")).data);
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
                const state = toSyncState(JSON.parse(msg.data));
                syncState.value = state;
                if (!state.is_syncing && state.synced_from && state.synced_to) {
                    console.log(`Sync complete: ${state.synced_from} -> ${state.synced_to}`)

                    // Auto-fetch the newly-synced runs (up to 4 weeks if this was a first-time sync).
                    let from = Temporal.Instant.from(state.synced_from).toZonedDateTimeISO("UTC");
                    const to = Temporal.Instant.from(state.synced_to).toZonedDateTimeISO("UTC");

                    if (from.until(to).days > SYNC_DAYS) {
                        from = to.subtract({ days: SYNC_DAYS });
                    }
                    getRuns(from, to);
                }
            },
            onerror(err) {
                console.error("Error in sync event source:", err);
            }
        });
    }

    async function getRuns(from: Temporal.ZonedDateTime, to: Temporal.ZonedDateTime) {
        let newRuns = ((await api.get("/runs", {
            params: {
                from: from.toString({ timeZoneName: 'never' }),
                to: to.toString({ timeZoneName: 'never' }),
            }
        })).data as []).map(r => toRun(r));

        // Lump all runs rogether and remove dupes
        const dates = new Set<Temporal.ZonedDateTime>();
        newRuns = newRuns.concat(runs.value).filter(r => {
            if (dates.has(r.start_time)) {
                return false;
            }
            dates.add(r.start_time);
            return true;
        });

        newRuns.sort((a: Run, b: Run) => Temporal.Instant.compare(b.start_time, a.start_time));
        runs.value = newRuns;
    }

    return { user, settings, runs, goals, logIn, logOut, startSync, syncState, getRuns };
});
