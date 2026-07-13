<script setup lang="ts">
import GoalsList from "./components/GoalsList.vue";
import HeaderView from "./components/HeaderView.vue";
import LoginButton from "./components/LoginButton.vue";
import RunsList from "./components/RunsList.vue";
import AccountDialog from "./dialogs/AccountDialog.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
import { useSession } from "./stores/session.ts";
import "./styles/style.scss";

const session = useSession();
</script>

<template>
    <HeaderView />
    <div class="container">
        <div v-if="session.user">
            <h2>Goals</h2>
            <GoalsList />
            <h2>Runs</h2>
            <RunsList />
        </div>
        <div v-else>
            <LoginButton />
        </div>

        <AccountDialog />
        <OnboardingDialog />
    </div>
</template>

<style scoped>
h2 {
    margin-top: 10px;

}
</style>