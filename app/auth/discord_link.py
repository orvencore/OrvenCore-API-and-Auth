from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import settings

DISCORD_LINK_TOKEN_TYPE = "discord_link"


def create_discord_link_token(
    *,
    discord_user_id: str,
    username: str,
    avatar_url: str | None = None,
    expires_minutes: int = 10,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "type": DISCORD_LINK_TOKEN_TYPE,
        "discord_user_id": discord_user_id,
        "username": username,
        "avatar_url": avatar_url,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_discord_link_token(token: str) -> dict[str, str | None]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid Discord link token") from exc

    if payload.get("type") != DISCORD_LINK_TOKEN_TYPE:
        raise ValueError("Invalid Discord link token type")

    discord_user_id = payload.get("discord_user_id")
    username = payload.get("username")
    avatar_url = payload.get("avatar_url")
    if not isinstance(discord_user_id, str) or not isinstance(username, str):
        raise ValueError("Invalid Discord link token payload")
    if avatar_url is not None and not isinstance(avatar_url, str):
        raise ValueError("Invalid Discord avatar URL")
    return {
        "discord_user_id": discord_user_id,
        "username": username,
        "avatar_url": avatar_url,
    }

