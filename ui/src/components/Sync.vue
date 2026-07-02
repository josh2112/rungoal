<script setup lang="ts">
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { onMounted, ref } from "vue";
import { type SyncProgress } from "../models";
import { useApi } from "../stores/api";
import { useSession } from "../stores/session";

const api = useApi();
const session = useSession();

async function startSync() {
    await fetchEventSource(`${import.meta.env.BASE_URL}/api/sync`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${api.accessToken}`,
        },
        onmessage(msg) {
            progress.value = JSON.parse(msg.data);
            console.log("Progress updated:", progress.value);
        },
        onerror(err) {
            console.error("SSE Error:", err);
            throw err;
        },
        onclose() {
            progress.value = undefined;
            console.log("Sync complete!");
        },
    });
}

const progress = ref<SyncProgress>();

onMounted(async () => {
    const p = await session.getSyncStatus();
    if (!p.is_complete) {
        progress.value = p;
    }
});
</script>

<template>
    <button v-if="!progress" @click="() => startSync()">Sync</button>
    <span v-else>{{ progress }}</span>
</template>
