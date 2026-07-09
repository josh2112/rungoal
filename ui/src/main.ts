import "bootstrap";
import { createPinia } from 'pinia';
import 'temporal-polyfill/global';
import { createApp } from "vue";
import GoogleSignInPlugin from 'vue3-google-signin';
import App from "./App.vue";
import "./styles/style.css";

const app = createApp(App);

app.use(createPinia()).use(GoogleSignInPlugin, {
    clientId:
        "679282487744-g1g7499ghno2ohs0f1j62eegrt6oud12.apps.googleusercontent.com",
    prompt: 'consent'
});

app.mount("#app");
