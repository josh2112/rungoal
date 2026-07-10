<script setup lang="ts">
import { toGoalStats, type Goal } from '../models/goal';
import { useSession } from '../stores/session';
import { formatDec } from '../utils';

const props = defineProps<{
    goal: Goal
}>();

const session = useSession();
const stats = toGoalStats(props.goal, session.settings!.distance_unit);
</script>

<template>
    <li>
        {{ stats.name }}<br>
        {{ formatDec(stats.total_dist, 2) }} {{ stats.dist_abbr }} in {{ stats.total_days }} days
        <br>
        <progress :value="stats.goal.current_distance_meters" :max="stats.goal.distance_meters" /><br>
        {{ formatDec(stats.current_dist, 2) }} {{ stats.dist_abbr }} / {{ formatDec(stats.percent, 0) }}% complete
        ({{ formatDec(Math.abs(stats.current_pace_diff), 2) }} {{ stats.current_pace_diff >= 0 ? 'over' : 'under' }}
        pace)<br>
        {{ stats.remaining_days }} days to go ({{ formatDec(stats.remaining_pace, 2) }} {{ stats.dist_abbr }} per day)
    </li>
</template>