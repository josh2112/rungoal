<script setup lang="ts">
import { useSession } from "../stores/session";

const session = useSession();
</script>

<template>
    <div class="account-box">
        <img class="avatar" :src="`${session.user?.avatar_uri}=s64-c`" />
        <div>
            <div class="user-name">
                {{ session.user?.name }}
            </div>
            <div>{{ session.user?.email }}</div>
        </div>
    </div>
</template>

<style scoped>
.avatar {
    width: 64px;
    height: 64px;
    border-radius: 32px;
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
