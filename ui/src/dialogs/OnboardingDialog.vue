<script setup lang="ts">
import { ref } from "vue";
import AccountView from "../components/AccountView.vue";
import { useDialog } from "../composables/dialog.ts";
import { useSession } from "../stores/session";

const session = useSession();

const onboardingIncludeRuntracker = ref(true);

const dialogRef = ref<Element>();
const { open, close } = useDialog(dialogRef);
defineExpose({ open })

const startFirstSync = () => {
    close();
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
                    <input type="checkbox" id="includeRuntrackerId" v-model="onboardingIncludeRuntracker" />
                    <label for="includeRuntrackerId" class="ms-2 pt-4">Also sync data from Runtracker</label>
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