"""Конвертация входного аудио в WAV 16 kHz mono для VOSK (нужен ffmpeg в PATH)."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def convert_to_wav_16k_mono(input_path: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        msg = "ffmpeg не найден в PATH — установите ffmpeg для конвертации аудио"
        raise RuntimeError(msg)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def convert_upload_to_temp_wav(upload_path: Path) -> Path:
    fd, name = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    tmp = Path(name)
    try:
        convert_to_wav_16k_mono(upload_path, tmp)
        return tmp
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
