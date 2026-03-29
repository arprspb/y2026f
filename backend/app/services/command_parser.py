"""
Извлечение ключевой команды и идентификатора из текста (после ASR).
Команды из задания; 8-значные последовательности и буквенно-цифровые ID.
"""

import re
from dataclasses import dataclass

# Длинные фразы первыми (жадное совпадение подстроки)
COMMAND_PHRASES: tuple[str, ...] = (
    "отменить регистрацию",
    "отменить обработку",
    "начать обработку",
    "завершить обработку",
    "зарегистрировать",
)

DIGITS_8 = re.compile(r"(?<!\d)(\d{8})(?!\d)")
# Токен с буквами и цифрами (кириллица/латиница), напр. Р45345ИВ
MIXED_ID = re.compile(
    r"(?<![\w\d])([A-Za-zА-Яа-яЁё0-9]*\d[A-Za-zА-Яа-яЁё0-9]+|[A-Za-zА-Яа-яЁё]+[0-9][A-Za-zА-Яа-яЁё0-9]*)(?![\w\d])",
    re.UNICODE,
)


@dataclass
class ParseResult:
    command: str | None
    identifier: str | None
    identifiers_found: list[str]


def normalize_text(text: str) -> str:
    t = text.lower().replace("ё", "е")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_command(normalized: str) -> str | None:
    for phrase in COMMAND_PHRASES:
        if phrase in normalized:
            return phrase
    return None


def extract_identifiers(normalized: str) -> list[str]:
    found: list[str] = []
    for m in DIGITS_8.finditer(normalized):
        found.append(m.group(1))
    for m in MIXED_ID.finditer(normalized):
        token = m.group(1)
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            if token not in found:
                found.append(token)
    return found


def parse_voice_text(raw: str) -> ParseResult:
    normalized = normalize_text(raw)
    cmd = extract_command(normalized)
    ids = extract_identifiers(normalized)
    primary = ids[0] if ids else None
    return ParseResult(command=cmd, identifier=primary, identifiers_found=ids)
