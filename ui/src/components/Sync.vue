<script setup lang="ts">
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { onMounted, ref } from "vue";
import { type SyncState } from "../models";
import { useApi } from "../stores/api";
import { useSession } from "../stores/session";

const api = useApi();
const session = useSession();

async function startSync() {
    await session.startSync(undefined, undefined, false)
    streamEvents();
}

function streamEvents() {
    fetchEventSource(`${import.meta.env.BASE_URL}/api/sync/stream`, {
        headers: {
            Authorization: `Bearer ${api.accessToken}`,
        },
        onmessage(msg) {
            syncState.value = JSON.parse(msg.data);
            if (syncState.value?.synced_from) {
                console.log(`Sync complete: ${syncState.value?.synced_from} -> ${syncState.value?.synced_to}`)
            }
        },
        onerror(err) {
            console.error("SSE Error:", err);
        },
        onclose() {
            syncState.value = undefined;
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
            <progress :value="task.total != null ? task.value : undefined" :max="task.total ?? undefined" />
        </div>
    </div>
</template>
