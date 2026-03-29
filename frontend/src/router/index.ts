import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/record" },
    { path: "/login", name: "login", component: () => import("@/views/LoginView.vue"), meta: { guest: true } },
    { path: "/register", name: "register", component: () => import("@/views/RegisterView.vue"), meta: { guest: true } },
    { path: "/record", name: "record", component: () => import("@/views/RecordView.vue"), meta: { auth: true } },
    { path: "/history", name: "history", component: () => import("@/views/HistoryView.vue"), meta: { auth: true } },
    { path: "/history/:id", name: "detail", component: () => import("@/views/DetailView.vue"), meta: { auth: true } },
    { path: "/admin", name: "admin", component: () => import("@/views/AdminView.vue"), meta: { auth: true, admin: true } },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { name: "record" };
  }
  if (to.meta.admin) {
    if (!auth.isAuthenticated) return { name: "login" };
    if (auth.role !== "admin") {
      if (!auth.role && auth.token) {
        try {
          await auth.fetchMe();
        } catch {
          return { name: "login" };
        }
      }
      if (auth.role !== "admin") return { name: "record" };
    }
  }
  return true;
});

export default router;
