<script setup lang="ts">
import { onMounted, ref } from "vue";
import FetchMoreTrigger from "../components/FetchMoreTrigger.vue";
import GoalsList from "../components/GoalsList.vue";
import LoginButton from "../components/LoginButton.vue";
import RunsList from "../components/RunsList.vue";
import SyncView from "../components/SyncView.vue";
import GoalDialog from "../dialogs/GoalDialog.vue";
import { navbarState } from "../models/misc.ts";
import { useSession } from "../stores/session";

const session = useSession();

const addGoalDialogRef = ref<InstanceType<typeof GoalDialog>>();

const addGoal = () => addGoalDialogRef.value?.open();

onMounted(() => {
    navbarState.title = "";
    navbarState.actions = [];
});
</script>

<template>
    <GoalDialog ref="addGoalDialogRef" :goal="undefined" />

    <div class="container mt-3">
        <div v-if="session.user">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <h5 class="mb-0 text-nowrap">Goals</h5>
                <button class="btn btn-primary" @click="() => addGoal()">Add goal</button>
            </div>

            <GoalsList v-if="session.goals.length > 0" />
            <div v-else class="align-items-center text-secondary">No goals</div>

            <div class="d-flex align-items-center justify-content-between w-100 gap-3 mt-3 mb-2" style="height: 35px">
                <h5 class="mb-0 text-nowrap">Runs</h5>
                <SyncView v-if="session.syncState" :sync-state="session.syncState" />
            </div>

            <RunsList />
        </div>
        <div v-else class="d-flex align-items-center justify-content-center min-vh-100">
            <LoginButton />
        </div>

        <FetchMoreTrigger />
    </div>
</template>
