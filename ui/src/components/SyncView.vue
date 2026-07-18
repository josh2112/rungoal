<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { SyncState } from "../models/misc";
import { useSession } from "../stores/session";

const props = defineProps<{
    syncState: SyncState;
}>();

const session = useSession();

const startSync = () => session.startSync(undefined, undefined, false);

const currentTask = computed(() =>
    props.syncState.tasks.length ? props.syncState.tasks[props.syncState.tasks.length - 1] : undefined,
);
const total = computed(() => props.syncState.tasks.reduce((sum, task) => sum + (task.total ?? task.value), 0));
const value = computed(() => props.syncState.tasks.reduce((sum, task) => sum + task.value, 0));

const secsSinceLastSynced = ref<number>();

let timer: number | undefined;

onMounted(() => {
    timer = setInterval(() => {
        if (session.lastSynced) {
            secsSinceLastSynced.value = (Date.now() - session.lastSynced) / 1000;
        } else {
            secsSinceLastSynced.value = undefined;
        }
    }, 1_000);
});

onUnmounted(() => clearInterval(timer));

const lastSyncedMsg = computed(() => {
    const s = secsSinceLastSynced.value;
    if (s) {
        if (s < 60) return "just now";
        else if (s < 60 * 60) {
            const mins = Math.round(s / 60);
            return `${mins} minute${mins != 1 ? "s" : ""} ago`;
        } else if (s < 60 * 60 * 24) {
            const hours = Math.round((s / 60) * 60);
            return `${hours} hours${hours != 1 ? "s" : ""} ago`;
        } else {
            const days = Math.round((s / 60) * 60 * 24);
            return `${days} days${days != 1 ? "s" : ""} ago`;
        }
    }
});
</script>

<template>
    <div v-if="!syncState.is_syncing">
        <small class="opacity-50 me-2" v-if="lastSyncedMsg">Last synced {{ lastSyncedMsg }}</small>
        <button class="btn sync-button btn-lg btn-primary ms-auto" @click="() => startSync()">
            <i class="bi bi-arrow-repeat"></i>
        </button>
    </div>
    <div v-else-if="currentTask" class="progress flex-grow-1 w-100">
        <div
            v-if="currentTask.total"
            class="progress w-100"
            role="progressbar"
            :aria-label="currentTask.task"
            :aria-valuemin="0"
            :aria-valuemax="total"
            :aria-valuenow="value"
        >
            <div class="progress-bar overflow-visible" :style="`width: ${(value / total) * 100}%`">
                {{ currentTask.task }}
            </div>
        </div>
        <div v-else class="progress w-100" role="progressbar" :aria-label="currentTask.task">
            <div class="progress-bar progress-bar-animated progress-bar-striped" style="width: 100%">
                {{ currentTask.task }}
            </div>
        </div>
    </div>
</template>

<style scoped>
.sync-button {
    --bs-btn-padding-x: 1rem;
    --bs-btn-padding-y: 0.1rem;
}
</style>
