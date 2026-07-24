from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth
from app.caldav.router import router as caldav_router
from app.core.config import get_settings


def _frontend_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "public",
        here.parents[2] / "frontend",
        Path("/frontend"),
        here.parents[1] / "frontend",
    ]


def _find_frontend() -> Path | None:
    for root in _frontend_roots():
        if (root / "index.html").is_file():
            return root
        dist = root / "dist"
        if (dist / "index.html").is_file():
            return dist
    return None


def _repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for root in (here.parents[2], here.parents[1].parent):
        if (root / "brand").is_dir() or (root / "public" / "brand").is_dir():
            return root
    return None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Do not touch Neon here — free tier autosuspend makes lifespan DB I/O a cold-start tax.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    auth.attach_session(app, settings.secret_key)
    app.include_router(auth.router)
    app.include_router(caldav_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        # Keep-warm ping only — no DB so Neon can stay asleep until real use.
        return {"status": "ok", "app": settings.app_name}

    repo = _repo_root()
    brand_dir = None
    if repo is not None:
        if (repo / "public" / "brand").is_dir():
            brand_dir = repo / "public" / "brand"
        elif (repo / "brand").is_dir():
            brand_dir = repo / "brand"
    if brand_dir is not None:
        app.mount("/brand", StaticFiles(directory=brand_dir), name="brand")

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
