<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useSession } from "../stores/session";
import { currentLocale, durationFormatter, formatDec, temperatureConvert } from "../utils";

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

const stats = computed(() => toRunStats(run.value, session.user!.distance_unit));

onMounted(() => (navbarState.title = stats.value.name));
</script>

<template>
    <div class="container mt-3">
        <div class="d-flex justify-content-between">
            <h5>{{ stats.name }}</h5>
            <h5 class="text-end">{{ formatDec(run.distance, 2) }} {{ stats.distAbbr }}</h5>
        </div>
        <div class="d-flex justify-content-between card-text">
            <div class="d-flex flex-column">
                <div>
                    {{
                        // Include year only if not current year
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
                <div v-if="run.location" class="mt-1">
                    <i class="bi bi-geo-alt-fill me-1 text-primary-emphasis" />
                    {{ run.location.name }}
                </div>
                <div class="mt-auto">
                    <div class="d-flex align-items-center mt-1">
                        <span v-if="stats.avgEff !== undefined" class="me-3"
                            ><strong>{{ formatDec(stats.avgEff, 2) }}</strong> m/hb
                        </span>
                        <EfficiencyBar
                            v-if="session.statsRanges.efficiency && stats.avgEff !== undefined"
                            class="me-3"
                            style="margin-top: 2px"
                            :efficiency-range="session.statsRanges.efficiency"
                            :split-stats="stats.paddedSplitStats"
                        />
                        <i
                            v-if="stats.deviceTypeIcon"
                            class="bi me-3 text-primary-emphasis"
                            :class="stats.deviceTypeIcon"
                        ></i>
                        <i
                            class="bi"
                            :class="stats.weatherIcon"
                            :style="{ color: stats.weatherIconColor }"
                        ></i>
                        <span v-if="stats.run.weather?.temp_c" class="ms-2"
                            >{{
                                formatDec(
                                    temperatureConvert(
                                        stats.run.weather.temp_c,
                                        "celsius",
                                        session.user!.temperature_unit,
                                    ),
                                    0,
                                )
                            }}°</span
                        >
                    </div>
                </div>
            </div>
            <div class="text-end">
                <div>{{ durationFormatter(run.average_pace) }} min/{{ stats.distAbbr }}</div>
                <div class="mt-1">{{ durationFormatter(run.active_duration) }}</div>
                <div class="mt-1" v-if="run.calories">{{ run.calories }} cal</div>
            </div>
        </div>
    </div>
</template>
