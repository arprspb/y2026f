"""
Извлечение ключевой команды и идентификатора из текста (после ASR).
Команды из задания; идентификаторы: только цифры, только буквы или буквы+цифры
(произвольной длины в разумных пределах паттернов).
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

# Последовательность цифр (не только 8 символов)
DIGIT_RUN = re.compile(r"(?<![0-9])(\d+)(?![0-9])")
# Токен с буквами и цифрами (кириллица/латиница), напр. Р45345ИВ
MIXED_ID = re.compile(
    r"(?<![\w\d])([A-Za-zА-Яа-яЁё0-9]*\d[A-Za-zА-Яа-яЁё0-9]+|[A-Za-zА-Яа-яЁё]+[0-9][A-Za-zА-Яа-яЁё0-9]*)(?![\w\d])",
    re.UNICODE,
)
# Цифры в начале, затем буквы/цифры: 123ив6 (старый regex иногда режет границы иначе)
MIXED_ID_DIGIT_LEADING = re.compile(
    r"(?<![\w\d])(\d{2,}[а-яёa-z][а-яёa-z0-9]*)(?![\w\d])",
    re.IGNORECASE,
)

# Чисто буквенный токен (частые служебные слова из примеров команд — отбрасываем)
_LETTER_RUN = re.compile(
    r"(?<![A-Za-zА-Яа-яЁё])([A-Za-zА-Яа-яЁё]{3,})(?![A-Za-zА-Яа-яЁё])",
    re.UNICODE,
)
_SKIP_LETTER_IDS: frozenset[str] = frozenset(
    {
        "номер",
        "плавки",
        "плавка",
        "плавку",
        "трубу",
        "труба",
        "обработку",
        "обработка",
        "регистрацию",
        "регистрация",
        "что",
        "как",
        "для",
        "при",
        "или",
        "это",
        "ещё",
        "уже",
        "начать",
        "завершить",
        "отменить",
        "зарегистрировать",
        "конец",
        "там",
        "тут",
        "тоже",
        "вот",
    }
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


# Одиночные русские числительные (как часто отдаёт ASR) -> цифры для парсера
_RU_DIGIT_WORD: dict[str, str] = {
    "ноль": "0",
    "один": "1",
    "два": "2",
    "три": "3",
    "четыре": "4",
    "пять": "5",
    "шесть": "6",
    "семь": "7",
    "восемь": "8",
    "девять": "9",
}


def normalize_transcript_for_commands(raw: str) -> str:
    """
    Приводит устные числительные к цифрам и сливает подряд идущие одноразрядные цифры
    (чтобы отдельно произнесённые цифры стали 8-значным номером для regex).
    """
    t = normalize_text(raw)
    if not t:
        return ""
    tokens = t.split()
    mapped = [_RU_DIGIT_WORD.get(w, w) for w in tokens]
    merged: list[str] = []
    i = 0
    while i < len(mapped):
        tok = mapped[i]
        if len(tok) == 1 and tok.isdigit():
            run = [tok]
            j = i + 1
            while j < len(mapped) and len(mapped[j]) == 1 and mapped[j].isdigit():
                run.append(mapped[j])
                j += 1
            if len(run) >= 2:
                merged.append("".join(run))
            else:
                merged.append(tok)
            i = j
        else:
            merged.append(tok)
            i += 1
    joined = " ".join(merged)
    return _collapse_digit_block_with_spaced_letter_suffix(joined)


# ASR: «12345 в б д», «123 ив 6» — склеиваем с цифровым блоком, если в хвосте есть буква.
_COLLAPSE_AFTER_DIGITS = re.compile(
    r"(\d{2,})\s+((?:[а-яёa-z0-9](?:\s*[а-яёa-z0-9]){0,32}))",
    re.IGNORECASE,
)


def _collapse_digit_block_with_spaced_letter_suffix(text: str) -> str:
    """
    Склеивает блок цифр с хвостом только если это похоже на код:
    в хвосте есть цифра, либо это «в б д» (одна буква на слово через пробел).
    Не сливает «21957898 конец» в один токен.
    """

    def repl(m: re.Match[str]) -> str:
        raw_suffix = m.group(2)
        suffix = re.sub(r"\s+", "", raw_suffix)
        if not any(c.isalpha() for c in suffix):
            return m.group(0)
        if any(c.isdigit() for c in suffix):
            return m.group(1) + suffix
        parts = raw_suffix.split()
        if len(parts) >= 2 and all(len(p) == 1 and p.isalpha() for p in parts):
            return m.group(1) + suffix
        return m.group(0)

    s = text
    for _ in range(8):
        ns = _COLLAPSE_AFTER_DIGITS.sub(repl, s)
        if ns == s:
            break
        s = ns
    return s


def extract_command(normalized: str) -> str | None:
    for phrase in COMMAND_PHRASES:
        if phrase in normalized:
            return phrase
    return None


def _tail_after_command(normalized: str, command: str | None) -> str | None:
    """Текст после фразы команды; None — искать по всей строке (команда не найдена)."""
    if not command:
        return None
    idx = normalized.find(command)
    if idx < 0:
        return None
    return normalized[idx + len(command) :].strip()


def extract_identifiers(normalized: str, command: str | None = None) -> list[str]:
    """
    Ищет ID в хвосте после команды (если команда есть), иначе по всему тексту.
    Приоритет по позиции в строке; смешанные и цифровые токены не фильтруются как слова.
    """
    tail = _tail_after_command(normalized, command)
    if command is not None and tail is not None and not tail:
        return []
    search = tail if tail is not None else normalized
    if not search.strip():
        return []

    matches: list[tuple[int, str]] = []

    for m in MIXED_ID.finditer(search):
        token = m.group(1)
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            matches.append((m.start(), token))
    for m in MIXED_ID_DIGIT_LEADING.finditer(search):
        matches.append((m.start(), m.group(1)))
    for m in DIGIT_RUN.finditer(search):
        matches.append((m.start(), m.group(1)))
    for m in _LETTER_RUN.finditer(search):
        w = m.group(1)
        if w.lower() not in _SKIP_LETTER_IDS:
            matches.append((m.start(), w))

    matches.sort(key=lambda x: x[0])
    out: list[str] = []
    seen: set[str] = set()
    for _, tok in matches:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def parse_voice_text(raw: str) -> ParseResult:
    prepared = normalize_transcript_for_commands(raw)
    normalized = normalize_text(prepared)
    cmd = extract_command(normalized)
    ids = extract_identifiers(normalized, cmd)
    primary = ids[0] if ids else None
    return ParseResult(command=cmd, identifier=primary, identifiers_found=ids)
