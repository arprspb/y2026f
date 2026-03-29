"""Права по ролям для голосовых команд."""

from app.enums import UserRole
from app.role_access import (
    can_access_voice_command,
    can_confirm_voice,
    can_record_voice,
    can_see_all_voice_commands,
)


def test_can_record_voice() -> None:
    assert can_record_voice(UserRole.admin) is True
    assert can_record_voice(UserRole.operator_record) is True
    assert can_record_voice(UserRole.operator_verify) is False


def test_can_see_all_voice_commands() -> None:
    assert can_see_all_voice_commands(UserRole.admin) is True
    assert can_see_all_voice_commands(UserRole.operator_verify) is True
    assert can_see_all_voice_commands(UserRole.operator_record) is False


def test_can_confirm_voice() -> None:
    assert can_confirm_voice(UserRole.admin) is True
    assert can_confirm_voice(UserRole.operator_verify) is True
    assert can_confirm_voice(UserRole.operator_record) is False


def test_can_access_voice_command() -> None:
    assert can_access_voice_command(UserRole.operator_record, 1, 1) is True
    assert can_access_voice_command(UserRole.operator_record, 99, 1) is False
    assert can_access_voice_command(UserRole.operator_verify, 99, 1) is True
    assert can_access_voice_command(UserRole.admin, 99, 1) is True
