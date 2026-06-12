<script setup lang="ts">
import { useCodeClient } from 'vue3-google-signin';
import { useApi } from '../stores/api';
import { useSession } from '../stores/session';

const api = useApi();
const session = useSession();

const doLoginFlow = async (code?: string) => session.logIn(code)

const { login, isReady } = useCodeClient({
    scope: 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',
    onSuccess: async (response) => { doLoginFlow(response.code) },
    onError: (ex) => {
        api.errors.push({
            title: "Request error",
            detail: ex.error_description ?? '',
            source: "local"
        });
    },
});

</script>

<template>
    <img v-if="session.user" class="avatar" :src="`${session.user.avatar_uri}=s32-c`" :alt="session.user.name"
        data-bs-toggle="modal" data-bs-target="#accountModal" />
    <div v-else>
        <button type="button" class="btn btn-primary" :disabled="!isReady" @click="() => login()">
            Login
        </button>
        <button type="button" class="btn btn-primary" @click="() => doLoginFlow()">
            Login (dev)
        </button>
    </div>

    <div class="modal fade" id="accountModal" tabindex="-1" aria-labelledby="modalTitle" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="modalTitle">Account</h1>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="account-box">
                        <img class="avatar" :src="`${session.user?.avatar_uri}=s64-c`" />
                        <div>
                            <div class="user-name">{{ session.user?.name }}</div>
                            <div>{{ session.user?.email }}</div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal"
                        @click="() => session.logOut()">Log out</button>
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
