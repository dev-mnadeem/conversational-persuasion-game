"""Wiring. One settings object, one store, one provider, one engine per process."""

from __future__ import annotations

from functools import lru_cache

from ..config import Settings, load_settings
from ..game.engine import GameEngine
from ..providers import DoormanProvider, build_provider
from ..sessions.store import JsonFileSessionStore, SessionStore


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


@lru_cache(maxsize=1)
def get_store() -> SessionStore:
    settings = get_settings()
    return JsonFileSessionStore(settings.sessions_dir, settings.session_cache_size)


@lru_cache(maxsize=1)
def get_provider() -> DoormanProvider:
    return build_provider(get_settings())


@lru_cache(maxsize=1)
def get_engine() -> GameEngine:
    settings = get_settings()
    return GameEngine(get_provider(), get_store(), settings.max_message_chars)


def reset_dependency_cache() -> None:
    """Drop every cached singleton. Used by the tests."""
    for cached in (get_settings, get_store, get_provider, get_engine):
        cached.cache_clear()
