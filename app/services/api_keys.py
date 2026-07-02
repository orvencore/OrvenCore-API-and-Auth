from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.utils.security import create_secret, hash_secret


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def create_api_key(db: Session, name: str, expires_at: datetime | None = None) -> tuple[ApiKey, str]:
    secret = create_secret("ocsvc_")
    api_key = ApiKey(
        name=name,
        key_hash=hash_secret(secret),
        prefix=secret[:12],
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, secret


def list_api_keys(db: Session) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())))


def get_api_key(db: Session, key_id: str) -> ApiKey | None:
    return db.get(ApiKey, key_id)


def revoke_api_key(db: Session, key_id: str) -> bool:
    api_key = get_api_key(db, key_id)
    if api_key is None or api_key.revoked_at is not None:
        return False
    api_key.is_active = False
    api_key.revoked_at = datetime.now(UTC)
    db.add(api_key)
    db.commit()
    return True


def authenticate_api_key(db: Session, secret: str) -> ApiKey | None:
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_secret(secret)))
    now = datetime.now(UTC)
    if api_key is None or not api_key.is_active or api_key.revoked_at is not None:
        return None
    if api_key.expires_at is not None and as_utc(api_key.expires_at) <= now:
        return None
    api_key.last_used_at = now
    db.add(api_key)
    db.commit()
    return api_key
