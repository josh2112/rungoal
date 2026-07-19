import { createRouter, createWebHistory } from "vue-router";
import GoalPage from "./pages/GoalPage.vue";
import HomePage from "./pages/HomePage.vue";

export const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        { path: "/", component: HomePage, meta: { isHome: true } },
        { path: "/goal/:index(\\d+)", component: GoalPage, meta: {title: "Goal"} },
        { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
});
