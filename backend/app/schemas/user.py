from pydantic import BaseModel, Field, field_validator, model_validator

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
    role: UserRole = UserRole.operator_record

    @field_validator("role")
    @classmethod
    def disallow_admin_on_create(cls, v: UserRole) -> UserRole:
        if v == UserRole.admin:
            raise ValueError("Роль admin задаётся только через переменные окружения при старте")
        return v


class UserAdminUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def disallow_admin_via_api(self) -> "UserAdminUpdate":
        if self.role == UserRole.admin:
            raise ValueError("Назначить роль admin через API нельзя")
        return self
