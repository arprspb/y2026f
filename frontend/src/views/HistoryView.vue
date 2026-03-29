<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import api from "@/api/client";
import { getApiErrorMessage } from "@/api/errors";

export interface Row {
  id: number;
  raw_transcript: string;
  edited_transcript: string | null;
  parsed_command: string | null;
  parsed_identifier: string | null;
  recorded_at: string;
  confirmed: boolean;
  operator_username: string;
  confirmed_by_username: string | null;
}

const rows = ref<Row[]>([]);
const qCommand = ref("");
const qId = ref("");
const qOp = ref("");
const dateFrom = ref("");
const dateTo = ref("");
const err = ref("");

async function load() {
  err.value = "";
  try {
    const params: Record<string, string> = {};
    if (qCommand.value) params.parsed_command = qCommand.value;
    if (qId.value) params.parsed_identifier = qId.value;
    if (qOp.value) params.operator_username = qOp.value;
    if (dateFrom.value) params.date_from = new Date(dateFrom.value).toISOString();
    if (dateTo.value) params.date_to = new Date(dateTo.value).toISOString();
    const { data } = await api.get<Row[]>("/api/voice-commands", { params });
    rows.value = data;
  } catch (e) {
    err.value = getApiErrorMessage(e, "Не удалось загрузить историю");
  }
}

onMounted(load);
</script>

<template>
  <div class="card" style="max-width: 900px">
    <h1>История</h1>
    <form class="filters" @submit.prevent="load">
      <div class="field">
        <label>Команда (фрагмент)</label>
        <input v-model="qCommand" />
      </div>
      <div class="field">
        <label>Параметр</label>
        <input v-model="qId" />
      </div>
      <div class="field">
        <label>Оператор</label>
        <input v-model="qOp" />
      </div>
      <div class="field">
        <label>Дата с</label>
        <input v-model="dateFrom" type="datetime-local" />
      </div>
      <div class="field">
        <label>Дата по</label>
        <input v-model="dateTo" type="datetime-local" />
      </div>
      <button type="submit" class="btn">Фильтровать</button>
    </form>
    <p v-if="err" class="error">{{ err }}</p>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Команда</th>
          <th>ID параметра</th>
          <th>Оператор</th>
          <th>Подтвердил</th>
          <th>Время</th>
          <th>Подтв.</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>
            <RouterLink :to="`/history/${r.id}`">{{ r.id }}</RouterLink>
          </td>
          <td>{{ r.parsed_command || "—" }}</td>
          <td>{{ r.parsed_identifier || "—" }}</td>
          <td>{{ r.operator_username }}</td>
          <td>{{ r.confirmed_by_username || "—" }}</td>
          <td>{{ new Date(r.recorded_at).toLocaleString() }}</td>
          <td>{{ r.confirmed ? "да" : "нет" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
