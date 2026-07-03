from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OrvenCore API"
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    orvencore_public_url: str = "http://127.0.0.1:8000"
    orvencore_canonical_domain: str = "orvencore.com"
    database_url: str = "sqlite:///./orvencore.db"
    jwt_secret_key: str = Field(default="change-me", min_length=8)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
        ),
    )
    refresh_token_expire_days: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
            "REFRESH_TOKEN_EXPIRE_DAYS",
        ),
    )
    auto_create_tables: bool = True
    cors_origins: list[str] = Field(
        default=["http://127.0.0.1:8000", "http://localhost:8000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def validate_runtime_safety(self) -> None:
        insecure_secrets = {"change-me", "change-me-before-production", "dev-secret"}
        if self.is_production and self.jwt_secret_key in insecure_secrets:
            raise RuntimeError("JWT_SECRET_KEY must be changed before running in production.")
        if self.is_production and self.database_url.startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must use PostgreSQL or another production database.")


@lru_cache
def get_settings() -> Settings:
    loaded_settings = Settings()
    loaded_settings.validate_runtime_safety()
    return loaded_settings


settings = get_settings()
