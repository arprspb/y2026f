import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import CurrentUserDep
from app.models import User, UserRole, VoiceCommand
from app.schemas.voice import VoiceCommandCreateResponse, VoiceCommandListItem, VoiceCommandUpdate
from app.services.asr import transcribe_wav_file
from app.services.audio_convert import convert_to_wav_16k_mono
from app.services.command_parser import parse_voice_text

router = APIRouter(prefix="/voice-commands", tags=["voice-commands"])
settings = get_settings()


def _ensure_upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("", response_model=VoiceCommandCreateResponse)
async def create_voice_command(
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Аудиофайл (webm, wav, ogg, ...)")],
) -> VoiceCommandCreateResponse:
    upload_dir = _ensure_upload_dir()
    ext = Path(file.filename or "audio").suffix or ".webm"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = upload_dir / stored_name
    content = await file.read()
    async with aiofiles.open(dest, "wb") as out:
        await out.write(content)

    wav_path = upload_dir / f"{uuid.uuid4().hex}.wav"
    try:
        await asyncio.to_thread(convert_to_wav_16k_mono, dest, wav_path)
        transcript = await asyncio.to_thread(transcribe_wav_file, wav_path)
    finally:
        wav_path.unlink(missing_ok=True)

    parsed = parse_voice_text(transcript)
    vc = VoiceCommand(
        user_id=current.id,
        audio_filename=stored_name,
        raw_transcript=transcript,
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
    stmt = select(VoiceCommand, User.username).join(User, VoiceCommand.user_id == User.id)

    if current.role != UserRole.admin:
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
        stmt = stmt.where(User.username == operator_username)

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
            operator_username=uname,
        )
        for vc, uname in rows
    ]


@router.get("/{command_id}", response_model=VoiceCommandCreateResponse)
async def get_voice_command(
    command_id: int,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoiceCommandCreateResponse:
    result = await db.execute(
        select(VoiceCommand, User.username)
        .join(User, VoiceCommand.user_id == User.id)
        .where(VoiceCommand.id == command_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    vc, uname = row
    if current.role != UserRole.admin and vc.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return VoiceCommandCreateResponse(
        id=vc.id,
        raw_transcript=vc.raw_transcript,
        edited_transcript=vc.edited_transcript,
        parsed_command=vc.parsed_command,
        parsed_identifier=vc.parsed_identifier,
        recorded_at=vc.recorded_at,
        confirmed=vc.confirmed,
        operator_username=uname,
    )


@router.patch("/{command_id}", response_model=VoiceCommandCreateResponse)
async def patch_voice_command(
    command_id: int,
    body: VoiceCommandUpdate,
    current: CurrentUserDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoiceCommandCreateResponse:
    result = await db.execute(
        select(VoiceCommand, User.username)
        .join(User, VoiceCommand.user_id == User.id)
        .where(VoiceCommand.id == command_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    vc, uname = row
    if current.role != UserRole.admin and vc.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if body.edited_transcript is not None:
        vc.edited_transcript = body.edited_transcript
        parsed = parse_voice_text(body.edited_transcript)
        vc.parsed_command = parsed.command
        vc.parsed_identifier = parsed.identifier
    if body.confirmed is True:
        vc.confirmed = True
        vc.confirmed_at = datetime.now(UTC)
    elif body.confirmed is False:
        vc.confirmed = False
        vc.confirmed_at = None

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
        operator_username=uname,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if current.role != UserRole.admin and vc.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    path = Path(settings.upload_dir) / vc.audio_filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing")
    return FileResponse(path, filename=vc.audio_filename)
