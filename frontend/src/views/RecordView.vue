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
const canvasRef = ref<HTMLCanvasElement | null>(null);

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
  recording.value = true;
  startViz(stream);
  mr.start(250);
}

async function stopAndSend() {
  err.value = "";
  const mr = mediaRecorder.value;
  if (!mr || mr.state === "inactive") {
    recording.value = false;
    stopViz();
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
    <div v-show="recording" class="record-viz-wrap">
      <p class="record-viz-caption">Идёт запись — уровень сигнала с микрофона</p>
      <canvas ref="canvasRef" class="record-viz-canvas" width="320" height="72" />
    </div>
  </div>
</template>
