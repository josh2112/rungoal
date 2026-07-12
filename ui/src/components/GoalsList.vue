<script setup lang="ts">
import { useSession } from "../stores/session";
import GoalView from "./GoalView.vue";

const session = useSession();
</script>

<template>
    <GoalView v-for="goal in session.goals" :key="goal.id" :goal="goal" />
</template>
