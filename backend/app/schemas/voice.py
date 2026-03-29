from datetime import datetime

from pydantic import BaseModel, Field


class VoiceCommandCreateResponse(BaseModel):
    id: int
    raw_transcript: str
    edited_transcript: str | None
    parsed_command: str | None
    parsed_identifier: str | None
    recorded_at: datetime
    confirmed: bool
    operator_username: str

    model_config = {"from_attributes": True}


class VoiceCommandListItem(BaseModel):
    id: int
    raw_transcript: str
    edited_transcript: str | None
    parsed_command: str | None
    parsed_identifier: str | None
    recorded_at: datetime
    confirmed: bool
    operator_username: str

    model_config = {"from_attributes": True}


class VoiceCommandUpdate(BaseModel):
    edited_transcript: str | None = None
    confirmed: bool | None = None
