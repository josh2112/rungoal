<script setup lang="ts">
import type { Run } from "../models/run";
import RunCard from "./RunCard.vue";

const props = defineProps<{
    run?: Run;
}>();
</script>

<template>
    <div v-if="run" class="mt-3">
        <slot></slot>
        <RunCard :run="run" />
    </div>
</template>
