from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    id: str
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

