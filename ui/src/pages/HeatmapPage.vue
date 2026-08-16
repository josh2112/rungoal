<script setup lang="ts">
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { onMounted, ref, watch } from "vue";
import { navbarState } from "../models/misc";
import { useApi } from "../stores/api";
import { useSession } from "../stores/session";

const session = useSession();
const api = useApi();

const map = ref<L.Map>();

onMounted(() => {
    navbarState.title = "Heatmap";

    map.value = L.map("map").setView([35.2271, -80.8431], 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map.value);

    if (session.user != null) {
        installMapLayer();
    }
});

const installMapLayer = () => {
    L.tileLayer(`${import.meta.env.BASE_URL.replace(/\/$/, "")}/api/heatmap/{z}/{x}/{y}.png?token=${api.accessToken}`, {
        maxZoom: 19,
        opacity: 0.7,
    }).addTo(map.value!);
    /*authenticatedTileLayer({
        maxZoom: 19,
        opacity: 0.7,
    }).addTo(map.value!);*/
};

watch(
    () => session.user,
    (prevUser, user) => {
        if (user && !prevUser) {
            installMapLayer();
        }
    },
);
</script>

<template>
    <div id="map" style="height: 100vh; width: 100%"></div>
</template>
