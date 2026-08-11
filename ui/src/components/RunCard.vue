<script setup lang="ts">
import { useDark } from "@vueuse/core";
import { computed } from "vue";
import { toRunStats, type Run } from "../models/run";
import { useSession } from "../stores/session";
import { currentLocale, durationFormatter, formatDec } from "../utils";
import EfficiencyBar from "./EfficiencyBar.vue";

const props = defineProps<{
    run: Run;
}>();

const session = useSession();

const stats = computed(() => toRunStats(props.run, session.settings));

const isDark = useDark();
</script>

<template>
    <div
        class="card rounded-4 border-0 hover-highlight"
        :class="isDark ? 'bg-body-tertiary' : 'bg-body-secondary'"
    >
        <div class="card-body">
            <div class="d-flex justify-content-between card-title">
                <h5 class="text-primary-emphasis">
                    <RouterLink
                        :to="`/run/${run.id}`"
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
                    <div v-if="run.location">{{ run.location.name }}</div>
                    <div class="d-flex align-items-center mt-2">
                        <EfficiencyBar
                            v-if="session.statsRanges.efficiency"
                            class="me-3"
                            :efficiency-range="session.statsRanges.efficiency"
                            :split-stats="stats.run.split_stats"
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
                    </div>
                </div>
                <div class="text-end">
                    <div>{{ durationFormatter(run.average_pace) }} min/{{ stats.distAbbr }}</div>
                    <div>{{ durationFormatter(run.active_duration) }}</div>
                    <div class="mt-1" v-if="run.calories">{{ run.calories }} cal</div>
                </div>
            </div>
        </div>
    </div>
</template>
