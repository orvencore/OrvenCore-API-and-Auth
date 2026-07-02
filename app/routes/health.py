from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check API health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health", summary="Check API health with API prefix")
def api_health_check() -> dict[str, str]:
    return {"status": "ok"}
