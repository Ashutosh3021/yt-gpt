"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import config
from ..auth import LocalAuthProvider, PyronitesAuthProvider
from ..events import EventBus
from ..ingest.jobs import IngestRunner
from ..version import __version__
from ..workspace.store import StoreError
from .routes import auth, sessions, settings, sources, videos, workspaces
from .static import mount_frontend

log = logging.getLogger(__name__)


def _auth_provider():
    cfg = config.load_config()
    if cfg.auth_provider == "pyronites":
        return PyronitesAuthProvider()
    return LocalAuthProvider()


def create_app() -> FastAPI:
    bus = EventBus()
    auth_provider = _auth_provider()
    workers = int(os.environ.get("YT_GPT_INGEST_WORKERS", "2") or 2)
    runner = IngestRunner(bus, workers=max(1, workers))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        config.ensure_home()
        await runner.start()
        log.info("yt-gpt %s ready at %s", __version__, config.home())
        try:
            yield
        finally:
            await runner.stop()

    app = FastAPI(
        title="yt-gpt",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.bus = bus
    app.state.auth = auth_provider
    app.state.runner = runner

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StoreError)
    async def store_error_handler(request: Request, exc: StoreError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(videos.router)
    app.include_router(sessions.router)
    app.include_router(sources.router)
    app.include_router(settings.router)
    mount_frontend(app)
    return app


app = create_app()
