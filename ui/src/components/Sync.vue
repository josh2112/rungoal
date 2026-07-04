<script setup lang="ts">
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { onMounted, ref } from "vue";
import { type SyncState } from "../models";
import { useApi } from "../stores/api";
import { useSession } from "../stores/session";

const api = useApi();
const session = useSession();

async function startSync() {
    await session.startSync();
    streamEvents();
}

function streamEvents() {
    fetchEventSource(`${import.meta.env.BASE_URL}/api/sync/stream`, {
        headers: {
            Authorization: `Bearer ${api.accessToken}`,
        },
        onmessage(msg) {
            syncState.value = JSON.parse(msg.data);
            console.log("Progress updated:", syncState.value);
        },
        onerror(err) {
            console.error("SSE Error:", err);
            throw err;
        },
        onclose() {
            syncState.value = undefined;
            console.log("Sync complete!");
        },
    });
}

const syncState = ref<SyncState>();

onMounted(async () => {
    const p = await session.getSyncStatus();
    if (!p.is_complete) {
        syncState.value = p;
        streamEvents();
    }
});
</script>

<template>
    <button v-if="!syncState" @click="() => startSync()">Sync</button>
    <div v-else>
        <div v-for="task in syncState.tasks" :key="task.task">
            <span>{{ task.task }}</span>
            <progress :value="task.value" :max="task.total ?? undefined" />
        </div>
    </div>
</template>
