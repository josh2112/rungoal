import { defineStore } from "pinia";
import { ref } from "vue";

export const useDialogs = defineStore("dialogs", () => {
    const isAccountDialogOpen = ref(false);
    const isOnboardingDialogOpen = ref(false);

    return { isAccountDialogOpen, isOnboardingDialogOpen }
});
