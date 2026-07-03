from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

DEFAULT_PERMISSIONS = {
    "auth.me": "Read own account profile.",
    "discord.link": "Link own Discord account.",
    "api.read": "Read OrvenCore API service metadata.",
    "discord.use": "Use OrvenCore Discord Bot features.",
    "flashback.read": "Read FlashbackVHS resources.",
    "marketplace.read": "Read marketplace resources.",
    "terminal.read": "Read OrvenTerminal resources.",
    "kpass.read": "Read KPass resources.",
    "admin.users": "Manage users.",
    "admin.discord": "Manage Discord account links.",
    "admin.api_keys": "Manage service API keys.",
    "admin.services": "Manage registered services.",
}

DEFAULT_ROLES = {
    "User": ["auth.me", "discord.link"],
    "Premium": ["auth.me", "discord.link"],
    "Beta Tester": ["auth.me", "discord.link"],
    "Moderator": ["auth.me", "discord.link", "admin.users"],
    "Administrator": [
        "auth.me",
        "discord.link",
        "admin.users",
        "admin.discord",
        "admin.api_keys",
        "admin.services",
    ],
    "Owner": [
        "auth.me",
        "discord.link",
        "admin.users",
        "admin.discord",
        "admin.api_keys",
        "admin.services",
    ],
}


def ensure_default_roles(db: Session) -> None:
    permissions_by_code: dict[str, Permission] = {}
    for code, description in DEFAULT_PERMISSIONS.items():
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=description)
            db.add(permission)
        permissions_by_code[code] = permission

    db.flush()

    for role_name, permission_codes in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, description=f"Default {role_name} role.")
            db.add(role)
        role.permissions = [permissions_by_code[code] for code in permission_codes]

    db.commit()


def get_default_user_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.name == "User"))
    if role is None:
        ensure_default_roles(db)
        role = db.scalar(select(Role).where(Role.name == "User"))
    if role is None:
        raise RuntimeError("Default User role could not be created")
    return role


def summarize_permissions(user: User) -> tuple[list[str], list[str]]:
    roles = sorted({role.name for role in user.roles})
    permissions = sorted(
        {permission.code for role in user.roles for permission in role.permissions}
    )
    return roles, permissions
