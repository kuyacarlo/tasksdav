from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth
from app.caldav.router import router as caldav_router
from app.core.config import get_settings
from app.db.session import init_db


def _frontend_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "frontend",  # repo layout: tasksdav/frontend
        Path("/frontend"),
        here.parents[1] / "frontend",
        Path(__file__).resolve().parents[1].parent / "frontend",
    ]


def _find_frontend() -> Path | None:
    for root in _frontend_roots():
        if (root / "index.html").is_file():
            return root
        dist = root / "dist"
        if (dist / "index.html").is_file():
            return dist
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for root in (here.parents[2], here.parents[1].parent, Path("/")):
        if (root / "brand").is_dir() and (root / "frontend" / "index.html").is_file():
            return root
        if (root / "brand").is_dir():
            return root
    brand_only = Path(__file__).resolve().parents[2]
    if (brand_only / "brand").is_dir():
        return brand_only
    return None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    auth.attach_session(app, settings.secret_key)
    app.include_router(auth.router)
    app.include_router(caldav_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    repo = _repo_root()
    if repo is not None and (repo / "brand").is_dir():
        app.mount("/brand", StaticFiles(directory=repo / "brand"), name="brand")

    frontend = _find_frontend()
    if frontend is not None:
        assets = frontend / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        index = frontend / "index.html"

        @app.get("/")
        async def spa_index() -> FileResponse:
            return FileResponse(index)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
