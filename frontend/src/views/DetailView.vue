<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import api from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const auth = useAuthStore();

const row = ref<{
  id: number;
  raw_transcript: string;
  edited_transcript: string | null;
  parsed_command: string | null;
  parsed_identifier: string | null;
  recorded_at: string;
  confirmed: boolean;
  operator_username: string;
} | null>(null);

const edited = ref("");
const err = ref("");
const audioUrl = ref<string | null>(null);

async function load() {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value);
    audioUrl.value = null;
  }
  const id = route.params.id as string;
  err.value = "";
  try {
    const { data } = await api.get(`/api/voice-commands/${id}`);
    row.value = data;
    edited.value = data.edited_transcript ?? data.raw_transcript ?? "";
    const res = await fetch(`/api/voice-commands/${id}/audio`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (res.ok) {
      const blob = await res.blob();
      audioUrl.value = URL.createObjectURL(blob);
    }
  } catch {
    err.value = "Ошибка загрузки";
  }
}

async function saveEdit() {
  if (!row.value) return;
  try {
    const { data } = await api.patch(`/api/voice-commands/${row.value.id}`, {
      edited_transcript: edited.value,
    });
    row.value = data;
  } catch {
    err.value = "Ошибка сохранения";
  }
}

async function confirm() {
  if (!row.value) return;
  try {
    const { data } = await api.patch(`/api/voice-commands/${row.value.id}`, { confirmed: true });
    row.value = data;
  } catch {
    err.value = "Ошибка подтверждения";
  }
}

onMounted(load);
watch(
  () => route.params.id,
  () => load()
);
</script>

<template>
  <div v-if="row" class="card" style="max-width: 720px">
    <h1>Запись #{{ row.id }}</h1>
    <p><strong>Оператор:</strong> {{ row.operator_username }}</p>
    <p><strong>Время:</strong> {{ new Date(row.recorded_at).toLocaleString() }}</p>
    <p><strong>Команда:</strong> {{ row.parsed_command || "—" }}</p>
    <p><strong>Идентификатор:</strong> {{ row.parsed_identifier || "—" }}</p>
    <div v-if="audioUrl" class="field">
      <label>Аудио</label>
      <audio :src="audioUrl" controls style="width: 100%" />
    </div>
    <div class="field">
      <label>Текст (правка)</label>
      <textarea v-model="edited" rows="4" />
    </div>
    <p v-if="err" class="error">{{ err }}</p>
    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
      <button type="button" class="btn btn-secondary" @click="saveEdit">Сохранить правку</button>
      <button type="button" class="btn" @click="confirm">Подтвердить</button>
    </div>
    <p v-if="row.confirmed"><strong>Подтверждено</strong></p>
  </div>
</template>
