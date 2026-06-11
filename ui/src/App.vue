<script setup lang="ts">
import { ref } from 'vue';
import { useCodeClient } from 'vue3-google-signin';

interface ApiError {
    title: string
    detail: string
    source: string
}

interface Authorizaton {
    access_token: string
    refresh_token: string
}

interface User {
    name: string
    email: string
    avatar_uri: string
}

const error = ref<ApiError>();
const auth = ref<Authorizaton>();
const user = ref<User>();

const doLoginFlow = async (code?: string) => {
    try {
        let resp = await fetch(`http://localhost:8000/api/auth/${code ? 'google' : 'dev'}`, {
            method: code ? 'POST' : 'GET',
            headers: { 'Content-Type': 'application/json' },
            body: code ? JSON.stringify({ code }) : undefined
        });

        if (!resp.ok) {
            error.value = await resp.json();
            return;
        }

        auth.value = await resp.json();

        resp = await fetch('http://localhost:8000/api/user/me', {
            headers: { 'Authorization': `Bearer ${auth.value!.access_token}` }
        })

        if (!resp.ok) {
            error.value = await resp.json();
            return;
        }

        user.value = await resp.json()
    } catch (ex) {
        error.value = {
            title: "Request error",
            detail: ex,
            source: "(local)"
        } as ApiError
    }
}

const { login, isReady } = useCodeClient({
    scope: 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',

    onSuccess: async (response) => { doLoginFlow(response.code) },
    onError: (ex) => {
        error.value = {
            title: "Request error",
            detail: ex,
            source: "local"
        } as ApiError
    },
});

</script>

<template>
    <button :disabled="!isReady" @click="() => login()">
        Login
    </button>
    <button @click="() => doLoginFlow()">
        Login (dev)
    </button>
    <div v-if="error">
        <pre>{{ error }}</pre>
    </div>
    <div v-if="auth">
        <pre>{{ auth }}</pre>
    </div>
    <div v-if="user">
        <div>{{ user.name }}</div>
        <div>{{ user.email }}</div>
        <img :src="user.avatar_uri" />
    </div>
</template>
