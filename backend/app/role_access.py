"""Правила доступа по ролям (без зависимости от database/config)."""

from app.enums import UserRole


def can_record_voice(role: UserRole) -> bool:
    return role in (UserRole.admin, UserRole.operator_record)


def can_see_all_voice_commands(role: UserRole) -> bool:
    return role in (UserRole.admin, UserRole.operator_verify)


def can_confirm_voice(role: UserRole) -> bool:
    return role in (UserRole.admin, UserRole.operator_verify)


def can_access_voice_command(
    role: UserRole,
    command_owner_user_id: int,
    current_user_id: int,
) -> bool:
    if can_see_all_voice_commands(role):
        return True
    return command_owner_user_id == current_user_id
