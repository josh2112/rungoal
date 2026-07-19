<script setup lang="ts">
import { useSession } from "../stores/session";
import RunCard from "./RunCard.vue";
const session = useSession();
</script>

<template>
    <div class="row gy-3">
        <RunCard v-for="run in session.runs" :key="run.id" :run="run" />
    </div>
</template>
