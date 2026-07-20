import { fetchEventSource } from "@microsoft/fetch-event-source";
import { defineStore } from "pinia";
import { Temporal } from "temporal-polyfill";
import { onMounted, ref } from "vue";
import { syncSizeInDays } from "../consts";
import { toGoal, type Goal, type GoalCreate, type GoalDTO, type GoalUpdate } from "../models/goal";
import {
    toSyncState,
    type ErrorResponse,
    type Settings,
    type SyncParams,
    type SyncState,
    type User,
} from "../models/misc";
import { toRun, type Run } from "../models/run";
import { useApi } from "./api";

const DEV_NO_AUTO_SYNC = true;

export const useSession = defineStore("session", () => {
    const api = useApi();

    const user = ref<User>();
    const settings = ref<Settings>({ distance_unit: "miles" }); // TODO: distance unit from Google Health settings?
    const syncState = ref<SyncState>();
    const lastSynced = ref<number>();

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
        user.value = (await api.get("/user/me")).data as User;

        await updateSyncState();

        if (user.value!.is_onboarded) {
            await getGoals();

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
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        await api.post("/sync", {
            from: from?.toISOString(),
            to: to?.toISOString(),
            runtracker_timezone: include_runtracker ? timezone : undefined,
        } as SyncParams);

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

                if (!state.is_syncing) {
                    if (state.error) {
                        console.log("Sync error:", state.error);
                        api.errors.push(state.error);
                    } else {
                        console.log(`Sync complete: ${state.synced_from} -> ${state.synced_to}`);
                    }

                    ctrl.abort();
                    lastSynced.value = Date.now();

                    if (state.synced_from && state.synced_to) {
                        // Auto-fetch the newly-synced runs (up to 4 weeks if this was a first-time sync).
                        let from = Temporal.Instant.from(state.synced_from).toZonedDateTimeISO("UTC");
                        const to = Temporal.Instant.from(state.synced_to).toZonedDateTimeISO("UTC");

                        if (from.until(to).days > syncSizeInDays) {
                            from = to.subtract({ days: syncSizeInDays });
                        }

                        getGoals();
                        getRuns(from, to);
                    }
                }
            },
            onerror(err) {
                console.error("Sync error:", err);
                api.errors.push({ title: "Sync error", detail: err.message } as ErrorResponse);
                throw err;
            },
        });
    }

    function _set_goals(goalDTOs: GoalDTO[]) {
        goals.value = goalDTOs.map((g) => toGoal(g));
    }

    async function getGoals() {
        _set_goals((await api.get("/goals")).data as []);
    }

    async function addGoal(goal: GoalCreate) {
        const response = await api.post("/goals", {
            ...goal,
            start_date: goal.start_date.toString({ calendarName: "never" }),
            end_date: goal.end_date.toString({ calendarName: "never" }),
        });
        _set_goals(response.data as []);
    }

    async function updateGoal(goal: GoalUpdate) {
        const response = await api.patch(`/goals/${goal.id}`, {
            ...goal,
            start_date: goal.start_date.toString({ calendarName: "never" }),
            end_date: goal.end_date.toString({ calendarName: "never" }),
        });
        _set_goals(response.data as []);
    }

    async function deleteGoal(goal: Goal) {
        await api.delete(`/goals/${goal.id}`);
        goals.value.splice(goals.value.indexOf(goal), 1);
    }

    async function getRuns(from: Temporal.ZonedDateTime, to: Temporal.ZonedDateTime): Promise<boolean> {
        from = from.round({ smallestUnit: "second" });
        to = to.round({ smallestUnit: "second" });

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

        const gotRuns = newRuns.length > 0;

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

        return gotRuns;
    }

    // Finds the oldest run and fetches [syncSizeInDays] days of runs before that. Returns true if any runs were
    // fetched.
    async function getPreviousRuns(): Promise<boolean> {
        const toTimestamp =
            runs.value.length > 0
                ? runs.value.reduce((min, cur) =>
                    Temporal.ZonedDateTime.compare(cur.start_time, min.start_time) < 0 ? cur : min,
                ).start_time
                : Temporal.Now.zonedDateTimeISO("UTC");
        return await getRuns(toTimestamp.subtract({ days: syncSizeInDays }), toTimestamp);
    }

    return {
        user,
        settings,
        runs,
        goals,
        addGoal,
        updateGoal,
        deleteGoal,
        logIn,
        logOut,
        startSync,
        syncState,
        lastSynced,
        getRuns,
        getPreviousRuns,
    };
});
