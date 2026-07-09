<script setup lang="ts">
import { useSession } from '../stores/session';
const session = useSession();
</script>

<template>
    <ul>
        <li v-for="goal in session.goals" :key="goal.id">
            {{ goal.start_date }}, {{ goal.distance_meters }}, {{ goal.current_distance_meters }},
            {{ goal.current_distance_meters / goal.distance_meters * 100 }}%
        </li>
    </ul>
</template>
