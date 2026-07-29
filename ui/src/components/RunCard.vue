<script setup lang="ts">
import { useDark } from "@vueuse/core";
import tinygradient from "tinygradient";
import { computed } from "vue";
import { type Run } from "../models/run";
import { useSession } from "../stores/session";
import { currentLocale, distanceAbbr, durationFormatter, formatDec } from "../utils";

const props = defineProps<{
    run: Run;
}>();

const session = useSession();

const distAbbr = distanceAbbr(session.settings.distance_unit);

const redToGreen = tinygradient([
    { color: "#ff0000", pos: 0 },
    { color: "#ff8800", pos: 0.5 },
    { color: "#00ff00", pos: 1 },
]);

const isDark = useDark();

// Split efficiencies normalized to 0-1
const normalizedSplitEfficiency = computed(() =>
    session.statRanges.efficiency?.range
        ? props.run.split_stats
              .map((ss) => ss.efficiency)
              .filter((eff): eff is number => eff !== undefined)
              .map((eff) => (eff - session.statRanges.efficiency!.min) / session.statRanges.efficiency!.range)
        : [],
);

const weatherIcon = computed(() => {
    if (!props.run.weather) return undefined;

    const r = props.run.weather.rain_mm;
    if (r !== undefined) {
        if (r > 2.5) return "bi-cloud-rain-fill";
        if (r > 0) return "bi-cloud-drizzle-fill";
    }

    const c = props.run.weather.cloud_cover_pct;
    if (c !== undefined) {
        if (c > 75) return "bi-clouds-fill";
        if (c > 50) return "bi-cloud-fill";
        if (c > 25) return "bi-cloud-sun-fill";
        return "bi-sun-fill";
    }
});

const weatherIconColor = computed(() => {
    if (!props.run.weather) return undefined;
    const r = props.run.weather?.rain_mm ?? 0;
    const c = props.run.weather?.cloud_cover_pct ?? -1;

    if (r > 0) return "dodgerblue";
    if (c > 25) return "gray";
    if (c >= 0) return "gold";
});

const deviceTypeIcon = computed(() => {
    if (props.run.device_type == "WATCH") return "bi-watch";
    else if (props.run.device_type == "PHONE") return "bi-phone";
});

const runName = computed(() => {
    if (props.run.start_time.hour < 11) return "Morning Run";
    if (props.run.start_time.hour < 14) return "Midday Run";
    if (props.run.start_time.hour < 17) return "Afternoon Run";
    return "Evening Run";
});
</script>

<template>
    <div class="col-lg-6">
        <div class="card rounded-4 border-0" :class="isDark ? 'bg-body-tertiary' : 'bg-body-secondary'">
            <div class="card-body">
                <div class="d-flex justify-content-between card-title">
                    <h5 class="text-primary-emphasis">{{ runName }}</h5>
                    <h5 class="text-end">{{ formatDec(run.distance, 2) }} {{ distAbbr }}</h5>
                </div>
                <div class="d-flex justify-content-between card-text">
                    <div>
                        <div>
                            {{
                                run.start_time.toLocaleString(currentLocale, {
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
                            <div v-if="normalizedSplitEfficiency.length > 0" class="eff-sq-container me-3">
                                <div
                                    v-for="eff in normalizedSplitEfficiency"
                                    class="eff-sq"
                                    :style="{ backgroundColor: redToGreen.rgbAt(eff).toHexString() }"
                                />
                            </div>
                            <i
                                v-if="run.device_type == 'WATCH'"
                                class="bi me-3 text-primary-emphasis"
                                :class="deviceTypeIcon"
                            ></i>
                            <i class="bi" :class="weatherIcon" :style="{ color: weatherIconColor }"></i>
                        </div>
                    </div>
                    <div class="text-end">
                        <div>{{ durationFormatter(run.average_pace) }} min/{{ distAbbr }}</div>

                        <div>
                            {{ durationFormatter(run.active_duration) }}
                        </div>
                        <div class="mt-1" v-if="run.calories">{{ run.calories }} cal</div>
                    </div>
                </div>
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
