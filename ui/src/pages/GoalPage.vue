<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { DialogParams } from "../dialogs/ConfirmationDialog.vue";
import ConfirmationDialog from "../dialogs/ConfirmationDialog.vue";
import GoalDialog from "../dialogs/GoalDialog.vue";
import { toGoalStats } from "../models/goal";
import { navbarState } from "../models/misc";
import { useSession } from "../stores/session";
import { formatDec } from "../utils";

const route = useRoute();
const router = useRouter();
const session = useSession();

const editGoalDialogRef = ref<InstanceType<typeof GoalDialog>>();
const removeGoalDialogRef = ref<InstanceType<typeof ConfirmationDialog>>();

const goal = computed(() => session.goals[+route.params.index - 1]);
const stats = computed(() => toGoalStats(goal.value, session.settings!.distance_unit));

const progress = computed(() => (stats.value.goal.current_distance_meters / stats.value.goal.distance_meters) * 100);

onMounted(() => {
    navbarState.title = stats.value.goal.name;
    navbarState.actions = [{
        icon: "bi-pencil",
        callback: () => editGoalDialogRef.value?.open()
    }, {
        icon: "bi-trash",
        callback: () => removeGoalDialogRef.value?.open()
    }]
});

const deleteDialogParmas = {
    title: "Remove goal",
    message: "Are you sure?",
    isCancelable: true,
    buttons: [{
        title: "Cancel",
        isCancel: true,
    }, {
        title: "Yes",
        action: async () => {
            // TODO: Indicate indeterminate progress here?
            await session.deleteGoal(goal.value);
            router.back();
        },
        isPrimary: true,
    }]
} as DialogParams
</script>

<template>
    <GoalDialog ref="editGoalDialogRef" :goal="goal" />
    <ConfirmationDialog ref="removeGoalDialogRef" :params="deleteDialogParmas" />

    <div class="container mt-3">
        <div class="col-lg-6">
            <div class="d-flex justify-content-between">
                <h5>
                    {{ stats.goal.name }}
                </h5>
                <h5 class="text-end"
                    :class="stats.current_pace_diff >= 0 ? 'text-success-emphasis' : 'text-danger-emphasis'">
                    {{ stats.current_pace_diff >= 0 ? "+" : "-" }}{{ formatDec(Math.abs(stats.current_pace_diff), 2) }}
                    {{ stats.dist_abbr }}
                </h5>
            </div>
            <div class="card-text">
                <div>{{ formatDec(stats.total_dist, 2) }} {{ stats.dist_abbr }} in {{ stats.total_days }} days</div>
                <div class="progress my-2" role="progressbar" aria-label="Goal progress"
                    :aria-valuenow="stats.goal.current_distance_meters" aria-valuemin="0"
                    :aria-valuemax="stats.goal.distance_meters">
                    <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
                </div>
                <div>
                    {{ formatDec(stats.current_dist, 2) }} {{ stats.dist_abbr }} / {{ formatDec(stats.percent, 0) }}%
                    complete<br />
                </div>
                <div>
                    {{ stats.remaining_days }} days to go ({{ formatDec(stats.remaining_pace, 2) }}
                    {{ stats.dist_abbr }} per day)
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.hover-highlight {
    transition: background-color 0.2s ease-in-out;
}

.hover-highlight:hover {
    background-color: rgba(var(--bs-secondary-bg-rgb), 0.6) !important;
}
</style>
