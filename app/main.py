from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal, create_db_and_tables
from app.routes import admin, auth, discord, health, permissions, users
from app.services.permissions import ensure_default_roles


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        create_db_and_tables()
        with SessionLocal() as db:
            ensure_default_roles(db)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Central API for OrvenCore accounts, authentication, permissions, and integrations.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(permissions.router)
app.include_router(discord.router)
app.include_router(admin.router)

frontend_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")
