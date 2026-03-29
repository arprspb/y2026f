import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api, { setAuthToken } from "@/api/client";

const TOKEN_KEY = "vc_token";

export type Role = "admin" | "operator";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const username = ref<string | null>(null);
  const role = ref<Role | null>(null);

  if (token.value) {
    setAuthToken(token.value);
  }

  const isAuthenticated = computed(() => !!token.value);

  function parseJwtRole(t: string): Role | null {
    try {
      const payload = JSON.parse(atob(t.split(".")[1])) as { role?: string };
      return payload.role === "admin" ? "admin" : "operator";
    } catch {
      return null;
    }
  }

  async function login(u: string, password: string) {
    const { data } = await api.post<{ access_token: string }>("/api/auth/login", {
      username: u,
      password,
    });
    token.value = data.access_token;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setAuthToken(data.access_token);
    username.value = u;
    role.value = parseJwtRole(data.access_token);
  }

  async function register(u: string, password: string, passwordConfirm: string) {
    await api.post("/api/auth/register", {
      username: u,
      password,
      password_confirm: passwordConfirm,
    });
  }

  async function fetchMe() {
    const { data } = await api.get<{ username: string; role: Role }>("/api/users/me");
    username.value = data.username;
    role.value = data.role;
  }

  function logout() {
    token.value = null;
    username.value = null;
    role.value = null;
    localStorage.removeItem(TOKEN_KEY);
    setAuthToken(null);
  }

  return {
    token,
    username,
    role,
    isAuthenticated,
    login,
    register,
    fetchMe,
    logout,
  };
});
