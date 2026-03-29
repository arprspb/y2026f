import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import get_settings
from app.database import get_db
from app.deps import (
    CurrentUserDep,
    can_access_voice_command_row,
    can_confirm_voice,
    can_record_voice,
    can_see_all_voice_commands,
)
from app.models import User, VoiceCommand
from app.schemas.voice import (
    VoiceCommandCreateResponse,
    VoiceCommandListItem,
    VoiceCommandUpdate,
    VoicePreviewConfirm,
    VoicePreviewResponse,
)
from app.services.asr import transcribe_wav_file
from app.services.audio_convert import convert_to_wav_16k_mono
from app.services.command_parser import normalize_transcript_for_commands, parse_voice_text

router = APIRouter(prefix="/voice-commands", tags=["voice-commands"])
settings = get_settings()


def _ensure_upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


PREVIEW_SUBDIR = "preview"


def _preview_dir(upload_dir: Path) -> Path:
    p = upload_dir / PREVIEW_SUBDIR
    p.mkdir(parents=True, exist_ok=True)
    return p


async def _transcribe_uploaded_file(dest: Path) -> str:
    wav_path = dest.parent / f"{uuid.uuid4().hex}.wav"
    try:
        await asyncio.to_thread(convert_to_wav_16k_mono, dest, wav_path)
        try:
            return await asyncio.to_thread(transcribe_wav_file, wav_path)
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
    finally:
        wav_path.unlink(missing_ok=True)



@router.post("/preview", response_model=VoicePreviewResponse)
async def preview_voice_command(
    current: CurrentUserDep,
    file: Annotated[UploadFile, File(description="Аудиофайл (webm, wav, ogg, ...)")],
) -> VoicePreviewResponse:
    if not can_record_voice(current.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Запись голоса разрешена операторам записи и администратору",
        )
    upload_dir = _ensure_upload_dir()
    prev_dir = _preview_dir(upload_dir)
    preview_id = uuid.uuid4().hex
    ext = Path(file.filename or "audio").suffix or ".webm"
    dest = prev_dir / f"{preview_id}{ext}"
    content = await file.read()
    async with aiofiles.open(dest, "wb") as out:
        await out.write(content)

    transcript_raw = await _transcribe_uploaded_file(dest)
    prepared = normalize_transcript_for_commands(transcript_raw)
    parsed = parse_voice_text(transcript_raw)
    meta = {
        "raw_transcript": prepared,
        "parsed_command": parsed.command,
        "parsed_identifier": parsed.identifier,
    }
    meta_path = prev_dir / f"{preview_id}.json"
    async with aiofiles.open(meta_path, "w", encoding="utf-8") as out:
        await out.write(json.dumps(meta, ensure_ascii=False))

    return VoicePreviewResponse(
        preview_id=preview_id,
        raw_transcript=prepared,
        parsed_command=parsed.command,
        parsed_identifier=parsed.identifier,
    )


@router.post("/confirm", response_model=VoiceCommandCreateResponse)
async def confirm_voice_command(
    body: VoicePreviewConfirm,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoiceCommandCreateResponse:
    if not can_record_voice(current.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Сохранение записи разрешено операторам записи и администратору",
        )
    upload_dir = _ensure_upload_dir()
    prev_dir = _preview_dir(upload_dir)
    pid = body.preview_id.strip()
    audio_path = None
    for path in prev_dir.iterdir():
        if path.is_file() and path.name.startswith(pid) and not path.name.endswith(".json"):
            audio_path = path
            break
    meta_path = prev_dir / f"{pid}.json"
    if audio_path is None or not meta_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предпросмотр не найден. Запишите команду снова.",
        )
    async with aiofiles.open(meta_path, encoding="utf-8") as f:
        meta = json.loads(await f.read())

    ext = audio_path.suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    final_path = upload_dir / stored_name
    audio_path.replace(final_path)
    meta_path.unlink(missing_ok=True)

    vc = VoiceCommand(
        user_id=current.id,
        audio_filename=stored_name,
        raw_transcript=meta["raw_transcript"],
        edited_transcript=None,
        parsed_command=meta.get("parsed_command"),
        parsed_identifier=meta.get("parsed_identifier"),
        recorded_at=datetime.now(UTC),
        confirmed=False,
        confirmed_at=None,
    )
    db.add(vc)
    await db.flush()
    await db.refresh(vc)
    return VoiceCommandCreateResponse(
        id=vc.id,
        raw_transcript=vc.raw_transcript,
        edited_transcript=vc.edited_transcript,
        parsed_command=vc.parsed_command,
        parsed_identifier=vc.parsed_identifier,
        recorded_at=vc.recorded_at,
        confirmed=vc.confirmed,
        operator_username=current.username,
        confirmed_by_username=None,
    )


