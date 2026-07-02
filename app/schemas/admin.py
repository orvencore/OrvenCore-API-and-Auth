from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.discord import DiscordAccountRead
from app.schemas.user import UserRead


class UserAdminUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    profile_picture_url: str | None = Field(default=None, max_length=500)
    email_verified: bool | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class DiscordLinkAdminRead(DiscordAccountRead):
    id: int
    user_id: str


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None


class ApiKeyRead(BaseModel):
    id: str
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyRead):
    key: str


class UserAdminRead(UserRead):
    pass

