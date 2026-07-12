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

        settings.value = { distance_unit: "miles" } as Settings; // TODO: distance unit from Google Health settings?

        if (user.value?.is_onboarded === true) {
            await getGoals();

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
            include_runtracker,
        });
        streamSyncEvents();
    }

    function streamSyncEvents() {
        const ctrl = new AbortController();

        fetchEventSource(api.syncEventStreamUrl, {
            headers: {
                Authorization: `Bearer ${api.accessToken}`,
            },
            signal: ctrl.signal,
            async onmessage(msg) {
                const state = toSyncState(JSON.parse(msg.data));
                syncState.value = state;
                if (!state.is_syncing && state.synced_from && state.synced_to) {
                    console.log(`Sync complete: ${state.synced_from} -> ${state.synced_to}`);
                    ctrl.abort();

                    // Auto-fetch the newly-synced runs (up to 4 weeks if this was a first-time sync).
                    let from = Temporal.Instant.from(state.synced_from).toZonedDateTimeISO("UTC");
                    const to = Temporal.Instant.from(state.synced_to).toZonedDateTimeISO("UTC");

                    if (from.until(to).days > SYNC_DAYS) {
                        from = to.subtract({ days: SYNC_DAYS });
                    }
                    getGoals();
                    getRuns(from, to);
                }
            },
            onerror(err) {
                console.error("Error in sync event source:", err);
            },
        });
    }

    async function getGoals() {
        goals.value = ((await api.get("/goals")).data as []).map((g) => toGoal(g));
    }

    async function getRuns(from: Temporal.ZonedDateTime, to: Temporal.ZonedDateTime) {
        console.log(`Fetching runs from ${from.toString()} to ${to.toString()}`);
        let newRuns = (
            (
                await api.get("/runs", {
                    params: {
                        from: from.toString({ timeZoneName: "never" }),
                        to: to.toString({ timeZoneName: "never" }),
                    },
                })
            ).data as []
        ).map((r) => toRun(r));

        // Lump all runs rogether and remove dupes
        const ids = new Set<number>();
        newRuns = newRuns.concat(runs.value).filter((r) => {
            if (ids.has(r.id)) {
                return false;
            }
            ids.add(r.id);
            return true;
        });

        newRuns.sort((a: Run, b: Run) => Temporal.Instant.compare(b.start_time, a.start_time));
        runs.value = newRuns;
    }

    return {
        user,
        settings,
        runs,
        goals,
        logIn,
        logOut,
        startSync,
        syncState,
        getRuns,
    };
});
