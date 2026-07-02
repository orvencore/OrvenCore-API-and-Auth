from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.passwords import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.permissions import get_default_user_role


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload("*"),
            selectinload(User.discord_account),
        )
    )


def get_user_by_username_or_email(db: Session, value: str) -> User | None:
    return db.scalar(
        select(User)
        .where(or_(User.username == value, User.email == value.lower()))
        .options(
            selectinload(User.roles).selectinload("*"),
            selectinload(User.discord_account),
        )
    )


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        username=payload.username,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        roles=[get_default_user_role(db)],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_user_by_id(db, user.id) or user


def authenticate_user(db: Session, username_or_email: str, password: str) -> User | None:
    user = get_user_by_username_or_email(db, username_or_email)
    if user is None or not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_user_by_id(db, user.id) or user

