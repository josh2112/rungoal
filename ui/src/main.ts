import { createApp } from "vue";
import vue3GoogleLogin from "vue3-google-login";
import App from "./App.vue";
import "./style.css";

const app = createApp(App);

app.use(vue3GoogleLogin, {
    clientId:
        "679282487744-g1g7499ghno2ohs0f1j62eegrt6oud12.apps.googleusercontent.com",
});

app.mount("#app");
