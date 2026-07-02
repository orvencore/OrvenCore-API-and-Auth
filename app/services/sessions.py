from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.jwt import create_access_token, create_refresh_token
from app.config import settings
from app.models.session import UserSession
from app.models.user import User
from app.schemas.token import TokenPair
from app.utils.security import hash_secret


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def create_session(
    db: Session,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    refresh_token = create_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret(refresh_token),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()
    return TokenPair(access_token=create_access_token(user.id), refresh_token=refresh_token)


def get_active_session_by_refresh_token(db: Session, refresh_token: str) -> UserSession | None:
    session = db.scalar(
        select(UserSession)
        .where(UserSession.refresh_token_hash == hash_secret(refresh_token))
        .options(selectinload(UserSession.user))
    )
    if session is None or session.revoked_at is not None:
        return None
    if as_utc(session.expires_at) <= datetime.now(UTC):
        return None
    if session.user is None or not session.user.is_active:
        return None
    return session


def rotate_refresh_token(
    db: Session,
    refresh_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair | None:
    session = get_active_session_by_refresh_token(db, refresh_token)
    if session is None:
        return None

    now = datetime.now(UTC)
    session.revoked_at = now
    session.last_used_at = now
    next_refresh_token = create_refresh_token()
    next_session = UserSession(
        user_id=session.user_id,
        refresh_token_hash=hash_secret(next_refresh_token),
        user_agent=user_agent or session.user_agent,
        ip_address=ip_address or session.ip_address,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(next_session)
    db.flush()
    session.replaced_by_session_id = next_session.id
    db.commit()

    return TokenPair(access_token=create_access_token(session.user_id), refresh_token=next_refresh_token)


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    session = get_active_session_by_refresh_token(db, refresh_token)
    if session is None:
        return False
    session.revoked_at = datetime.now(UTC)
    db.add(session)
    db.commit()
    return True


def revoke_all_sessions(db: Session, user_id: str) -> int:
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
    ).all()
    now = datetime.now(UTC)
    for session in sessions:
        session.revoked_at = now
        db.add(session)
    db.commit()
    return len(sessions)


def list_user_sessions(db: Session, user_id: str) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        )
    )
