<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import LogoSvg from "../../assets/logo.svg";
import AccountDialog from "../dialogs/AccountDialog.vue";
import { navbarState } from "../models/misc.ts";
import { useSession } from "../stores/session.ts";

const session = useSession();

const accountDialogRef = ref<InstanceType<typeof AccountDialog>>();

const router = useRouter();

const goBack = () => {
    if (window.history.length > 1) {
        router.back();
    } else {
        router.push("/");
    }
};

const fart = () => {
    console.log("fart", accountDialogRef.value);
    accountDialogRef.value?.open();
}
</script>

<template>
    <nav class="navbar sticky-top bg-body-secondary">
        <div class="container d-grid gap-3 align-items-center" style="grid-template-columns: 1fr auto 1fr">
            <div class="d-flex justify-content-start mt-1">
                <div v-if="navbarState.title" class="navbar-brand py-0">
                    <button class="btn text-light text-decoration-none navbar-button" @click="goBack">
                        <i class="bi bi-arrow-left fs-4"></i>
                    </button>
                    <span class="align-middle">{{ navbarState.title }}</span>
                </div>
            </div>
            <div class="d-flex justify-content-center mt-1">
                <div v-if="!navbarState.title" class="navbar-brand align-items-center">
                    <LogoSvg alt="logo" class="logo d-inline-block align-text-top me-1" />
                    RunGoal
                </div>
            </div>
            <div class="d-flex justify-content-end">
                <button v-for="action in navbarState.actions" :key="action.icon"
                    class="btn text-light text-decoration-none navbar-button" @click="() => action.callback()">
                    <i class="bi" :class="action.icon"></i></button>
                <a href='#' @click="() => fart()"><img v-if="session.user" class="avatar-circle-32 ms-3"
                        :src="`${session.user.avatar_uri}=s32-c`" :alt="session.user.name" /></a>
            </div>
        </div>
    </nav>

    <AccountDialog ref="accountDialogRef" />
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

.navbar-button {
    --bs-btn-padding-y: 0.1rem;
}
</style>
