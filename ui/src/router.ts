import { createRouter, createWebHistory } from "vue-router";
import GoalPage from "./pages/GoalPage.vue";
import HomePage from "./pages/HomePage.vue";
import NotableRunsPage from "./pages/NotableRunsPage.vue";
import RouteNotFoundPage from "./pages/RouteNotFoundPage.vue";
import RunPage from "./pages/RunPage.vue";
import { useSession } from "./stores/session.ts";

export const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        { path: "/", component: HomePage },
        {
            path: "/goal/:id",
            component: GoalPage,
            beforeEnter: async (to, _, next) => {
                const session = useSession();
                if (session.goals.find((g) => g.id == to.params.id)) next();
                else next({ name: "404" });
            },
        },
        {
            path: "/run/:id",
            component: RunPage,
            beforeEnter: async (to, _, next) => {
                const session = useSession();
                if (
                    session.runs
                        .concat(Object.values(session.notableRuns?.runs ?? {}))
                        .find((r) => r.id == to.params.id)
                )
                    next();
                else next({ name: "404" });
            },
        },

        { path: "/runs/notable", component: NotableRunsPage },
        { path: "/:pathMatch(.*)*", name: "404", component: RouteNotFoundPage },
    ],
});
