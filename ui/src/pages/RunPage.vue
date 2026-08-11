<script setup lang="ts">
import tinygradient from "tinygradient";
import { computed, onMounted } from "vue";
import { useSession } from "../stores/session";
import { currentLocale, durationFormatter, formatDec } from "../utils";

import { useRoute } from "vue-router";
import { navbarState } from "../models/misc";
import { toRunStats } from "../models/run";

const route = useRoute();
const session = useSession();

const run = computed(
    () =>
        session.runs
            .concat(Object.values(session.notableRuns?.runs ?? {}))
            .find((r) => r.id == route.params.id)!,
);

const stats = computed(() =>
    toRunStats(run.value, session.settings, session.statRanges.efficiency),
);

onMounted(() => (navbarState.title = stats.value.name));

const redToGreen = tinygradient([
    { color: "#ff0000", pos: 0 },
    { color: "#ff8800", pos: 0.5 },
    { color: "#00ff00", pos: 1 },
]);
</script>

<template>
    <div class="container mt-3">
        <div class="d-flex justify-content-between">
            <h5 class="text-primary-emphasis">
                <RouterLink
                    :to="`/run/${session.runs.indexOf(run) + 1}`"
                    class="stretched-link text-decoration-none text-primary-emphasis"
                    >{{ stats.name }}
                </RouterLink>
            </h5>
            <h5 class="text-end">{{ formatDec(run.distance, 2) }} {{ stats.distAbbr }}</h5>
        </div>
        <div class="d-flex justify-content-between card-text">
            <div>
                <div>
                    {{
                        run.start_time.toLocaleString(currentLocale, {
                            year: stats.includeYearInDate ? "numeric" : undefined,
                            weekday: "long",
                            month: "long",
                            day: "numeric",
                            hour: "numeric",
                            minute: "numeric",
                        })
                    }}
                </div>
                <div v-if="run.location">{{ run.location.name }}</div>
                <div class="d-flex align-items-center mt-2">
                    <div
                        v-if="stats.normalizedSplitEfficiencies.length > 0"
                        class="eff-sq-container me-3"
                    >
                        <div
                            v-for="eff in stats.normalizedSplitEfficiencies"
                            class="eff-sq"
                            :style="{
                                backgroundColor: redToGreen.rgbAt(eff).toHexString(),
                            }"
                        />
                    </div>
                    <i
                        v-if="run.device_type == 'WATCH'"
                        class="bi me-3 text-primary-emphasis"
                        :class="stats.deviceTypeIcon"
                    ></i>
                    <i
                        class="bi"
                        :class="stats.weatherIcon"
                        :style="{ color: stats.weatherIconColor }"
                    ></i>
                </div>
            </div>
            <div class="text-end">
                <div>{{ durationFormatter(run.average_pace) }} min/{{ stats.distAbbr }}</div>
                <div>{{ durationFormatter(run.active_duration) }}</div>
                <div class="mt-1" v-if="run.calories">{{ run.calories }} cal</div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.eff-sq-container {
    display: flex;
    gap: 2px;
    border-radius: 5px;
    overflow: hidden;
}

.eff-sq {
    width: 10px;
    height: 10px;
    border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
