<script setup lang="ts">
import LogoSvg from '../../assets/logo.svg';
import { useDialogs } from '../stores/dialogs.ts';
import { useSession } from '../stores/session.ts';
import Sync from './Sync.vue';

const session = useSession();
const dialogs = useDialogs();

const openAccountDialog = () => {
    dialogs.isAccountDialogOpen = true;
}
</script>

<template>
    <nav class="navbar sticky-top bg-body-secondary">
        <div class="container">
            <div class="navbar-brand">
                <LogoSvg alt="logo" class="logo d-inline-block align-text-top me-1" />
                RunGoal
            </div>
            <div class="d-flex">
                <Sync />
                <img v-if="session.user" class="avatar-circle" :src="`${session.user.avatar_uri}=s32-c`"
                    :alt="session.user.name" @click="() => openAccountDialog()" />
            </div>
        </div>
    </nav>
</template>

<style scoped>
.logo {
    height: 24px;
}
</style
