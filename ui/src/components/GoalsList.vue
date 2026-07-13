<script setup lang="ts">
import { useSession } from "../stores/session";
import GoalView from "./GoalView.vue";

const session = useSession();
</script>

<template>
    <div class="row gy-3">
        <GoalView v-for="goal in session.goals" :key="goal.id" :goal="goal" />
    </div>
</template>
