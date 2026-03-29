from pydantic import BaseModel, Field

from app.models import UserRole


class UserListItem(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class UserAdminCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=512)
    role: UserRole = UserRole.operator


class UserAdminUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
