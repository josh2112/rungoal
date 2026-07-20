<script setup lang="ts">
import { ref } from "vue";
import AccountView from "../components/AccountView.vue";
import { useDialog } from "../composables/dialog.ts";
import { useSession } from "../stores/session";

const session = useSession();

const dialogRef = ref<Element>();
const { open, close } = useDialog(dialogRef);
defineExpose({ open })

const closeAndLogOut = () => {
    close();
    session.logOut();
}

const appVersion = import.meta.env.APP_VERSION;
</script>

<template>
    <div ref="dialogRef" class="modal fade" tabindex="-1" aria-labelledby="accountModalTitle" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="accountModalTitle">Account</h1>
                    <button type="button" class="btn-close" @click="() => close()" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <AccountView />
                    <div class="mt-4">
                        <small class="mt-3">RunGoal version {{ appVersion }}</small>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal"
                        @click="() => closeAndLogOut()">
                        Log out
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>