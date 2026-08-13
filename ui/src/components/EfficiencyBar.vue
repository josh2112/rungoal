<script setup lang="ts">
import { computed } from "vue";
import type { RunSplitStats } from "../models/run";
import { gradientRedToGreen, type Range } from "../utils";

const props = defineProps<{
    efficiencyRange: Range;
    splitStats: RunSplitStats[];
}>();

const effSpread = computed(() => props.efficiencyRange.max - props.efficiencyRange.min);

const normalize = (v: number) =>
    Math.min(
        props.efficiencyRange.max,
        Math.max(props.efficiencyRange.min, (v - props.efficiencyRange.min) / effSpread.value),
    );
</script>

<template>
    <div class="eff-sq-container">
        <div
            v-for="split in splitStats"
            class="eff-sq"
            :style="{
                backgroundColor:
                    split.efficiency > 0
                        ? gradientRedToGreen.rgbAt(normalize(split.efficiency)).toHexString()
                        : 'transparent',
                width: `${((split.end_secs - split.start_secs) / 300) * 10}px`,
            }"
        />
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
    height: 10px;
    border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