@router.post("", response_model=VoiceCommandCreateResponse)
async def create_voice_command(
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Аудиофайл (webm, wav, ogg, ...)")],
) -> VoiceCommandCreateResponse:
    if not can_record_voice(current.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Запись голоса разрешена операторам записи и администратору",
        )
    upload_dir = _ensure_upload_dir()
    ext = Path(file.filename or "audio").suffix or ".webm"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = upload_dir / stored_name
    content = await file.read()
    async with aiofiles.open(dest, "wb") as out:
        await out.write(content)

    transcript_raw = await _transcribe_uploaded_file(dest)
    prepared = normalize_transcript_for_commands(transcript_raw)
    parsed = parse_voice_text(transcript_raw)
    vc = VoiceCommand(
        user_id=current.id,
        audio_filename=stored_name,
        raw_transcript=prepared,
        edited_transcript=None,
        parsed_command=parsed.command,
        parsed_identifier=parsed.identifier,
        recorded_at=datetime.now(UTC),
        confirmed=False,
        confirmed_at=None,
    )
    db.add(vc)
    await db.flush()
    await db.refresh(vc)
    return VoiceCommandCreateResponse(
        id=vc.id,
        raw_transcript=vc.raw_transcript,
        edited_transcript=vc.edited_transcript,
        parsed_command=vc.parsed_command,
        parsed_identifier=vc.parsed_identifier,
        recorded_at=vc.recorded_at,
        confirmed=vc.confirmed,
        operator_username=current.username,
        confirmed_by_username=None,
    )


@router.get("", response_model=list[VoiceCommandListItem])
async def list_voice_commands(
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    parsed_command: Annotated[str | None, Query()] = None,
    parsed_identifier: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    operator_username: Annotated[str | None, Query()] = None,
) -> list[VoiceCommandListItem]:
    author = aliased(User)
    confirmer = aliased(User)
    stmt = (
        select(VoiceCommand, author.username, confirmer.username)
        .join(author, VoiceCommand.user_id == author.id)
        .outerjoin(confirmer, VoiceCommand.confirmed_by_user_id == confirmer.id)
    )

    if not can_see_all_voice_commands(current.role):
        stmt = stmt.where(VoiceCommand.user_id == current.id)
    if parsed_command:
        stmt = stmt.where(VoiceCommand.parsed_command.ilike(f"%{parsed_command}%"))
    if parsed_identifier:
        stmt = stmt.where(
            or_(
                VoiceCommand.parsed_identifier.ilike(f"%{parsed_identifier}%"),
                VoiceCommand.raw_transcript.ilike(f"%{parsed_identifier}%"),
            )
        )
    if date_from:
        stmt = stmt.where(VoiceCommand.recorded_at >= date_from)
    if date_to:
        stmt = stmt.where(VoiceCommand.recorded_at <= date_to)
    if operator_username:
        stmt = stmt.where(author.username == operator_username)

    stmt = stmt.order_by(VoiceCommand.recorded_at.desc())
    result = await db.execute(stmt)
    rows = result.all()
    return [
        VoiceCommandListItem(
            id=vc.id,
            raw_transcript=vc.raw_transcript,
            edited_transcript=vc.edited_transcript,
            parsed_command=vc.parsed_command,
            parsed_identifier=vc.parsed_identifier,
            recorded_at=vc.recorded_at,
            confirmed=vc.confirmed,
            operator_username=author_uname,
            confirmed_by_username=cuname,
        )
        for vc, author_uname, cuname in rows
    ]


