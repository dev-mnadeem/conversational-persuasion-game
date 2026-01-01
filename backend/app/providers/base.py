"""The port every doorman brain plugs into.

The engine only ever talks to :class:`DoormanProvider`. That is what lets the
repo ship a deterministic provider as the default and a hosted model as an
opt-in, without the game rules knowing which one is answering.

The two halves are deliberately asymmetric:

* :meth:`DoormanProvider.judge` is **authoritative** — its verdict moves the
  score, so a failure must be raised (:class:`JudgeUnavailable`) and the turn
  refused rather than silently scored zero.
* :meth:`DoormanProvider.respond` is **cosmetic** — if it fails the engine
  substitutes a line and the run still advances, because a mute doorman must
  not be able to strand a run in a state it can neither win nor end.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..game.rules import GameStatus, Mood, clamp_turn_delta


class ProviderError(RuntimeError):
    """Base class for provider failures."""


class JudgeUnavailable(ProviderError):
    """The judge could not produce a usable verdict for this turn."""


class DoormanUnavailable(ProviderError):
    """Marcus could not produce a line. The engine substitutes one."""


@dataclass(frozen=True)
class JudgeContext:
    """Everything the judge is allowed to see."""

    history: str
    fenced_message: str
    raw_message: str
    turn_index: int
    previous_tactics: tuple[str, ...] = ()
    session_id: str = ""


@dataclass(frozen=True)
class DoormanContext:
    """Everything Marcus is allowed to see."""

    history: list[dict]
    fenced_message: str
    raw_message: str
    mood: Mood
    status: GameStatus
    tactic: str = "neutral"
    turn_index: int = 0
    session_id: str = ""


@dataclass(frozen=True)
class Verdict:
    """A scored judgement of one player line."""

    score: int
    reasoning: str
    tactic: str = "unknown"

    def clamped(self) -> Verdict:
        return Verdict(clamp_turn_delta(self.score), self.reasoning, self.tactic)


class DoormanProvider(ABC):
    """Scores a line and speaks as Marcus."""

    #: Stable identifier surfaced on ``/healthz`` and in the UI.
    name: str = "abstract"

    #: True when the provider needs no network and no credentials.
    offline: bool = False

    @abstractmethod
    def judge(self, context: JudgeContext) -> Verdict:
        """Score the player's latest line. Raise :class:`JudgeUnavailable` on failure."""

    @abstractmethod
    def respond(self, context: DoormanContext) -> str:
        """Speak as Marcus. Raise :class:`DoormanUnavailable` on failure."""

    def speak(self, text: str) -> str | None:
        """Optional text-to-speech. Returns base64 audio, or None."""
        return None
