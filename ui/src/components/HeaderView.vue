<script setup lang="ts">
import { useRouter } from "vue-router";
import LogoSvg from "../../assets/logo.svg";
import { navbarState } from "../models/misc.ts";
import { useDialogs } from "../stores/dialogs.ts";
import { useSession } from "../stores/session.ts";

const session = useSession();
const dialogs = useDialogs();

const openAccountDialog = () => (dialogs.isAccountDialogOpen = true);

const router = useRouter();

const goBack = () => {
    if (window.history.length > 1) {
        router.back();
    } else {
        router.push("/");
    }
};
</script>

<template>
    <nav class="navbar sticky-top bg-body-secondary">
        <div class="container d-grid gap-3 align-items-center" style="grid-template-columns: 1fr auto 1fr">
            <div class="d-flex justify-content-start align-items-center mt-1">
                <div v-if="navbarState.title" class="navbar-brand py-0">
                    <button class="btn text-light text-decoration-none back-button" @click="goBack">
                        <i class="bi bi-arrow-left fs-4"></i>
                    </button>
                    {{ navbarState.title }}
                </div>
            </div>
            <div class="d-flex justify-content-center mt-1">
                <div v-if="!navbarState.title" class="navbar-brand align-items-center">
                    <LogoSvg alt="logo" class="logo d-inline-block align-text-top me-1" />
                    RunGoal
                </div>
            </div>
            <div class="d-flex justify-content-end">
                <img
                    v-if="session.user"
                    class="avatar-circle-32"
                    :src="`${session.user.avatar_uri}=s32-c`"
                    :alt="session.user.name"
                    @click="() => openAccountDialog()"
                />
            </div>
        </div>
    </nav>
</template>

<style scoped>
.logo {
    height: 24px;
}
.avatar-circle-32 {
    width: 32px;
    height: 32px;
    border-radius: 50%;
}

.back-button {
    --bs-btn-padding-y: 0.1rem;
}
</style>
