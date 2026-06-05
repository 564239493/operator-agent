"""FastAPI application factory for the operator-agent main system."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from agent.core.config import settings
from agent.core.logging import setup_logging
from agent.routes.query import router as query_router
from agent.routes.task import router as task_router
from agent.routes.upload import router as upload_router


def create_app() -> FastAPI:
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        description="Operator Agent - CANN operator constraint extraction and test generation",
    )

    app.include_router(upload_router)
    app.include_router(query_router)
    app.include_router(task_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return (settings.static_dir / "index.html").read_text(encoding="utf-8")

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    return app
