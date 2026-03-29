<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/client";
import { getApiErrorMessage } from "@/api/errors";

const router = useRouter();
const recording = ref(false);
const err = ref("");
const mediaRecorder = ref<MediaRecorder | null>(null);
const chunks = ref<Blob[]>([]);

async function start() {
  err.value = "";
  chunks.value = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : undefined;
  const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
  mediaRecorder.value = mr;
  mr.ondataavailable = (e) => {
    if (e.data.size) chunks.value.push(e.data);
  };
  mr.onstop = () => stream.getTracks().forEach((t) => t.stop());
  // Интервал даёт куски данных до stop — иначе в части браузеров финальный chunk опоздает.
  mr.start(250);
  recording.value = true;
}

async function stopAndSend() {
  err.value = "";
  const mr = mediaRecorder.value;
  if (!mr || mr.state === "inactive") {
    recording.value = false;
    return;
  }
  await new Promise<void>((resolve) => {
    mr.addEventListener("stop", () => resolve(), { once: true });
    mr.stop();
  });
  recording.value = false;
  mediaRecorder.value = null;
  const blob = new Blob(chunks.value, { type: "audio/webm" });
  if (!blob.size) {
    err.value = "Запись пустая — разрешите микрофон и попробуйте ещё раз.";
    return;
  }
  const fd = new FormData();
  fd.append("file", blob, "record.webm");
  try {
    const { data } = await api.post("/api/voice-commands", fd);
    await router.push({ name: "detail", params: { id: String(data.id) } });
  } catch (e) {
    err.value = getApiErrorMessage(
      e,
      "Ошибка отправки. Проверьте бэкенд, ffmpeg и модель VOSK.",
    );
  }
}
</script>

<template>
  <div class="card">
    <h1>Запись команды</h1>
    <p>«Начать» → произнесите команду → «Стоп и отправить».</p>
    <p v-if="err" class="error">{{ err }}</p>
    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
      <button type="button" class="btn" :disabled="recording" @click="start">Начать запись</button>
      <button type="button" class="btn btn-secondary" :disabled="!recording" @click="stopAndSend">Стоп и отправить</button>
    </div>
    <p v-if="recording" style="color: #c62828; font-weight: 600">Идёт запись…</p>
  </div>
</template>