@router.get("/{command_id}", response_model=VoiceCommandCreateResponse)
async def get_voice_command(
    command_id: int,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoiceCommandCreateResponse:
    author = aliased(User)
    confirmer = aliased(User)
    result = await db.execute(
        select(VoiceCommand, author.username, confirmer.username)
        .join(author, VoiceCommand.user_id == author.id)
        .outerjoin(confirmer, VoiceCommand.confirmed_by_user_id == confirmer.id)
        .where(VoiceCommand.id == command_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    vc, uname, cuname = row
    if not can_access_voice_command_row(current, vc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return VoiceCommandCreateResponse(
        id=vc.id,
        raw_transcript=vc.raw_transcript,
        edited_transcript=vc.edited_transcript,
        parsed_command=vc.parsed_command,
        parsed_identifier=vc.parsed_identifier,
        recorded_at=vc.recorded_at,
        confirmed=vc.confirmed,
        operator_username=uname,
        confirmed_by_username=cuname,
    )


@router.patch("/{command_id}", response_model=VoiceCommandCreateResponse)
async def patch_voice_command(
    command_id: int,
    body: VoiceCommandUpdate,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoiceCommandCreateResponse:
    author = aliased(User)
    confirmer = aliased(User)
    result = await db.execute(
        select(VoiceCommand, author.username, confirmer.username)
        .join(author, VoiceCommand.user_id == author.id)
        .outerjoin(confirmer, VoiceCommand.confirmed_by_user_id == confirmer.id)
        .where(VoiceCommand.id == command_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    vc, uname, cuname = row
    if not can_access_voice_command_row(current, vc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if body.confirmed is not None:
        if not can_confirm_voice(current.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Подтверждать записи могут операторы проверки и администратор",
            )
        if body.confirmed is True:
            vc.confirmed = True
            vc.confirmed_at = datetime.now(UTC)
            vc.confirmed_by_user_id = current.id
        else:
            vc.confirmed = False
            vc.confirmed_at = None
            vc.confirmed_by_user_id = None

    if body.edited_transcript is not None:
        prepared = normalize_transcript_for_commands(body.edited_transcript)
        vc.edited_transcript = prepared
        parsed = parse_voice_text(body.edited_transcript)
        vc.parsed_command = parsed.command
        vc.parsed_identifier = parsed.identifier

    await db.flush()
    await db.refresh(vc)
    if vc.confirmed_by_user_id:
        r2 = await db.execute(select(User.username).where(User.id == vc.confirmed_by_user_id))
        cuname = r2.scalar_one_or_none()
    else:
        cuname = None

    return VoiceCommandCreateResponse(
        id=vc.id,
        raw_transcript=vc.raw_transcript,
        edited_transcript=vc.edited_transcript,
        parsed_command=vc.parsed_command,
        parsed_identifier=vc.parsed_identifier,
        recorded_at=vc.recorded_at,
        confirmed=vc.confirmed,
        operator_username=uname,
        confirmed_by_username=cuname,
    )


@router.get("/{command_id}/audio")
async def get_audio(
    command_id: int,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    result = await db.execute(select(VoiceCommand).where(VoiceCommand.id == command_id))
    vc = result.scalar_one_or_none()
    if vc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    if not can_access_voice_command_row(current, vc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    path = Path(settings.upload_dir) / vc.audio_filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл записи отсутствует на сервере")
    return FileResponse(path, filename=vc.audio_filename)
