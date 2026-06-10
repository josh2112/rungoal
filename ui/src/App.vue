<script setup lang="ts">
import type { CallbackTypes } from "vue3-google-login";

const callback: CallbackTypes.CodeResponseCallback = (response) => {
    console.log("Auth code", response);
};
</script>

<template>
    <GoogleLogin :callback="callback" />
</template>
