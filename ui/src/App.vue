<script setup lang="ts">
import Account from "./components/Account.vue";
import GoalsList from "./components/GoalsList.vue";
import LoginButton from "./components/LoginButton.vue";
import RunsList from "./components/RunsList.vue";
import Sync from "./components/Sync.vue";
import { useSession } from "./stores/session.ts";
import "./styles/style.scss";

const session = useSession();
</script>

<template>
    <div class="container-sm">
        <Account />
        <Sync />
        <div v-if="session.user">
            <h2>Goals</h2>
            <GoalsList />
            <h2>Runs</h2>
            <RunsList />
        </div>
        <div v-else>
            <LoginButton />
        </div>
    </div>
</template>
