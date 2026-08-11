<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useSession } from "../stores/session";
import { currentLocale, durationFormatter, formatDec } from "../utils";

import { useRoute } from "vue-router";
import EfficiencyBar from "../components/EfficiencyBar.vue";
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

const stats = computed(() => toRunStats(run.value, session.settings));

onMounted(() => (navbarState.title = stats.value.name));
</script>

<template>
    <div class="container mt-3">
        <div class="d-flex justify-content-between">
            <h5>{{ stats.name }}</h5>
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
                    <EfficiencyBar
                        v-if="session.statsRanges.efficiency"
                        class="me-3"
                        :efficiency-range="session.statsRanges.efficiency"
                        :split-stats="stats.run.split_stats"
                    />
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
