<script setup lang="ts">
import { useEventSource } from '@vueuse/core';
import Account from './components/Account.vue';
import { useApi } from './stores/api.ts';
import "./styles/style.scss";

const api = useApi();
const { data, status, error } = useEventSource(`/sync?token=${api.accessToken}`)

function sync() {

}
</script>

<template>
    <Account />

    <button @onclick="sync">Sync</button>
</template>
