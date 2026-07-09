<script setup lang="ts">
import { Temporal } from 'temporal-polyfill';
import { currentLocale, distanceAbbr, distanceConvert, formatDec } from '../conversion';
import type { Goal } from '../models';
import { useSession } from '../stores/session';

// TODO: This needs to be precalculated and stored in GoalStats or something... we may have diffent Vue components
// to display this data in different ways

const props = defineProps<{
    goal: Goal
}>();

const session = useSession();

const today = Temporal.Now.plainDateISO();

const distUnit = session.settings!.distance_unit;
const distAbbr = distanceAbbr(distUnit);

const name = props.goal.start_date.toLocaleString(currentLocale, { dateStyle: "full" });

const totalDist = distanceConvert(props.goal.distance_meters, "meters", distUnit);
const currentDist = distanceConvert(props.goal.current_distance_meters, "meters", distUnit);
const remainingDist = totalDist - currentDist;

const totalDays = props.goal.start_date.until(props.goal.end_date).days + 1;
const elapsedDays = props.goal.start_date.until(today).days + 1;
const remainingDays = totalDays - elapsedDays;

const remainingPace = remainingDist / remainingDays;

const currentPaceDiff = currentDist - (elapsedDays / totalDays) * totalDist;

const percent = props.goal.current_distance_meters / props.goal.distance_meters * 100
</script>

<template>
    <li>
        {{ name }}<br>
        {{ formatDec(totalDist, 2) }} {{ distAbbr }} in {{ totalDays }} days
        <br>
        {{ formatDec(currentDist, 2) }} {{ distAbbr }} / {{ formatDec(percent, 0) }}% complete
        ({{ formatDec(Math.abs(currentPaceDiff), 2) }} {{ currentPaceDiff >= 0 ? 'over' : 'under' }} pace)<br>
        {{ remainingDays }} days to go ({{ formatDec(remainingPace, 2) }} {{ distAbbr }} per day)
    </li>
</template>