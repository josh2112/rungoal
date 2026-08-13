<script setup lang="ts">
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { onMounted } from "vue";
import { authenticatedTileLayer } from "../composables/maplayer";
import { navbarState } from "../models/misc";

onMounted(() => {
    navbarState.title = "Heatmap";

    const map = L.map("map").setView([35.2271, -80.8431], 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    /* L.tileLayer(`${import.meta.env.BASE_URL.replace(/\/$/, "")}/api/heatmap/{z}/{x}/{y}.png`, {
        maxZoom: 19,
        opacity: 0.7, // Lets the background map show through nicely
    }).addTo(map);*/
    authenticatedTileLayer({
        maxZoom: 19,
        opacity: 0.7, // Lets the background map show through nicely
    }).addTo(map);
});
</script>

<template><div id="map" style="height: 100vh; width: 100%"></div></template>
