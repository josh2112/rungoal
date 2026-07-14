<script setup lang="ts">
import { useCodeClient } from "vue3-google-signin";
import { useApi } from "../stores/api";
import { useSession } from "../stores/session";

const scopes = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.location.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
];

const api = useApi();
const session = useSession();

const doLoginFlow = async (code?: string) => session.logIn(code);

const { login, isReady } = useCodeClient({
    scope: scopes,
    onSuccess: async (response) => {
        doLoginFlow(response.code);
    },
    onError: (ex) => {
        api.errors.push({
            title: "Request error",
            detail: ex.error_description ?? "",
            source: "local",
        });
    },
});
</script>

<template>
    <div v-if="!session.user">
        <button type="button" class="btn btn-primary" :disabled="!isReady" @click="() => login()">Login with Google
            Health</button>
    </div>
</template>
