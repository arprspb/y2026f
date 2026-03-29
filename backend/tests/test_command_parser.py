import pytest

from app.services.command_parser import parse_voice_text


def test_parse_cancel_processing_with_digits() -> None:
    r = parse_voice_text("отменить обработку плавки 21957898")
    assert r.command == "отменить обработку"
    assert r.identifier == "21957898"


def test_parse_start_processing_eight_digits() -> None:
    r = parse_voice_text("начать обработку 12345678")
    assert r.command == "начать обработку"
    assert r.identifier == "12345678"


def test_eight_digits_without_command() -> None:
    r = parse_voice_text("что-то 21957898 конец")
    assert r.identifier == "21957898"


def test_mixed_id_with_register() -> None:
    r = parse_voice_text("зарегистрировать номер Р45345ИВ")
    assert r.command == "зарегистрировать"
    assert r.identifier is not None
    assert "45345" in r.identifier

def test_spoken_digits_merge_to_eight() -> None:
    r = parse_voice_text("начать обработку один два три четыре пять шесть семь восемь")
    assert r.command == "начать обработку"
    assert r.identifier == "12345678"


def test_digits_then_spaced_cyrillic_suffix_mixed_id() -> None:
    """Как часто отдаёт ASR: цифры и буквы разнесены пробелами."""
    r = parse_voice_text("зарегистрировать 12345 в б д")
    assert r.command == "зарегистрировать"
    assert r.identifier == "12345вбд"


def test_short_digit_run_with_command() -> None:
    r = parse_voice_text("начать обработку 123")
    assert r.command == "начать обработку"
    assert r.identifier == "123"


def test_letters_only_id_after_command() -> None:
    r = parse_voice_text("зарегистрировать абвгд")
    assert r.command == "зарегистрировать"
    assert r.identifier == "абвгд"
