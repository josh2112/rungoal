<script setup lang="ts">
import type { CallbackTypes } from "vue3-google-login";

const handleLogin: CallbackTypes.CodeResponseCallback = async (response) => {
    console.log("Auth code", response);

    try {
        const res = await fetch('http://localhost:8000/api/auth/callback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: response.code })
        });
        const data = await res.json();
        console.log('Tokens saved on backend', data);
    } catch (error) {
        console.error('Login failed', error);
    }
};

const googleInitOptions = {
    response_type: 'code',
    access_type: 'offline',
    prompt: 'consent' // Forces consent screen to guarantee refresh token is issued
}
</script>

<template>
    <GoogleLogin :callback="handleLogin" request-code popup-type="CODE">
        <button>login</button>
    </GoogleLogin>

</template>
