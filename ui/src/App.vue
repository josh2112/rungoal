<script setup lang="ts">
import Account from "./components/Account.vue";
import RunsList from "./components/RunsList.vue";
import GoalsList from "./components/GoalsList.vue";
import Sync from "./components/Sync.vue";
import "./styles/style.scss";
</script>

<template>
    <Account />
    <Sync />
    <h2>Goals</h2>
    <GoalsList />
    <h2>Runs</h2>
    <RunsList />
</template>
