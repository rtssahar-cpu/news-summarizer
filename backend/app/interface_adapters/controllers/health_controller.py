from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def get_health_status() -> dict[str, str]:
    return {"status": "ok"}
