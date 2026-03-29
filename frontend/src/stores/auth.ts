import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api, { setAuthToken } from "@/api/client";

const TOKEN_KEY = "vc_token";

export type Role = "admin" | "operator_record" | "operator_verify";

const ROLES: readonly Role[] = ["admin", "operator_record", "operator_verify"];

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
      const r = payload.role;
      if (r && (ROLES as readonly string[]).includes(r)) return r as Role;
      return null;
    } catch {
      return null;
    }
  }

  const canRecord = computed(
    () => role.value === "admin" || role.value === "operator_record"
  );
  const canVerify = computed(
    () => role.value === "admin" || role.value === "operator_verify"
  );

  /** Первый экран после входа */
  function homePath(): string {
    const r = role.value ?? parseJwtRole(token.value ?? "");
    if (r === "operator_verify") return "/history";
    return "/record";
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
    canRecord,
    canVerify,
    parseJwtRole,
    homePath,
    login,
    fetchMe,
    logout,
  };
});
