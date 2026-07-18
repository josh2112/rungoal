import { defineStore } from "pinia";
import { ref } from "vue";

export const useDialogs = defineStore("dialogs", () => {
    const isAccountDialogOpen = ref(false);
    const isOnboardingDialogOpen = ref(false);
    const isGoalDialogOpen = ref(false);

    return { isAccountDialogOpen, isOnboardingDialogOpen, isGoalDialogOpen };
});
