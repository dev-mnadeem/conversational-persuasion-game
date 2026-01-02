"""Configuration resolution, including the default that matters most."""

import pytest

from app.config import load_settings
from app.providers import PROVIDERS, build_provider

ENV_KEYS = [
    "DOORMAN_PROVIDER",
    "VENICE_API_KEY",
    "DOORMAN_TTS_ENABLED",
    "DOORMAN_CORS_ORIGINS",
    "DOORMAN_MAX_MESSAGE_CHARS",
    "DOORMAN_ADMIN_TOKEN",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_a_clone_with_no_env_runs_offline():
    """No key, no config, still a playable game."""
    settings = load_settings()
    assert settings.provider == "local"
    assert build_provider(settings).offline is True


def test_a_key_alone_selects_the_hosted_provider(monkeypatch):
    monkeypatch.setenv("VENICE_API_KEY", "abc")
    assert load_settings().provider == "venice"


def test_an_explicit_provider_wins_over_a_present_key(monkeypatch):
    monkeypatch.setenv("VENICE_API_KEY", "abc")
    monkeypatch.setenv("DOORMAN_PROVIDER", "local")
    assert load_settings().provider == "local"


def test_an_unknown_provider_fails_loudly(monkeypatch):
    monkeypatch.setenv("DOORMAN_PROVIDER", "gpt9")
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider(load_settings())
    assert set(PROVIDERS) == {"local", "venice"}


def test_speech_is_off_by_default():
    assert load_settings().tts_enabled is False


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
def test_truthy_flags_are_accepted(monkeypatch, raw):
    monkeypatch.setenv("DOORMAN_TTS_ENABLED", raw)
    assert load_settings().tts_enabled is True


def test_cors_origins_are_an_explicit_list(monkeypatch):
    monkeypatch.setenv("DOORMAN_CORS_ORIGINS", "https://a.example, https://b.example")
    assert load_settings().cors_origins == ["https://a.example", "https://b.example"]


def test_the_default_origins_do_not_include_a_wildcard():
    assert "*" not in load_settings().cors_origins


def test_a_nonsense_integer_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("DOORMAN_MAX_MESSAGE_CHARS", "lots")
    assert load_settings().max_message_chars == 500


def test_admin_endpoints_are_disabled_by_default():
    assert load_settings().admin_token is None


def test_urls_are_derived_from_one_base(monkeypatch):
    monkeypatch.setenv("VENICE_BASE_URL", "https://example.test/v9/")
    settings = load_settings()
    assert settings.venice_chat_url == "https://example.test/v9/chat/completions"
    assert settings.venice_tts_url == "https://example.test/v9/audio/speech"
    assert settings.venice_models_url == "https://example.test/v9/models"
