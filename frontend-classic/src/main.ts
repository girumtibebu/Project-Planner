import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";
import "./design/tokens.css";
import { ensureCsrfToken } from "./composables/useFrappe";

// Lazy-loaded pages
const Landing = () => import("./pages/Landing.vue");
const Brief = () => import("./pages/Brief.vue");
const Action = () => import("./pages/Action.vue");
const Timeline = () => import("./pages/TimeWorkspace.vue");
const Schedule = () => import("./pages/Schedule.vue");
const Debrief = () => import("./pages/Debrief.vue");

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/:project/landing",
      component: Landing,
    },
    {
      path: "/:project/brief",
      component: Brief,
    },
    {
      path: "/:project/action",
      component: Action,
    },
    {
      path: "/:project/timeline",
      component: Timeline,
    },
    {
      path: "/:project/schedule",
      component: Schedule,
    },
    {
      path: "/:project/debrief",
      component: Debrief,
    },
    // Default redirect
    {
      path: "/:project",
      redirect: (to) => `/${to.params.project}/landing`,
    },
  ],
});

async function start() {
  try {
    await ensureCsrfToken();
  } catch (e) {
    console.warn("[event_planner] CSRF prefetch failed:", e);
  }
  const app = createApp(App);
  app.use(router);
  app.mount("#app");
}

start();
