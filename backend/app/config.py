"""Runtime configuration, resolved once from the environment.

Everything the game needs to know about *where* it runs lives here so no other
module reads ``os.environ`` directly. The important default is
``DOORMAN_PROVIDER=local``: the game is fully playable, testable and
screenshottable without an API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parent.parent

#: The dev client is pinned to 7322 in frontend/vite.config.js. Development is
#: proxied and therefore same-origin anyway — this list only matters when the
#: two are served from different hosts.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:7322",
    "http://127.0.0.1:7322",
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable view of the process environment."""

    provider: str = "local"
    venice_api_key: str | None = None
    venice_base_url: str = "https://api.venice.ai/api/v1"
    judge_model: str = "qwen3-next-80b"
    doorman_model: str = "qwen3-4b"
    request_timeout_seconds: int = 60

    tts_enabled: bool = False
    tts_model: str = "tts-kokoro"
    tts_voice: str = "am_adam"
    tts_timeout_seconds: int = 30

    sessions_dir: Path = BACKEND_ROOT / "sessions"
    session_cache_size: int = 256
    max_message_chars: int = 500

    cors_origins: list[str] = field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))
    admin_token: str | None = None

    @property
    def venice_chat_url(self) -> str:
        return f"{self.venice_base_url.rstrip('/')}/chat/completions"

    @property
    def venice_tts_url(self) -> str:
        return f"{self.venice_base_url.rstrip('/')}/audio/speech"

    @property
    def venice_models_url(self) -> str:
        return f"{self.venice_base_url.rstrip('/')}/models"


def load_settings() -> Settings:
    """Build :class:`Settings` from the environment.

    ``DOORMAN_PROVIDER`` may be left unset. In that case the remote provider is
    only selected when an API key is actually present, so a fresh clone starts
    in local mode instead of failing on the first turn.
    """
    api_key = os.getenv("VENICE_API_KEY") or None
    provider = (os.getenv("DOORMAN_PROVIDER") or "").strip().lower()
    if not provider:
        provider = "venice" if api_key else "local"

    return Settings(
        provider=provider,
        venice_api_key=api_key,
        venice_base_url=os.getenv("VENICE_BASE_URL", "https://api.venice.ai/api/v1"),
        judge_model=os.getenv("DOORMAN_JUDGE_MODEL", "qwen3-next-80b"),
        doorman_model=os.getenv("DOORMAN_DOORMAN_MODEL", "qwen3-4b"),
        request_timeout_seconds=_env_int("DOORMAN_REQUEST_TIMEOUT", 60),
        tts_enabled=_env_bool("DOORMAN_TTS_ENABLED", False),
        tts_model=os.getenv("DOORMAN_TTS_MODEL", "tts-kokoro"),
        tts_voice=os.getenv("DOORMAN_TTS_VOICE", "am_adam"),
        tts_timeout_seconds=_env_int("DOORMAN_TTS_TIMEOUT", 30),
        sessions_dir=Path(os.getenv("DOORMAN_SESSIONS_DIR", str(BACKEND_ROOT / "sessions"))),
        session_cache_size=_env_int("DOORMAN_SESSION_CACHE_SIZE", 256),
        max_message_chars=_env_int("DOORMAN_MAX_MESSAGE_CHARS", 500),
        cors_origins=_env_list("DOORMAN_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        admin_token=os.getenv("DOORMAN_ADMIN_TOKEN") or None,
    )
