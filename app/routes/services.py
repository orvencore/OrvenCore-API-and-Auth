from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceAccessRead, ServiceRead
from app.services.permissions import summarize_permissions
from app.services.registry import get_service_by_slug, list_services, user_has_service_access

router = APIRouter(prefix="/services", tags=["services"])


def serialize_service(service: Service) -> ServiceRead:
    return ServiceRead(
        id=service.id,
        name=service.name,
        slug=service.slug,
        description=service.description,
        url=service.url,
        icon=service.icon,
        status=service.status,
        required_permissions=service.required_permissions,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


def serialize_service_access(service: Service, user: User) -> ServiceAccessRead:
    _, permissions = summarize_permissions(user)
    permission_set = set(permissions)
    missing_permissions = [
        permission for permission in service.required_permissions if permission not in permission_set
    ]
    return ServiceAccessRead(
        **serialize_service(service).model_dump(),
        has_access=user_has_service_access(user, service),
        missing_permissions=missing_permissions,
    )


@router.get("", response_model=list[ServiceRead], summary="List OrvenCore services")
def read_services(db: Session = Depends(get_db)) -> list[ServiceRead]:
    return [serialize_service(service) for service in list_services(db)]


@router.get("/me", response_model=list[ServiceAccessRead], summary="List current user's service access")
def read_my_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ServiceAccessRead]:
    return [serialize_service_access(service, current_user) for service in list_services(db)]


@router.get("/{slug}", response_model=ServiceRead, summary="Read a service by slug")
def read_service(slug: str, db: Session = Depends(get_db)) -> ServiceRead:
    service = get_service_by_slug(db, slug)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return serialize_service(service)

