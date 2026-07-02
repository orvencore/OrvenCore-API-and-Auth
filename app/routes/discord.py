from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.discord_link import decode_discord_link_token
from app.dependencies.auth import get_current_user, require_service_api_key
from app.models.user import User
from app.schemas.discord import DiscordAccountCreate, DiscordAccountLink, DiscordAccountRead, DiscordUserLookup
from app.services.discord import get_user_by_discord_id, upsert_discord_account
from app.services.permissions import summarize_permissions

router = APIRouter(prefix="/discord", tags=["discord"])


@router.put(
    "/me",
    response_model=DiscordAccountRead,
    summary="Link or update the current user's Discord account",
)
def link_my_discord(
    payload: DiscordAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscordAccountRead:
    if payload.link_token:
        try:
            signed_payload = decode_discord_link_token(payload.link_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        link_payload = DiscordAccountLink(**signed_payload)
    else:
        if payload.discord_user_id is None or payload.username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discord user ID and username are required",
            )
        link_payload = DiscordAccountLink(
            discord_user_id=payload.discord_user_id,
            username=payload.username,
            avatar_url=payload.avatar_url,
        )
    try:
        return upsert_discord_account(db, current_user, link_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/users/{discord_user_id}",
    response_model=DiscordUserLookup,
    summary="Resolve an OrvenCore account by Discord user ID",
)
def resolve_discord_user(
    discord_user_id: str,
    _: None = Depends(require_service_api_key),
    db: Session = Depends(get_db),
) -> DiscordUserLookup:
    user = get_user_by_discord_id(db, discord_user_id)
    if user is None or user.discord_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discord user not found")

    roles, permissions = summarize_permissions(user)
    return DiscordUserLookup(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        discord=user.discord_account,
        roles=roles,
        permissions=permissions,
    )
