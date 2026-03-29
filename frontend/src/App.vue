<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { onMounted } from "vue";

const auth = useAuthStore();
const route = useRoute();

onMounted(async () => {
  if (auth.isAuthenticated && !auth.username) {
    try {
      await auth.fetchMe();
    } catch {
      auth.logout();
    }
  }
});
</script>

<template>
  <header v-if="auth.isAuthenticated" class="nav">
    <RouterLink v-if="auth.canRecord" to="/record">Запись</RouterLink>
    <RouterLink to="/history">История</RouterLink>
    <RouterLink v-if="auth.role === 'admin'" to="/admin">Пользователи</RouterLink>
    <span style="margin-left: auto">{{ auth.username }}</span>
    <button type="button" class="btn btn-secondary" style="margin-left: 0.5rem" @click="auth.logout(); $router.push('/login')">
      Выход
    </button>
  </header>
  <main style="padding: 1rem">
    <RouterView :key="route.fullPath" />
  </main>
</template>
