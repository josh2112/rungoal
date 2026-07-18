<script setup lang="ts">
import ErrorsView from "./components/ErrorsView.vue";
import FetchMoreView from "./components/FetchMoreView.vue";
import GoalsList from "./components/GoalsList.vue";
import HeaderView from "./components/HeaderView.vue";
import LoginButton from "./components/LoginButton.vue";
import RunsList from "./components/RunsList.vue";
import SyncView from "./components/SyncView.vue";
import AccountDialog from "./dialogs/AccountDialog.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
import { useSession } from "./stores/session";
import "./styles/style.scss";

const session = useSession();
</script>

<template>
    <HeaderView />

    <AccountDialog />
    <OnboardingDialog />

    <div class="container mt-3">
        <div v-if="session.user">
            <h5>Goals</h5>
            <GoalsList />
            <div class="d-flex align-items-center justify-content-between w-100 gap-3 mt-3" style="height: 35px">
                <h5 class="mb-0 text-nowrap">Runs</h5>
                <SyncView v-if="session.syncState" :sync-state="session.syncState" />
            </div>
            <RunsList />
        </div>
        <div v-else class="d-flex align-items-center justify-content-center min-vh-100">
            <LoginButton />
        </div>

        <FetchMoreView />
    </div>

    <ErrorsView />
</template>
