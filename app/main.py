from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal, create_db_and_tables
from app.routes import admin, auth, discord, health, permissions, services, users
from app.services.permissions import ensure_default_roles
from app.services.registry import ensure_default_services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        create_db_and_tables()
        with SessionLocal() as db:
            ensure_default_roles(db)
            ensure_default_services(db)
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
app.include_router(services.router)

frontend_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/register", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
@app.get("/account", include_in_schema=False)
@app.get("/apps", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")
