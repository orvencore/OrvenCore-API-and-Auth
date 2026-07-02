from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import require_permission
from app.models.discord_account import DiscordAccount
from app.models.user import User
from app.schemas.admin import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
    DiscordLinkAdminRead,
    UserAdminRead,
    UserAdminUpdate,
)
from app.schemas.common import MessageResponse
from app.services.api_keys import create_api_key, list_api_keys, revoke_api_key
from app.services.users import get_user_by_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserAdminRead],
    summary="List users",
    dependencies=[Depends(require_permission("admin.users"))],
)
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .options(selectinload(User.roles).selectinload("*"), selectinload(User.discord_account))
            .order_by(User.created_at.desc())
        )
    )


@router.get(
    "/users/{user_id}",
    response_model=UserAdminRead,
    summary="Read a user",
    dependencies=[Depends(require_permission("admin.users"))],
)
def read_user(user_id: str, db: Session = Depends(get_db)) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch(
    "/users/{user_id}",
    response_model=UserAdminRead,
    summary="Update a user",
    dependencies=[Depends(require_permission("admin.users"))],
)
def update_user(user_id: str, payload: UserAdminUpdate, db: Session = Depends(get_db)) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    return get_user_by_id(db, user_id) or user


@router.get(
    "/discord/links",
    response_model=list[DiscordLinkAdminRead],
    summary="List Discord links",
    dependencies=[Depends(require_permission("admin.discord"))],
)
def list_discord_links(db: Session = Depends(get_db)) -> list[DiscordAccount]:
    return list(db.scalars(select(DiscordAccount).order_by(DiscordAccount.linked_at.desc())))


@router.delete(
    "/discord/links/{link_id}",
    response_model=MessageResponse,
    summary="Delete a Discord link",
    dependencies=[Depends(require_permission("admin.discord"))],
)
def delete_discord_link(link_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    link = db.get(DiscordAccount, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discord link not found")
    db.delete(link)
    db.commit()
    return MessageResponse(message="Discord link deleted")


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service API key",
    dependencies=[Depends(require_permission("admin.api_keys"))],
)
def create_service_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db)) -> ApiKeyCreateResponse:
    api_key, secret = create_api_key(db, payload.name, payload.expires_at)
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        key=secret,
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeyRead],
    summary="List service API keys",
    dependencies=[Depends(require_permission("admin.api_keys"))],
)
def read_service_api_keys(db: Session = Depends(get_db)) -> list[ApiKeyRead]:
    return list_api_keys(db)


@router.delete(
    "/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="Revoke a service API key",
    dependencies=[Depends(require_permission("admin.api_keys"))],
)
def delete_service_api_key(key_id: str, db: Session = Depends(get_db)) -> MessageResponse:
    if not revoke_api_key(db, key_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return MessageResponse(message="API key revoked")
