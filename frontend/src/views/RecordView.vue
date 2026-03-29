<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/client";
import { getApiErrorMessage } from "@/api/errors";

const router = useRouter();

type Phase = "idle" | "recording" | "processing" | "preview";

const phase = ref<Phase>("idle");
const recording = ref(false);
const err = ref("");
const processing = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const chunks = ref<Blob[]>([]);
const canvasRef = ref<HTMLCanvasElement | null>(null);

const previewId = ref<string | null>(null);
const previewTranscript = ref("");
const previewCommand = ref<string | null>(null);
const previewIdentifier = ref<string | null>(null);

let audioContext: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let freqData: Uint8Array | null = null;
let rafId = 0;
let vizActive = false;

function stopViz() {
  vizActive = false;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = 0;
  void audioContext?.close();
  audioContext = null;
  analyser = null;
  freqData = null;
  const c = canvasRef.value;
  const ctx = c?.getContext("2d");
  if (c && ctx) {
    ctx.clearRect(0, 0, c.width, c.height);
  }
}

function drawLevel() {
  if (!vizActive || !analyser || !freqData || !canvasRef.value) return;
  const canvas = canvasRef.value;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  analyser.getByteFrequencyData(freqData);
  const dpr = window.devicePixelRatio || 1;
  const cssW = 320;
  const cssH = 72;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = "#e8eef2";
  ctx.fillRect(0, 0, cssW, cssH);
  const bars = 32;
  const step = Math.max(1, Math.floor(freqData.length / bars));
  const barW = cssW / bars;
  for (let i = 0; i < bars; i++) {
    let sum = 0;
    for (let j = 0; j < step; j++) sum += freqData[i * step + j] ?? 0;
    const avg = sum / step / 255;
    const bh = Math.max(2, avg * cssH * 0.92);
    ctx.fillStyle = "#1565c0";
    ctx.fillRect(i * barW + 0.5, cssH - bh, Math.max(1, barW - 1), bh);
  }
  if (vizActive) rafId = requestAnimationFrame(drawLevel);
}

function startViz(stream: MediaStream) {
  stopViz();
  const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return;
  audioContext = new Ctor();
  void audioContext.resume();
  const source = audioContext.createMediaStreamSource(stream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.82;
  source.connect(analyser);
  freqData = new Uint8Array(analyser.frequencyBinCount);
  const c = canvasRef.value;
  if (c) {
    const dpr = window.devicePixelRatio || 1;
    const logicalW = 320;
    const logicalH = 72;
    c.width = Math.floor(logicalW * dpr);
    c.height = Math.floor(logicalH * dpr);
    c.style.width = `${logicalW}px`;
    c.style.height = `${logicalH}px`;
  }
  vizActive = true;
  drawLevel();
}

function clearPreview() {
  previewId.value = null;
  previewTranscript.value = "";
  previewCommand.value = null;
  previewIdentifier.value = null;
  phase.value = "idle";
}

async function start() {
  err.value = "";
  clearPreview();
  chunks.value = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : undefined;
  const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
  mediaRecorder.value = mr;
  mr.ondataavailable = (e) => {
    if (e.data.size) chunks.value.push(e.data);
  };
  mr.onstop = () => stream.getTracks().forEach((t) => t.stop());
  recording.value = true;
  phase.value = "recording";
  startViz(stream);
  mr.start(250);
}

async function stopAndRecognize() {
  err.value = "";
  const mr = mediaRecorder.value;
  if (!mr || mr.state === "inactive") {
    recording.value = false;
    stopViz();
    phase.value = "idle";
    return;
  }
  await new Promise<void>((resolve) => {
    mr.addEventListener("stop", () => resolve(), { once: true });
    mr.stop();
  });
  recording.value = false;
  stopViz();
  mediaRecorder.value = null;
  const blob = new Blob(chunks.value, { type: "audio/webm" });
  if (!blob.size) {
    err.value = "Запись пустая — разрешите микрофон и попробуйте ещё раз.";
    phase.value = "idle";
    return;
  }
  processing.value = true;
  phase.value = "processing";
  const fd = new FormData();
  fd.append("file", blob, "record.webm");
  try {
    const { data } = await api.post<{
      preview_id: string;
      raw_transcript: string;
      parsed_command: string | null;
      parsed_identifier: string | null;
    }>("/api/voice-commands/preview", fd);
    previewId.value = data.preview_id;
    previewTranscript.value = data.raw_transcript;
    previewCommand.value = data.parsed_command;
    previewIdentifier.value = data.parsed_identifier;
    phase.value = "preview";
  } catch (e) {
    err.value = getApiErrorMessage(
      e,
      "Ошибка распознавания. Проверьте бэкенд, ffmpeg и модель VOSK.",
    );
    phase.value = "idle";
    clearPreview();
  } finally {
    processing.value = false;
  }
}

async function saveToHistory() {
  if (!previewId.value) return;
  err.value = "";
  try {
    const { data } = await api.post<{ id: number }>("/api/voice-commands/confirm", {
      preview_id: previewId.value,
    });
    clearPreview();
    await router.push({ name: "detail", params: { id: String(data.id) } });
  } catch (e) {
    err.value = getApiErrorMessage(e, "Не удалось сохранить запись.");
  }
}

function discardAndRecordAgain() {
  clearPreview();
  err.value = "";
}
</script>

<template>
  <div class="card">
    <h1>Запись команды</h1>
    <p>«Начать запись» → произнесите команду → «Стоп» → проверьте результат → «Сохранить в историю» или «Перезаписать».</p>
    <p v-if="err" class="error">{{ err }}</p>

    <template v-if="phase !== 'preview'">
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center">
        <button type="button" class="btn" :disabled="recording || processing" @click="start">Начать запись</button>
        <button type="button" class="btn btn-secondary" :disabled="!recording || processing" @click="stopAndRecognize">
          Стоп
        </button>
        <span v-if="processing" class="hint">Распознаём…</span>
      </div>
      <div v-show="recording" class="record-viz-wrap">
        <p class="record-viz-caption">Идёт запись — уровень сигнала с микрофона</p>
        <canvas ref="canvasRef" class="record-viz-canvas" width="320" height="72" />
      </div>
    </template>

    <div v-else class="preview-block">
      <h2>Результат распознавания</h2>
      <p><strong>Текст:</strong> {{ previewTranscript || "—" }}</p>
      <p><strong>Команда:</strong> {{ previewCommand || "—" }}</p>
      <p><strong>Параметр (ID):</strong> {{ previewIdentifier || "—" }}</p>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem">
        <button type="button" class="btn" @click="saveToHistory">Сохранить в историю</button>
        <button type="button" class="btn btn-secondary" @click="discardAndRecordAgain">Перезаписать</button>
      </div>
    </div>
  </div>
</template>
