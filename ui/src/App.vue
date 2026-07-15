<script setup lang="ts">
import { ref } from "vue";
import GoalsList from "./components/GoalsList.vue";
import HeaderView from "./components/HeaderView.vue";
import LoginButton from "./components/LoginButton.vue";
import RunsList from "./components/RunsList.vue";
import SyncView from "./components/SyncView.vue";
import AccountDialog from "./dialogs/AccountDialog.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
import { useFetchMore } from "./fetch_more";
import { useSession } from "./stores/session";
import "./styles/style.scss";

const session = useSession();

const fetchMoreTrigger = ref<Element>();
const isLoading = ref(false)
const hasMore = ref(true)

useFetchMore(fetchMoreTrigger, async () => {
    if (isLoading.value || !hasMore.value) return;

    isLoading.value = true;
    hasMore.value = await session.getPreviousRuns();
    isLoading.value = false;
});

</script>

<template>
    <HeaderView />

    <AccountDialog />
    <OnboardingDialog />

    <div class="container mt-3">
        <div v-if="session.user">
            <h5>Goals</h5>
            <GoalsList />
            <div class="d-flex align-items-center justify-content-between w-100 gap-3 mt-3" style="height: 35px;">
                <h5 class="mb-0 text-nowrap">Runs</h5>
                <SyncView v-if="session.syncState" :sync-state="session.syncState" />
            </div>
            <RunsList />
        </div>
        <div v-else class="d-flex align-items-center justify-content-center min-vh-100"">
            <LoginButton />
        </div>

        <div class=" text-center mt-5" style="min-height: 50px;" ref="fetchMoreTrigger">
            <div v-if="isLoading" class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <hr v-else-if="!hasMore" />
        </div>
    </div>



</template>
