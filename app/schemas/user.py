from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.discord import DiscordAccountRead
from app.schemas.permission import RoleRead


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    username_or_email: str
    password: str


class UserRead(BaseModel):
    id: str
    username: str
    email: EmailStr
    display_name: str | None = None
    profile_picture_url: str | None = None
    email_verified: bool
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    roles: list[RoleRead] = []
    discord_account: DiscordAccountRead | None = None

    model_config = ConfigDict(from_attributes=True)

