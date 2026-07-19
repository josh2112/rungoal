<script setup lang="ts">
import ErrorsList from "./components/ErrorsList.vue";
import HeaderView from "./components/HeaderView.vue";
import AccountDialog from "./dialogs/AccountDialog.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
</script>

<template>
    <header>
        <HeaderView />
    </header>

    <AccountDialog />
    <OnboardingDialog />

    <main>
        <RouterView />
    </main>

    <ErrorsList />
</template>
