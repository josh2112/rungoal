<script setup lang="ts">
import { useSession } from "../stores/session";
import GoalCard from "./GoalCard.vue";

const session = useSession();
</script>

<template>
    <div class="row gy-3">
        <GoalCard v-for="goal in session.goals" :key="goal.id" :goal="goal" />
    </div>
</template>
