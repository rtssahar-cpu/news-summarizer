from fastapi import APIRouter


def build_health_router(app_version: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def get_health_status() -> dict[str, str]:
        return {"status": "ok", "version": app_version}

    return router
