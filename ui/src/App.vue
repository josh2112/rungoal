<script setup lang="ts">
import { ref, watch } from "vue";
import ErrorsList from "./components/ErrorsList.vue";
import HeaderView from "./components/HeaderView.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
import { useSession } from "./stores/session.ts";

const session = useSession();

const onboardingGoalDialogRef = ref<InstanceType<typeof OnboardingDialog> | null>(null);

// If user is not onboarded yet and the onboarding process has not been started, do it now
watch(() => [session.user, session.syncState], (_1, _2) => {
    if (!session.user!.is_onboarded) {
        if (!session.syncState?.is_syncing) {
            onboardingGoalDialogRef.value!.open();
        }
    }
});
</script>

<template>
    <header>
        <HeaderView />
    </header>

    <OnboardingDialog ref="onboardingGoalDialogRef" />

    <main>
        <RouterView />
    </main>

    <ErrorsList />
</template>
