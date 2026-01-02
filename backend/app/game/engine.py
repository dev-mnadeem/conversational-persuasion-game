"""Turn resolution: the only place a score is allowed to change.

The engine owns the run's lifecycle. Routes call :meth:`GameEngine.play_turn`
and get back a :class:`TurnResult`; nothing else in the codebase may write to
``Session.cumulative_score`` or ``Session.status``.

The order below is deliberate. Injection screening happens *before* the judge
is consulted, so a message trying to dictate its own score is scored by the
rulebook instead of by a model that might agree with it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..providers.base import (
    DoormanContext,
    DoormanProvider,
    DoormanUnavailable,
    JudgeContext,
    JudgeUnavailable,
    Verdict,
)
from ..sessions.models import Session, Turn
from ..sessions.store import SessionStore
from . import injection
from .rules import (
    HISTORY_WINDOW_MESSAGES,
    INJECTION_PENALTY,
    GameStatus,
    apply_delta,
    mood_for_score,
    resolve_status,
)

logger = logging.getLogger(__name__)

#: Substituted when the doorman provider fails. The run still advances — a mute
#: Marcus must not be able to strand a player in an unfinishable state.
DOORMAN_FALLBACK_LINE = "*stares at you, says nothing, and gestures at the queue*"


class GameOver(RuntimeError):
    """Raised when a player sends a message into a finished run."""

    def __init__(self, status: GameStatus) -> None:
        super().__init__(f"this run already ended: {status.value}")
        self.status = status


class EmptyMessage(ValueError):
    """Raised when the player submits nothing but whitespace."""


@dataclass(frozen=True)
class TurnResult:
    """Everything the transport layer needs after one turn."""

    session: Session
    turn: Turn
    audio_base64: str | None = None

    @property
    def injection_blocked(self) -> bool:
        return self.turn.tactic == "injection"


class GameEngine:
    """Applies the rulebook to one player message at a time."""

    def __init__(
        self,
        provider: DoormanProvider,
        store: SessionStore,
        max_message_chars: int = 500,
    ) -> None:
        self._provider = provider
        self._store = store
        self._max_message_chars = max_message_chars

    @property
    def provider(self) -> DoormanProvider:
        return self._provider

    def play_turn(self, session: Session, message: str) -> TurnResult:
        """Score one message, advance the run and persist it."""
        if session.status.is_terminal:
            raise GameOver(session.status)

        clean = injection.sanitise(message)[: self._max_message_chars]
        if not clean:
            raise EmptyMessage("message cannot be empty")

        verdict = self._score(session, clean)
        session.cumulative_score = apply_delta(session.cumulative_score, verdict.score)
        session.turns_used += 1
        session.status = resolve_status(session.cumulative_score, session.turns_used)

        reply = self._speak(session, clean, verdict)
        turn = Turn(
            index=session.turns_used,
            player_message=clean,
            doorman_reply=reply,
            score_delta=verdict.score,
            reasoning=verdict.reasoning,
            tactic=verdict.tactic,
        )
        session.turns.append(turn)
        self._store.save(session)

        audio = None
        if session.status is not GameStatus.EJECTED:
            audio = self._provider.speak(reply)

        return TurnResult(session=session, turn=turn, audio_base64=audio)

    # -- internals --------------------------------------------------------

    def _score(self, session: Session, message: str) -> Verdict:
        """Produce the verdict for one message.

        A detected injection attempt never reaches the provider: the engine
        applies a fixed penalty itself. That is the difference between telling
        a model to resist and not giving it the chance to fold.
        """
        scan = injection.scan(message)
        if scan.detected:
            logger.info("injection attempt on session %s: %s", session.session_id, scan.patterns)
            return Verdict(score=INJECTION_PENALTY, reasoning=scan.summary, tactic="injection")

        context = JudgeContext(
            history=self._history_text(session),
            fenced_message=injection.fence(message),
            raw_message=message,
            turn_index=session.turns_used + 1,
            previous_tactics=tuple(turn.tactic for turn in session.turns),
            session_id=session.session_id,
        )
        return self._provider.judge(context).clamped()

    def _speak(self, session: Session, message: str, verdict: Verdict) -> str:
        context = DoormanContext(
            history=session.transcript()[-HISTORY_WINDOW_MESSAGES:],
            fenced_message=injection.fence(message),
            raw_message=message,
            mood=mood_for_score(session.cumulative_score),
            status=session.status,
            tactic=verdict.tactic,
            turn_index=session.turns_used,
            session_id=session.session_id,
        )
        try:
            return self._provider.respond(context)
        except DoormanUnavailable:
            logger.warning("doorman provider failed on session %s", session.session_id, exc_info=True)
            return DOORMAN_FALLBACK_LINE

    def _history_text(self, session: Session) -> str:
        """Render the windowed transcript for a text prompt."""
        window = session.transcript()[-HISTORY_WINDOW_MESSAGES:]
        if not window:
            return "[no conversation yet — this is the player's opening line]"

        lines = [f"{'Player' if item['role'] == 'user' else 'Marcus'}: {item['content']}" for item in window]
        omitted = len(session.transcript()) - len(window)
        if omitted > 0:
            lines.insert(0, f"[...{omitted} earlier messages omitted...]")
        return "\n".join(lines)


__all__ = [
    "DOORMAN_FALLBACK_LINE",
    "EmptyMessage",
    "GameEngine",
    "GameOver",
    "JudgeUnavailable",
    "TurnResult",
]
