<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const err = ref("");

async function submit() {
  err.value = "";
  try {
    await auth.register(username.value, password.value);
    await auth.login(username.value, password.value);
    await router.push("/record");
  } catch {
    err.value = "Не удалось зарегистрироваться";
  }
}
</script>

<template>
  <div class="card">
    <h1>Регистрация</h1>
    <p class="hint">Первый зарегистрированный пользователь получает роль администратора.</p>
    <form @submit.prevent="submit">
      <div class="field">
        <label>Логин</label>
        <input v-model="username" required minlength="2" autocomplete="username" />
      </div>
      <div class="field">
        <label>Пароль</label>
        <input v-model="password" type="password" required minlength="4" autocomplete="new-password" />
      </div>
      <p v-if="err" class="error">{{ err }}</p>
      <button type="submit" class="btn">Создать аккаунт</button>
    </form>
    <p><RouterLink to="/login">Уже есть аккаунт</RouterLink></p>
  </div>
</template>
