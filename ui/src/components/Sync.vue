<script setup lang="ts">
import { useSession } from "../stores/session";

const session = useSession();

const startSync = () => session.startSync(undefined, undefined, false);
</script>

<template>
    <div v-if="session.syncState">
        <button class="btn btn-primary" v-if="false == session.syncState.is_syncing" @click="() => startSync()">
            Sync
        </button>
        <div v-else>
            <div v-for="task in session.syncState.tasks" :key="task.task">
                <span>{{ task.task }}</span>
                <progress :value="task.total != null ? task.value : undefined" :max="task.total ?? undefined" />
            </div>
        </div>
    </div>
</template>
