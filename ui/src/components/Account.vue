<script setup lang="ts">
import { Modal } from "bootstrap";
import { onMounted, ref, watch } from "vue";
import { useSession } from "../stores/session";

const session = useSession();

// First-time user onboarding stuff

const onboardingModalRef = ref<Element>();
let onboardingModal: Modal | null = null;

const onboardingIncludeRuntracker = ref(true);

onMounted(() => (onboardingModal = new Modal(onboardingModalRef.value!)));

watch(
    () => session.user,
    (user, _) => {
        if (user && !user.is_onboarded) {
            onboardingModal?.show();
        }
    },
);

const startFirstSync = () => {
    console.log("starting sync with include runtracker = ", onboardingIncludeRuntracker.value);
    session.startSync(undefined, undefined, onboardingIncludeRuntracker.value);
    onboardingModal?.hide();
};
</script>

<template>
    <div>
        <img
            v-if="session.user"
            class="avatar"
            :src="`${session.user.avatar_uri}=s32-c`"
            :alt="session.user.name"
            data-bs-toggle="modal"
            data-bs-target="#accountModal"
        />
    </div>

    <div id="accountModal" class="modal fade" tabindex="-1" aria-labelledby="accountModalTitle" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="accountModalTitle">Account</h1>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="account-box">
                        <img class="avatar" :src="`${session.user?.avatar_uri}=s64-c`" />
                        <div>
                            <div class="user-name">
                                {{ session.user?.name }}
                            </div>
                            <div>{{ session.user?.email }}</div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button
                        type="button"
                        class="btn btn-primary"
                        data-bs-dismiss="modal"
                        @click="() => session.logOut()"
                    >
                        Log out
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div
        ref="onboardingModalRef"
        class="modal fade"
        tabindex="-1"
        aria-labelledby="onboardingModalTitle"
        aria-hidden="true"
        data-bs-backdrop="static"
        data-bs-keyboard="false"
    >
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="onboardingModalTitle">Welcome!</h1>
                </div>
                <div class="modal-body">
                    <p>We'll sync run data from Google Health for this account:</p>
                    <div class="account-box">
                        <img class="avatar" :src="`${session.user?.avatar_uri}=s64-c`" />
                        <div>
                            <div class="user-name">
                                {{ session.user?.name }}
                            </div>
                            <div>{{ session.user?.email }}</div>
                        </div>
                    </div>
                    <input type="checkbox" id="includRuntrackerId" v-model="onboardingIncludeRuntracker" />
                    <label for="includRuntrackerId" class="ms-2 pt-4">Also sync data from Runtracker</label>
                </div>
                <div class="modal-footer">
                    <button
                        type="button"
                        class="btn btn-primary"
                        data-bs-dismiss="modal"
                        @click="() => startFirstSync()"
                    >
                        Start sync
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.avatar {
    border-radius: 50%;
}

.account-box {
    display: flex;
    align-items: center;
    gap: 10px;
}

.user-name {
    font-weight: bold;
}
</style>
