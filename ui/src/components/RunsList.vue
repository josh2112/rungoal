<script setup lang="ts">
import { useSession } from "../stores/session";
import RunView from "./RunView.vue";
const session = useSession();
</script>

<template>
    <RunView v-for="run in session.runs" :key="run.id" :run="run" />
</template>
