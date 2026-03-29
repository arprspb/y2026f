<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { getApiErrorMessage } from "@/api/errors";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const username = ref("");
const password = ref("");
const err = ref("");

async function submit() {
  err.value = "";
  try {
    await auth.login(username.value, password.value);
    const redirect = (route.query.redirect as string) || "/record";
    await router.push(redirect);
  } catch (e) {
    err.value = getApiErrorMessage(e, "Неверный логин или пароль");
  }
}
</script>

<template>
  <div class="card">
    <h1>Вход</h1>
    <form @submit.prevent="submit">
      <div class="field">
        <label>Логин</label>
        <input v-model="username" required autocomplete="username" />
      </div>
      <div class="field">
        <label>Пароль</label>
        <input v-model="password" type="password" required autocomplete="current-password" />
      </div>
      <p v-if="err" class="error">{{ err }}</p>
      <button type="submit" class="btn">Войти</button>
    </form>
    <p><RouterLink to="/register">Регистрация</RouterLink></p>
  </div>
</template>
