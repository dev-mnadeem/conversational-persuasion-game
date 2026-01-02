"""Hosted-model adapter for the Venice AI OpenAI-compatible API.

Opt in with ``DOORMAN_PROVIDER=venice`` and a ``VENICE_API_KEY``. The key is
read here, server side, and never appears in any response body — the browser
talks only to this backend.
"""

from __future__ import annotations

import base64
import json
import logging
import re

import requests

from ..config import Settings
from ..game.prompts import (
    EJECT_INSTRUCTION,
    GRANT_INSTRUCTION,
    REFUSE_INSTRUCTION,
    build_doorman_prompt,
    build_judge_prompt,
)
from ..game.rules import GameStatus, clamp_turn_delta
from .base import (
    DoormanContext,
    DoormanProvider,
    DoormanUnavailable,
    JudgeContext,
    JudgeUnavailable,
    Verdict,
)

logger = logging.getLogger(__name__)

#: Reasoning models leak chain-of-thought inside these tags.
_THINK_TAGS = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

#: An *unterminated* opening tag is the nastier case: a truncated reply used to
#: leave the JSON unparseable, which silently scored the turn zero forever.
_OPEN_THINK = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)

_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

#: Last-resort extraction of the first JSON object in a chatty reply.
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

_OUTCOME_INSTRUCTIONS = {
    GameStatus.ACCESS_GRANTED: GRANT_INSTRUCTION,
    GameStatus.TURNS_EXHAUSTED: REFUSE_INSTRUCTION,
    GameStatus.EJECTED: EJECT_INSTRUCTION,
}


def strip_reasoning(text: str) -> str:
    """Remove chain-of-thought tags, closed or left hanging."""
    return _OPEN_THINK.sub("", _THINK_TAGS.sub("", text or "")).strip()


def parse_verdict(content: str) -> Verdict:
    """Parse a judge reply into a :class:`Verdict`.

    Raises :class:`JudgeUnavailable` when no score can be recovered. The
    previous behaviour — return zero and carry on — meant a model stuck in a
    refusal loop produced a run that could never be won and never ended.
    """
    cleaned = strip_reasoning(content)
    fenced = _CODE_FENCE.search(cleaned)
    if fenced:
        cleaned = fenced.group(1)
    else:
        obj = _JSON_OBJECT.search(cleaned)
        if obj:
            cleaned = obj.group(0)

    try:
        payload = json.loads(cleaned)
        score = clamp_turn_delta(int(payload["score"]))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise JudgeUnavailable(f"judge reply was not scoreable: {content[:200]!r}") from exc

    reasoning = str(payload.get("reasoning") or "No reasoning supplied.")
    return Verdict(score=score, reasoning=reasoning, tactic="model")


class VeniceDoormanProvider(DoormanProvider):
    """Calls two hosted chat models: one to score, one to speak."""

    name = "venice"
    offline = False

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        if not settings.venice_api_key:
            raise ValueError("VENICE_API_KEY is required for the venice provider")
        self._settings = settings
        self._http = session or requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.venice_api_key}",
            "Content-Type": "application/json",
        }

    def _chat(self, model: str, messages: list[dict]) -> str:
        response = self._http.post(
            self._settings.venice_chat_url,
            headers=self._headers,
            json={"model": model, "messages": messages},
            timeout=self._settings.request_timeout_seconds,
        )
        if response.status_code != 200:
            raise ProviderHTTPError(model, response.status_code)
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as exc:
            raise ProviderHTTPError(model, response.status_code) from exc

    def judge(self, context: JudgeContext) -> Verdict:
        prompt = build_judge_prompt(context.history, context.fenced_message)
        try:
            content = self._chat(self._settings.judge_model, [{"role": "system", "content": prompt}])
        except (requests.RequestException, ProviderHTTPError) as exc:
            raise JudgeUnavailable(str(exc)) from exc
        return parse_verdict(content)

    def respond(self, context: DoormanContext) -> str:
        system = build_doorman_prompt(
            context.mood,
            _OUTCOME_INSTRUCTIONS.get(context.status, ""),
        )
        messages: list[dict] = [{"role": "system", "content": system}]
        messages.extend(context.history)
        messages.append({"role": "user", "content": context.fenced_message})

        try:
            content = self._chat(self._settings.doorman_model, messages)
        except (requests.RequestException, ProviderHTTPError) as exc:
            raise DoormanUnavailable(str(exc)) from exc

        reply = strip_reasoning(content)
        if not reply:
            raise DoormanUnavailable("doorman returned an empty line")
        return reply

    def speak(self, text: str) -> str | None:
        settings = self._settings
        if not settings.tts_enabled:
            return None
        spoken = re.sub(r"\*[^*]+\*", "", text).replace('"', "").strip()
        if not spoken:
            return None
        try:
            response = self._http.post(
                settings.venice_tts_url,
                headers=self._headers,
                json={"model": settings.tts_model, "input": spoken, "voice": settings.tts_voice},
                timeout=settings.tts_timeout_seconds,
            )
        except requests.RequestException:
            logger.warning("tts request failed", exc_info=True)
            return None
        if response.status_code != 200:
            logger.warning("tts returned %s", response.status_code)
            return None
        return base64.b64encode(response.content).decode("utf-8")


class ProviderHTTPError(RuntimeError):
    """Non-200 from the upstream API. The status is logged, never echoed."""

    def __init__(self, model: str, status: int) -> None:
        super().__init__(f"upstream returned {status} for model {model}")
        self.model = model
        self.status = status
