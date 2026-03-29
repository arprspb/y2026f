"""Распознавание речи через VOSK (модель на диске)."""

import json
import wave
from pathlib import Path

from app.config import get_settings

_model = None


def _has_vosk_am(model_dir: Path) -> bool:
    """Маркер комплекта модели Kaldi/Vosk (small-ru и аналоги)."""
    return (model_dir / "am" / "final.mdl").is_file()


def resolve_vosk_model_dir(root: Path) -> Path:
    """
    Корень из архива часто даёт вложенную папку с тем же именем.
    Если напрямую am/final.mdl нет — ищем первый подкаталог, где он есть.
    """
    if _has_vosk_am(root):
        return root
    if not root.is_dir():
        return root
    try:
        subs = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return root
    for sub in subs:
        if _has_vosk_am(sub):
            return sub
    return root


def describe_vosk_folder(path: Path) -> str:
    if not path.exists():
        return "каталог отсутствует"
    if not path.is_dir():
        return "это не каталог"
    try:
        names = sorted(p.name for p in path.iterdir())
    except OSError as e:
        return f"не удалось прочитать: {e}"
    if not names:
        return "каталог пустой — скачайте и распакуйте русскую модель VOSK (см. README, vosk-model-ru-0.42)"
    return f"содержимое верхнего уровня: {', '.join(names[:15])}{'…' if len(names) > 15 else ''}"


def _load_model():
    global _model
    if _model is None:
        from vosk import Model

        root = Path(get_settings().vosk_model_path)
        path = resolve_vosk_model_dir(root)

        if not path.is_dir():
            msg = (
                f"Модель VOSK: {path} не найдена. {describe_vosk_folder(root)}. "
                "См. README: каталог из VOSK_MODEL_PATH (по умолчанию ./models/vosk-model-ru-0.42)"
            )
            raise RuntimeError(msg)

        if not _has_vosk_am(path):
            msg = (
                f"В {path} нет файлов модели VOSK (ожидается am/final.mdl). "
                f"{describe_vosk_folder(path)}. "
                "Скачайте архив с https://alphacephei.com/vosk/models (русская большая модель), "
                "распакуйте так, чтобы в каталоге модели оказались папки am, conf, graph "
                "(часто нужно поднять содержимое из внутренней папки архива на уровень выше)."
            )
            raise RuntimeError(msg)

        try:
            _model = Model(str(path))
        except Exception as e:
            msg = (
                f"VOSK не смог открыть модель в {path}: {e}. "
                "Проверьте целостность архива и права на чтение."
            )
            raise RuntimeError(msg) from e
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
