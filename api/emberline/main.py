"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from emberline import __version__
from emberline.config import Settings, get_settings
from emberline.data.firms import FirmsClient
from emberline.data.store import HotspotStore
from emberline.jobs import JobManager
from emberline.routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="EMBERLINE API",
        version=__version__,
        description="Harmonized MODIS + VIIRS fire record. Data: NASA FIRMS.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],  # locked to the web app, no wildcard
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    store = HotspotStore(settings.data_dir)
    app.state.settings = settings
    app.state.store = store
    key = settings.firms_map_key
    factory = (lambda: FirmsClient(key, guard_every=8)) if key else None
    app.state.jobs = JobManager(store, settings.data_dir / "results", firms_factory=factory)
    app.include_router(router)
    return app


app = create_app()
