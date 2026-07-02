from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.discord_account import DiscordAccount
from app.models.user import User
from app.schemas.discord import DiscordAccountLink


def upsert_discord_account(
    db: Session,
    user: User,
    payload: DiscordAccountLink,
) -> DiscordAccount:
    existing_for_discord = db.scalar(
        select(DiscordAccount).where(DiscordAccount.discord_user_id == payload.discord_user_id)
    )
    if existing_for_discord is not None and existing_for_discord.user_id != user.id:
        raise ValueError("Discord account is already linked to another user")

    account = user.discord_account
    if account is None:
        account = DiscordAccount(user_id=user.id, discord_user_id=payload.discord_user_id)

    account.username = payload.username
    account.avatar_url = payload.avatar_url
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_user_by_discord_id(db: Session, discord_user_id: str) -> User | None:
    return db.scalar(
        select(User)
        .join(User.discord_account)
        .where(DiscordAccount.discord_user_id == discord_user_id)
        .options(
            selectinload(User.discord_account),
            selectinload(User.roles).selectinload("*"),
        )
    )
