<script setup lang="ts">
import { Modal } from "bootstrap";
import { onMounted, ref, watch } from "vue";
import AccountView from "../components/AccountView.vue";
import { useDialogs } from "../stores/dialogs";
import { useSession } from "../stores/session";

const session = useSession();
const dialogs = useDialogs();

const dialogRef = ref<Element>();
let dialog: Modal | null = null;

onMounted(() => (dialog = new Modal(dialogRef.value!)));

watch(() => dialogs.isOnboardingDialogOpen, (isOpen) => {
    if (isOpen) dialog?.show();
    else dialog?.hide();
});


const onboardingIncludeRuntracker = ref(true);

const startFirstSync = () => {
    (document.activeElement as HTMLElement)?.blur();
    dialogs.isOnboardingDialogOpen = false;

    console.log("Starting sync with include runtracker = ", onboardingIncludeRuntracker.value);
    session.startSync(undefined, undefined, onboardingIncludeRuntracker.value);
};
</script>

<template>
    <div ref="dialogRef" class="modal fade" tabindex="-1" aria-labelledby="onboardingModalTitle" aria-hidden="true"
        data-bs-backdrop="static" data-bs-keyboard="false">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="onboardingModalTitle">Welcome!</h1>
                </div>
                <div class="modal-body">
                    <p>We'll sync run data from Google Health for this account:</p>
                    <AccountView />
                    <input type="checkbox" id="includRuntrackerId" v-model="onboardingIncludeRuntracker" />
                    <label for="includRuntrackerId" class="ms-2 pt-4">Also sync data from Runtracker</label>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal"
                        @click="() => startFirstSync()">
                        Start sync
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>