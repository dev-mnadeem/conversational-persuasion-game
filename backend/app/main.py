"""Application factory for the Doorman Game backend."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.dependencies import get_provider, get_settings
from .api.routes import router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

API_TITLE = "The Doorman Game"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "A persuasion game. Talk your way past Marcus, the doorman at BLVD Dubai. "
    "A hidden judge scores every line you speak against his secret profile."
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=API_TITLE, version=API_VERSION, description=API_DESCRIPTION)

    # The old configuration paired a wildcard origin with credentials, which
    # browsers reject outright. Origins are now an explicit, configurable list.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )
    app.include_router(router)

    provider = get_provider()
    logger.info("doorman provider=%s offline=%s", provider.name, provider.offline)
    return app


app = create_app()
