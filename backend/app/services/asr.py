"""Распознавание речи через VOSK (модель на диске)."""

import json
import wave
from pathlib import Path

from app.config import get_settings

_model = None


def _load_model():
    global _model
    if _model is None:
        from vosk import Model

        path = Path(get_settings().vosk_model_path)
        if not path.is_dir():
            msg = (
                f"Модель VOSK не найдена: {path}. "
                "Скачайте vosk-model-small-ru-0.22 и укажите VOSK_MODEL_PATH в .env"
            )
            raise RuntimeError(msg)
        _model = Model(str(path))
    return _model


def transcribe_wav_file(wav_path: Path) -> str:
    """Вход: WAV 16 kHz mono."""
    from vosk import KaldiRecognizer

    model = _load_model()
    wf = wave.open(str(wav_path), "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        wf.close()
        msg = "Неверный формат WAV: нужны 16-bit mono PCM"
        raise ValueError(msg)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(False)
    parts: list[str] = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if res.get("text"):
                parts.append(res["text"])
    res = json.loads(rec.FinalResult())
    if res.get("text"):
        parts.append(res["text"])
    wf.close()
    return " ".join(parts).strip()
