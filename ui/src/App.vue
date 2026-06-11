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

const error = ref<ApiError>();

const auth = ref<Authorizaton>();

const { login, isReady } = useCodeClient({
    scope: 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',

    onSuccess: async (response) => {
        try {
            const resp = await fetch('http://localhost:8000/api/auth/callback/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: response.code })
            });
            if (!resp.ok) {
                // Try to read the error body if the server sent details
                error.value = await resp.json();
            }
            else {
                auth.value = await resp.json();
            }
        } catch (ex) {
            error.value = {
                title: "Request error",
                detail: ex,
                source: "(local)"
            } as ApiError
        }
    },
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
    <div v-if="error">
        {{ error.title }}: {{ error.detail }} ({{ error.source }})
    </div>
    <div v-if="auth">
        <pre>{{ auth }}</pre>
    </div>
</template>
