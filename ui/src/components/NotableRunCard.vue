<script setup lang="ts">
import type { Run } from "../models/run";
import RunCard from "./RunCard.vue";

const props = defineProps<{
    run?: Run;
}>();
</script>

<template>
    <div v-if="run" class="col-lg-6 mt-3">
        <slot></slot>
        <RunCard class="mt-3" :run="run" />
    </div>
</template>
