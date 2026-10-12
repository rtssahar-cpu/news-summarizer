import os

from fastapi import FastAPI

from app.interface_adapters.controllers.health_controller import build_health_router


def create_app(app_version: str) -> FastAPI:
    app = FastAPI()
    app.include_router(build_health_router(app_version))
    return app


# APP_VERSION はビルド時にコミット SHA が埋め込まれる（Dockerfile の production ステージ）
app = create_app(app_version=os.environ.get("APP_VERSION", "unknown"))
