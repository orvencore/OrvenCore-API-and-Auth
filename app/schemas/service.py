from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=1)
    url: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=120)
    status: str = Field(default="planned", max_length=40)
    required_permissions: list[str] = []


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=40)
    required_permissions: list[str] | None = None


class ServiceRead(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceAccessRead(ServiceRead):
    has_access: bool
    missing_permissions: list[str]

