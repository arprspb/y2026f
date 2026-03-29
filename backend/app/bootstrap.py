"""Однократное создание администратора из переменных окружения при старте."""

import logging

from sqlalchemy import func, select

from app.config import Settings
from app.database import async_session_maker
from app.models import User, UserRole
from app.security import hash_password

log = logging.getLogger(__name__)


async def ensure_bootstrap_admin(settings: Settings) -> None:
    username = (settings.bootstrap_admin_username or "").strip()
    password = settings.bootstrap_admin_password or ""
    if not username or not password:
        async with async_session_maker() as session:
            n = await session.scalar(select(func.count()).select_from(User))
            if n == 0:
                log.warning(
                    "В базе нет пользователей, а BOOTSTRAP_ADMIN_USERNAME / "
                    "BOOTSTRAP_ADMIN_PASSWORD не заданы — создайте админа через .env и перезапустите."
                )
        return

    async with async_session_maker() as session:
        exists = await session.execute(select(User).where(User.username == username))
        if exists.scalar_one_or_none() is not None:
            return
        session.add(
            User(
                username=username,
                hashed_password=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            )
        )
        await session.commit()
        log.info("Создан начальный администратор (логин из BOOTSTRAP_ADMIN_USERNAME).")
