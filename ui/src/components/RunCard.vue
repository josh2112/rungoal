<script setup lang="ts">
import tinygradient from 'tinygradient';
import { computed } from "vue";
import { toRunStats, type Run, type Weather } from "../models/run";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

/*
rain nonzero? < 2.5mm = cloud-drizzle, otherwize cloud-rain
clouds? sun -> cloud-sun -> cloud -> clouds
*/
const props = defineProps<{
    run: Run;
}>();

const session = useSession();

const stats = computed(() => toRunStats(props.run, session.statRanges, session.settings!.distance_unit));

const redToGreen = tinygradient([
    { color: '#ff0000', pos: 0 },
    { color: '#ff8800', pos: 0.5 },
    { color: '#00ff00', pos: 1 }
]);

const effRange = computed(() => session.statRanges.efficiency ? session.statRanges.efficiency.max - session.statRanges.efficiency.min : undefined);

const splitEfficiency = computed(() => effRange.value ? props.run.split_stats.map(ss => ss.efficiency).filter(eff => eff !== null).map(eff =>
    (eff - session.statRanges.efficiency!.min) / effRange.value!
) : []);

const weatherIcon = (wx: Weather | undefined): string | undefined => {
    if (!wx) return undefined;

    const r = wx.rain_mm;
    if (r && r > 2.5) return 'bi-cloud-rain-fill';
    if (r && r > 0) return 'bi-cloud-drizzle-fill';

    const c = wx.cloud_cover_pct;
    if (c !== null) {
        if (c > 75) return 'bi-clouds-fill';
        if (c > 50) return 'bi-cloud-fill';
        if (c > 25) return 'bi-cloud-sun-fill';
        return 'bi-sun-fill';
    }
}

const weatherIconColor = (wx: Weather | undefined): string | undefined => {
    if (!wx) return undefined;
    const r = wx?.rain_mm ?? 0;
    const c = wx?.cloud_cover_pct ?? -1;

    if (r > 0) return 'dodgerblue';
    if (c > 25) return 'gray';
    if (c >= 0) return 'gold';
}
</script>

<template>
    <div class="col-lg-6">
        <div class="card bg-body-tertiary rounded-4 border-0">
            <div class="card-body">
                <div class="d-flex justify-content-between card-title">
                    <h5 class="text-primary-emphasis">{{ stats.date_str }}</h5>
                    <h5 class="text-end">{{ formatDec(stats.distance, 2) }} {{ stats.dist_abbr }}</h5>
                </div>
                <div class="d-flex justify-content-between card-text">
                    <div>
                        <div v-if="stats.run.calories">{{ stats.run.calories }} cal</div>
                        <i v-if="run.device_type == 'WATCH'" class="bi bi-watch me-2 text-primary-emphasis"
                            style="float:left"></i>
                        <i class="bi me-3" :class="weatherIcon(run.weather)" style="float:left"
                            :style="{ color: weatherIconColor(run.weather) }"></i>
                        <div class="eff-sq-container">
                            <div v-for="eff in splitEfficiency" class="eff-sq"
                                :style="{ backgroundColor: redToGreen.rgbAt(eff).toHexString() }" />
                        </div>

                    </div>
                    <div class="text-end">
                        <div>{{ stats.duration_str }}</div>
                        <div>{{ stats.pace_str }} min/{{ stats.dist_abbr }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.eff-sq-container {
    margin-top: 8px;
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
