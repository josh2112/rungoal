<script setup lang="ts">
import { useSession } from '../stores/session';
import RunView from './RunView.vue';
const session = useSession();
</script>

<template>
    <ul>
        <RunView v-for="run in session.runs" :key="run.id" :run="run" />
    </ul>
</template>
