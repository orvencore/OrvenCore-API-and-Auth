from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.discord_link import create_discord_link_token, decode_discord_link_token
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.discord import DiscordLinkStartResponse
from app.schemas.session import SessionRead
from app.schemas.token import LogoutRequest, RefreshTokenRequest, TokenPair
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.sessions import (
    create_session,
    list_user_sessions,
    revoke_all_sessions,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.users import (
    authenticate_user,
    create_user,
    get_user_by_username_or_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new OrvenCore account",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing_user = get_user_by_username_or_email(db, payload.username) or get_user_by_username_or_email(
        db, str(payload.email).lower()
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        )
    return create_user(db, payload)


@router.post("/login", response_model=TokenPair, summary="Login and create a refresh session")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    user = authenticate_user(db, payload.username_or_email, payload.password)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )
    return create_session(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )


@router.post("/refresh", response_model=TokenPair, summary="Rotate a refresh token")
def refresh(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    token_pair = rotate_refresh_token(
        db,
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    if token_pair is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return token_pair


@router.post("/logout", response_model=MessageResponse, summary="Revoke one refresh session")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> MessageResponse:
    revoke_refresh_token(db, payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse, summary="Revoke all current user sessions")
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    revoked_count = revoke_all_sessions(db, current_user.id)
    return MessageResponse(message=f"Revoked {revoked_count} session(s)")


@router.get("/sessions", response_model=list[SessionRead], summary="List current user sessions")
def sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    return list_user_sessions(db, current_user.id)


@router.get("/me", response_model=UserRead, summary="Read the current account")
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get(
    "/discord/start",
    response_model=DiscordLinkStartResponse,
    summary="Create a short-lived signed Discord linking URL",
)
def start_discord_link(
    request: Request,
    discord_id: str,
    discord_username: str,
    discord_avatar: str | None = None,
) -> DiscordLinkStartResponse:
    token = create_discord_link_token(
        discord_user_id=discord_id,
        username=discord_username,
        avatar_url=discord_avatar,
    )
    root_url = str(request.base_url).rstrip("/")
    return DiscordLinkStartResponse(
        link_token=token,
        link_url=f"{root_url}/?source=discord&discord_link_token={token}",
        expires_in_seconds=600,
    )


@router.get("/discord/callback", summary="Validate a signed Discord linking token")
def discord_callback(token: str) -> dict[str, str | None]:
    try:
        return decode_discord_link_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
