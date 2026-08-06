import { createRouter, createWebHistory } from "vue-router";
import GoalPage from "./pages/GoalPage.vue";
import HomePage from "./pages/HomePage.vue";
import NotableRunsPage from "./pages/NotableRunsPage.vue";
import RunPage from "./pages/RunPage.vue";

export const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        { path: "/", component: HomePage },
        { path: "/goal/:index(\\d+)", component: GoalPage },
        { path: "/run/:index(\\d+)", component: RunPage },

        { path: "/runs/notable", component: NotableRunsPage },
        { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
});
