from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DiscordAccountCreate(BaseModel):
    discord_user_id: str | None = Field(default=None, min_length=1, max_length=32)
    username: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    link_token: str | None = None


class DiscordAccountLink(BaseModel):
    discord_user_id: str = Field(min_length=1, max_length=32)
    username: str = Field(min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)


class DiscordLinkStartResponse(BaseModel):
    link_token: str
    link_url: str
    expires_in_seconds: int


class DiscordAccountRead(BaseModel):
    discord_user_id: str
    username: str
    avatar_url: str | None = None
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscordUserLookup(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    discord: DiscordAccountRead
    roles: list[str]
    permissions: list[str]
