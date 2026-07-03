from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.user import User
from app.services.permissions import summarize_permissions

DEFAULT_SERVICES = [
    {
        "name": "FlashbackVHS",
        "slug": "flashbackvhs",
        "description": "A retro VHS-style web app for creating nostalgic visual presets and effects.",
        "status": "development",
        "url": "",
        "icon": "video",
        "required_permissions": ["flashback.read"],
    },
    {
        "name": "ProgressiveNodeX",
        "slug": "progressivenodex",
        "description": "A project/template CLI and marketplace platform for creating, sharing, and running development templates.",
        "status": "development",
        "url": "",
        "icon": "package",
        "required_permissions": ["marketplace.read"],
    },
    {
        "name": "OrvenTerminal",
        "slug": "orventerminal",
        "description": "A custom terminal and developer tool experience for the OrvenCore ecosystem.",
        "status": "development",
        "url": "",
        "icon": "terminal",
        "required_permissions": ["terminal.read"],
    },
    {
        "name": "KPass",
        "slug": "kpass",
        "description": "Password and secrets management project within the OrvenCore ecosystem.",
        "status": "planned",
        "url": "",
        "icon": "key",
        "required_permissions": ["kpass.read"],
    },
    {
        "name": "Discord Bot",
        "slug": "discord-bot",
        "description": "The OrvenCore Discord bot connected to central authentication and user permissions.",
        "status": "active",
        "url": "",
        "icon": "message",
        "required_permissions": ["discord.use"],
    },
    {
        "name": "OrvenCore API",
        "slug": "orvencore-api",
        "description": "The central authentication, permissions, Discord linking, and service API backend.",
        "status": "internal",
        "url": "/docs",
        "icon": "server",
        "required_permissions": [],
    },
]


def ensure_default_services(db: Session) -> None:
    for item in DEFAULT_SERVICES:
        service = db.scalar(select(Service).where(Service.slug == item["slug"]))
        if service is None:
            service = Service(
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                status=item["status"],
                url=item["url"],
                icon=item["icon"],
            )
            service.required_permissions = item["required_permissions"]
            db.add(service)
    db.commit()


def list_services(db: Session) -> list[Service]:
    return list(db.scalars(select(Service).order_by(Service.name.asc())))


def get_service_by_slug(db: Session, slug: str) -> Service | None:
    return db.scalar(select(Service).where(Service.slug == slug))


def user_has_service_access(user: User, service: Service) -> bool:
    if user.is_superuser:
        return True
    _, permission_codes = summarize_permissions(user)
    permissions = set(permission_codes)
    return all(permission in permissions for permission in service.required_permissions)

