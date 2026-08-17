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

const hasMapMoved = ref(false);

onMounted(() => {
    navbarState.title = "Heatmap";

    map.value = L.map("map").setView([0, 0], 13);
    map.value.on("movestart", () => (hasMapMoved.value = true));

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map.value);

    maybeInstallHeatmapLayer();
    maybeSetInitialView();
});

const maybeInstallHeatmapLayer = () => {
    if (session.user) {
        L.tileLayer(
            `${import.meta.env.BASE_URL.replace(/\/$/, "")}/api/heatmap/{z}/{x}/{y}.png?token=${api.accessToken}`,
            {
                maxZoom: 19,
                opacity: 0.7,
            },
        ).addTo(map.value!);
    }
};

const maybeSetInitialView = () => {
    if (session.runs) {
        const bbox = session.runs.find((r) => r.bbox)?.bbox;
        if (bbox) {
            // Pad the bouding box by 20%
            const wpad = (bbox[2] - bbox[0]) * 0.2;
            const hpad = (bbox[3] - bbox[1]) * 0.2;
            const mapBounds: L.LatLngBoundsExpression = [
                [bbox[1] - hpad, bbox[0] - wpad],
                [bbox[3] + hpad, bbox[2] + wpad],
            ];
            map.value?.fitBounds(mapBounds);
        }
        // TODO
    }
};

watch(
    () => session.runs,
    (_) => maybeSetInitialView(),
);

watch(
    () => session.user,
    (prevUser, user) => {
        if (user && !prevUser) {
            maybeInstallHeatmapLayer();
        }
    },
);
</script>

<template>
    <div id="map" style="height: 100vh; width: 100%"></div>
</template>
