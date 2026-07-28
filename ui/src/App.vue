<script setup lang="ts">
import { ref, watch } from "vue";
import ErrorsList from "./components/ErrorsList.vue";
import HeaderView from "./components/HeaderView.vue";
import OnboardingDialog from "./dialogs/OnboardingDialog.vue";
import { useSession } from "./stores/session.ts";

const session = useSession();

const onboardingGoalDialogRef = ref<InstanceType<typeof OnboardingDialog> | null>(null);

// If user is not onboarded yet and the onboarding process has not been started, do it now
watch(
    () => session.syncState,
    (_) => {
        if (!session.user!.is_onboarded && !session.syncState?.is_syncing) {
            onboardingGoalDialogRef.value!.open();
        }
    },
);

import { useDark, useMutationObserver } from "@vueuse/core";

const isDark = useDark({
    // 1. Tell VueUse to target the 'data-bs-theme' attribute instead of a class
    attribute: "data-bs-theme",
    valueDark: "dark",
    valueLight: "light",

    // 2. Use your application's exact localStorage key
    storageKey: "rungoal.theme",
});

// 3. Listen to external mutations (like Chrome DevTools or other scripts)
useMutationObserver(
    document.documentElement,
    (mutations) => {
        for (const mutation of mutations) {
            if (mutation.attributeName === "data-bs-theme") {
                const currentAttr = document.documentElement.getAttribute("data-bs-theme");

                // Keep VueUse's internal ref synchronized with the DOM state
                if (currentAttr && isDark.value !== (currentAttr === "dark")) {
                    isDark.value = currentAttr === "dark";
                }
            }
        }
    },
    {
        attributes: true,
        attributeFilter: ["data-bs-theme"],
    },
);
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
