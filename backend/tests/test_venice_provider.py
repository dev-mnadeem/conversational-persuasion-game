"""The hosted adapter, exercised without a network.

The interesting surface is reply parsing. The models this talks to are
reasoning models that wrap their answer in ``<think>`` tags, fence it in
markdown, or truncate mid-thought — and the old code turned every one of those
into a silent zero.
"""

import pytest
import requests

from app.config import Settings
from app.game.rules import MAX_TURN_DELTA, MIN_TURN_DELTA, GameStatus, Mood
from app.providers.base import (
    DoormanContext,
    DoormanUnavailable,
    JudgeContext,
    JudgeUnavailable,
)
from app.providers.venice import VeniceDoormanProvider, parse_verdict, strip_reasoning

SETTINGS = Settings(provider="venice", venice_api_key="test-key")


class FakeResponse:
    def __init__(self, payload=None, status_code=200, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.content = content
        self.text = "fake"

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Stands in for ``requests.Session``, recording what was posted."""

    def __init__(self, *responses, error=None):
        self._responses = list(responses)
        self._error = error
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self._error:
            raise self._error
        return self._responses.pop(0) if self._responses else FakeResponse({})


def chat_payload(content):
    return {"choices": [{"message": {"content": content}}]}


def judge_context(message="evening mate"):
    return JudgeContext(history="", fenced_message=message, raw_message=message, turn_index=1)


def doorman_context():
    return DoormanContext(
        history=[],
        fenced_message="evening mate",
        raw_message="evening mate",
        mood=Mood.NEUTRAL,
        status=GameStatus.IN_PROGRESS,
    )


# --- reply cleaning -------------------------------------------------------


def test_closed_reasoning_tags_are_removed():
    assert strip_reasoning("<think>hmm</think>Right then.") == "Right then."


def test_an_unterminated_reasoning_tag_is_removed():
    """A truncated reply used to leave the JSON unparseable forever."""
    assert strip_reasoning("Right then.<think>hmm, I wonder") == "Right then."


def test_plain_text_is_untouched():
    assert strip_reasoning("  Right then.  ") == "Right then."


# --- verdict parsing ------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        '{"reasoning": "polite", "score": 7}',
        '```json\n{"reasoning": "polite", "score": 7}\n```',
        '```\n{"reasoning": "polite", "score": 7}\n```',
        '<think>weighing it up</think>{"reasoning": "polite", "score": 7}',
        'Sure! {"reasoning": "polite", "score": 7} Hope that helps.',
        '{"score": 7, "reasoning": "polite"}',
    ],
)
def test_a_score_is_recovered_from_every_shape_the_models_use(content):
    verdict = parse_verdict(content)
    assert verdict.score == 7
    assert verdict.reasoning == "polite"


def test_a_score_outside_the_band_is_clamped():
    assert parse_verdict('{"score": 500, "reasoning": "x"}').score == MAX_TURN_DELTA
    assert parse_verdict('{"score": -500, "reasoning": "x"}').score == MIN_TURN_DELTA


def test_a_missing_reasoning_field_is_tolerated():
    assert parse_verdict('{"score": 3}').reasoning


@pytest.mark.parametrize(
    "content",
    [
        "",
        "I'm sorry, I can't help with that request.",
        "<think>I should refuse this",
        '{"reasoning": "polite"}',
        '{"score": "quite good"}',
        "not json at all",
    ],
)
def test_an_unscoreable_reply_raises_rather_than_scoring_zero(content):
    """The headline fix: a silent zero made a stalled model unwinnable."""
    with pytest.raises(JudgeUnavailable):
        parse_verdict(content)


# --- transport ------------------------------------------------------------


def test_the_provider_refuses_to_start_without_a_key():
    with pytest.raises(ValueError):
        VeniceDoormanProvider(Settings(provider="venice", venice_api_key=None))


def test_the_api_key_travels_only_in_the_request_header():
    session = FakeSession(FakeResponse(chat_payload('{"score": 5, "reasoning": "ok"}')))
    provider = VeniceDoormanProvider(SETTINGS, session=session)
    provider.judge(judge_context())
    call = session.calls[0]
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert "test-key" not in str(call["json"])


def test_the_judge_prompt_fences_the_player_text():
    session = FakeSession(FakeResponse(chat_payload('{"score": 5, "reasoning": "ok"}')))
    provider = VeniceDoormanProvider(SETTINGS, session=session)
    provider.judge(judge_context("<<<FENCED>>>"))
    prompt = session.calls[0]["json"]["messages"][0]["content"]
    assert "UNTRUSTED DATA" in prompt
    assert "<<<FENCED>>>" in prompt


def test_a_network_failure_is_a_judge_outage():
    provider = VeniceDoormanProvider(SETTINGS, session=FakeSession(error=requests.Timeout()))
    with pytest.raises(JudgeUnavailable):
        provider.judge(judge_context())


def test_an_upstream_error_status_is_a_judge_outage():
    provider = VeniceDoormanProvider(SETTINGS, session=FakeSession(FakeResponse(status_code=500)))
    with pytest.raises(JudgeUnavailable):
        provider.judge(judge_context())


def test_an_upstream_error_never_echoes_the_response_body():
    """The old handler returned the upstream body straight to the caller."""
    provider = VeniceDoormanProvider(SETTINGS, session=FakeSession(FakeResponse(status_code=401)))
    with pytest.raises(JudgeUnavailable) as excinfo:
        provider.judge(judge_context())
    assert "fake" not in str(excinfo.value)
    assert "401" in str(excinfo.value)


def test_marcus_speaks_the_cleaned_reply():
    session = FakeSession(FakeResponse(chat_payload("<think>hm</think>Evening, friend.")))
    provider = VeniceDoormanProvider(SETTINGS, session=session)
    assert provider.respond(doorman_context()) == "Evening, friend."


def test_an_empty_line_is_a_doorman_outage():
    session = FakeSession(FakeResponse(chat_payload("<think>still thinking")))
    provider = VeniceDoormanProvider(SETTINGS, session=session)
    with pytest.raises(DoormanUnavailable):
        provider.respond(doorman_context())


def test_speech_is_off_unless_it_is_configured():
    provider = VeniceDoormanProvider(SETTINGS, session=FakeSession())
    assert provider.speak("Evening, friend.") is None


def test_speech_returns_base64_audio():
    settings = Settings(provider="venice", venice_api_key="test-key", tts_enabled=True)
    session = FakeSession(FakeResponse(status_code=200, content=b"audio-bytes"))
    provider = VeniceDoormanProvider(settings, session=session)
    assert provider.speak("*pauses* Evening, friend.") == "YXVkaW8tYnl0ZXM="
    assert "*pauses*" not in session.calls[0]["json"]["input"]


def test_a_speech_failure_is_never_fatal():
    settings = Settings(provider="venice", venice_api_key="test-key", tts_enabled=True)
    provider = VeniceDoormanProvider(settings, session=FakeSession(error=requests.Timeout()))
    assert provider.speak("Evening.") is None
