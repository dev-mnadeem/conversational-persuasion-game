"""Build the configured provider.

Adding a third brain means adding one entry here and one class — the engine and
the routes do not change.
"""

from __future__ import annotations

from ..config import Settings
from .base import DoormanProvider
from .local import LocalDoormanProvider
from .venice import VeniceDoormanProvider

PROVIDERS = ("local", "venice")


def build_provider(settings: Settings) -> DoormanProvider:
    """Return the provider named by ``settings.provider``."""
    if settings.provider == "local":
        return LocalDoormanProvider()
    if settings.provider == "venice":
        return VeniceDoormanProvider(settings)
    raise ValueError(f"unknown provider {settings.provider!r}, expected one of {PROVIDERS}")
