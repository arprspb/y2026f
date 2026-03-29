<script setup lang="ts">
import { onMounted, ref } from "vue";
import api from "@/api/client";
import { getApiErrorMessage } from "@/api/errors";

type OpRole = "operator_record" | "operator_verify";

interface U {
  id: number;
  username: string;
  role: "admin" | OpRole;
  is_active: boolean;
}

const users = ref<U[]>([]);
const newUsername = ref("");
const newPassword = ref("");
const newRole = ref<OpRole>("operator_record");
const err = ref("");

async function load() {
  err.value = "";
  try {
    const { data } = await api.get<U[]>("/api/users");
    users.value = data;
  } catch (e) {
    err.value = getApiErrorMessage(e, "Нет доступа или ошибка сети");
  }
}

async function createUser() {
  err.value = "";
  try {
    await api.post("/api/users", {
      username: newUsername.value,
      password: newPassword.value,
      role: newRole.value,
    });
    newUsername.value = "";
    newPassword.value = "";
    await load();
  } catch (e) {
    err.value = getApiErrorMessage(e, "Не удалось создать пользователя");
  }
}

async function toggleBlock(u: U) {
  await api.patch(`/api/users/${u.id}`, { is_active: !u.is_active });
  await load();
}

async function setRole(u: U, role: OpRole) {
  await api.patch(`/api/users/${u.id}`, { role });
  await load();
}

onMounted(load);
</script>

<template>
  <div class="card" style="max-width: 720px">
    <h1>Пользователи</h1>
    <p v-if="err" class="error">{{ err }}</p>

    <h2>Новый пользователь</h2>
    <form class="row" @submit.prevent="createUser">
      <input v-model="newUsername" placeholder="Логин" required />
      <input v-model="newPassword" type="password" placeholder="Пароль" required />
      <select v-model="newRole">
        <option value="operator_record">Оператор (запись)</option>
        <option value="operator_verify">Оператор (проверка)</option>
      </select>
      <button type="submit" class="btn">Создать</button>
    </form>
    <p style="font-size: 0.9rem; color: var(--muted, #666)">
      Роль администратора задаётся только через переменные окружения при первом запуске API.
    </p>

    <table class="table">
      <thead>
        <tr>
          <th>Логин</th>
          <th>Роль</th>
          <th>Активен</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.username }}</td>
          <td>
            <span v-if="u.role === 'admin'">Администратор</span>
            <select
              v-else
              :value="u.role"
              @change="setRole(u, ($event.target as HTMLSelectElement).value as OpRole)"
            >
              <option value="operator_record">Оператор (запись)</option>
              <option value="operator_verify">Оператор (проверка)</option>
            </select>
          </td>
          <td>{{ u.is_active ? "да" : "заблокирован" }}</td>
          <td>
            <button type="button" class="btn btn-danger" @click="toggleBlock(u)">
              {{ u.is_active ? "Блокировать" : "Разблокировать" }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
