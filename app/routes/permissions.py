from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.permission import PermissionSummary
from app.services.permissions import summarize_permissions

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/me", response_model=PermissionSummary, summary="Read current user's permissions")
def read_my_permissions(current_user: User = Depends(get_current_user)) -> PermissionSummary:
    roles, permissions = summarize_permissions(current_user)
    return PermissionSummary(roles=roles, permissions=permissions)

