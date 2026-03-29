"""Человекочитаемые сообщения для ошибок валидации тела запроса."""

from typing import Any

_FIELD_LABELS: dict[str, str] = {
    "username": "Логин",
    "password": "Пароль",
    "password_confirm": "Подтверждение пароля",
    "role": "Роль",
    "file": "Файл",
}


def format_request_validation_errors(errors: list[Any]) -> str:
    parts: list[str] = []
    for err in errors:
        if not isinstance(err, dict):
            continue
        loc = err.get("loc") or ()
        loc_list = list(loc) if loc else []

        field: str | None = None
        if len(loc_list) >= 2 and loc_list[0] == "body":
            field = str(loc_list[-1])
        elif loc_list:
            field = str(loc_list[-1])

        label = _FIELD_LABELS.get(field or "", field or "Данные")

        err_type = str(err.get("type", ""))
        ctx: dict[str, Any] = err.get("ctx") or {}

        if err_type == "string_too_short":
            min_l = ctx.get("min_length", "?")
            parts.append(f"{label}: не меньше {min_l} символов")
        elif err_type == "string_too_long":
            max_l = ctx.get("max_length", "?")
            parts.append(f"{label}: не больше {max_l} символов")
        elif err_type in ("missing", "json_invalid"):
            parts.append(f"{label}: обязательное поле или неверный JSON")
        else:
            parts.append(f"{label}: {err.get('msg', 'некорректное значение')}")

    return "; ".join(parts) if parts else "Некорректные данные запроса"
