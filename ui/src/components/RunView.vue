<script setup lang="ts">
import { toRunStats, type Run } from "../models/run";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const props = defineProps<{
    run: Run;
}>();

const session = useSession();
const stats = toRunStats(props.run, session.settings!.distance_unit);
</script>

<template>
    <li>
        {{ stats.date_str }}<br />
        <span v-if="stats.run.calories">{{ stats.run.calories }} cal</span>
        {{ formatDec(stats.distance, 2) }} {{ stats.dist_abbr }}<br />
        {{ stats.duration_str }}<br />
        {{ stats.pace_str }} {{ stats.dist_abbr }} / min
    </li>
</template>
