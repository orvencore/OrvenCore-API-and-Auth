from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    code: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleRead(BaseModel):
    name: str
    description: str | None = None
    permissions: list[PermissionRead] = []

    model_config = ConfigDict(from_attributes=True)


class PermissionSummary(BaseModel):
    roles: list[str]
    permissions: list[str]

