import { defineStore } from "pinia";
import { onMounted, ref } from "vue";
import type { User } from "../models";
import { useApi } from "./api";

export const useSession = defineStore('session', () => {
    const api = useApi();

    const user = ref<User | null>(null);

    onMounted(async () => {
        await getMe();
    });

    async function logIn(google_access_code?: string) {
        api.post(`/auth/${google_access_code ? 'google' : 'dev'}`,
            google_access_code ? JSON.stringify({ google_access_code }) : undefined
        );

        await getMe();
    }

    function logOut() {
        api.get('/auth/logout');
        api.accessToken = null;
        user.value = null;
    }

    async function getMe() {
        user.value = (await api.get('/user/me')).data;
    }

    return { user, logIn, logOut }
});