<script setup lang="ts">
import { useCodeClient } from 'vue3-google-signin';

const { login, isReady } = useCodeClient({
    scope: 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',

    onSuccess: async (response) => {
        try {
            const req = await fetch('http://localhost:8000/api/auth/callback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: response.code })
            });
            await req.json()
        } catch (error) {
            console.error('Login failed', error);
        }
    },
    onError: (error) => {
        console.error('Login failed', error);
    },
});
</script>

<template>
    <button :disabled="!isReady" @click="() => login()">
        Login
    </button>
</template>
