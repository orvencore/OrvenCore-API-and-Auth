from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.database import get_db
from app.models.user import User
from app.services.api_keys import authenticate_api_key
from app.services.users import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token, "access")
    except ValueError as exc:
        raise credentials_error from exc

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_permission(permission_code: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        permission_codes = {
            permission.code for role in current_user.roles for permission in role.permissions
        }
        if current_user.is_superuser or permission_code in permission_codes:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission_code}",
        )

    return dependency


def require_service_api_key(
    service_key: str | None = Header(default=None, alias="X-OrvenCore-Service-Key"),
    db: Session = Depends(get_db),
) -> None:
    if not service_key or authenticate_api_key(db, service_key) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid service API key required",
        )
