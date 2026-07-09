<script setup lang="ts">
import { useSession } from '../stores/session';
const session = useSession();
</script>

<template>
    <ul>
        <li v-for="run in session.runs" :key="run.id">
            {{ run.start_time }}
        </li>
    </ul>
</template>
