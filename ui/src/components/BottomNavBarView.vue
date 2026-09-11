<template>
    <nav class="navbar fixed-bottom navbar-dark bg-body-secondary">
        <div
            class="container d-grid gap-3 align-items-center"
            style="grid-template-columns: 1fr auto 1fr"
        >
            <router-link to="/" class="nav-link text-center text-white">
                <i class="bi bi-house-door fs-4 d-block"></i>
                <span class="small">Runs</span>
            </router-link>

            <router-link to="/heatmap" class="nav-link text-center text-white">
                <i class="bi bi-map fs-4 d-block"></i>
                <span class="small">Heatmap</span>
            </router-link>

            <router-link to="/runs/notable" class="nav-link text-center text-white">
                <i class="bi bi-award fs-4 d-block"></i>
                <span class="small">Records</span>
            </router-link>
        </div>
    </nav>
</template>
