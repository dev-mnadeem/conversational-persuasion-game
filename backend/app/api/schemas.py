"""Typed request and response bodies.

Note what is *absent* from :class:`TurnResponse` while a run is live: the
judge's reasoning. It quotes Marcus's secret profile, and shipping it to the
browser every turn handed the player the answer key in the network tab. It is
released in one go by ``/debrief`` once the run is over.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..game.rules import MAX_TURNS, GameStatus
from ..sessions.models import Session


class TurnRequest(BaseModel):
    """One line spoken at the doorman."""

    message: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    role: str
    content: str


class SessionState(BaseModel):
    """Everything the client is allowed to know about a live run."""

    session_id: str
    cumulative_score: int
    threshold: int
    status: GameStatus
    turns_used: int
    turns_remaining: int
    max_turns: int = MAX_TURNS
    transcript: list[MessageOut] = []

    @classmethod
    def from_session(cls, session: Session, threshold: int) -> SessionState:
        return cls(
            session_id=session.session_id,
            cumulative_score=session.cumulative_score,
            threshold=threshold,
            status=session.status,
            turns_used=session.turns_used,
            turns_remaining=session.turns_remaining,
            transcript=[MessageOut(**item) for item in session.transcript()],
        )


class TurnResponse(BaseModel):
    """The result of one turn."""

    reply: str
    score_delta: int
    cumulative_score: int
    threshold: int
    status: GameStatus
    turns_used: int
    turns_remaining: int
    max_turns: int = MAX_TURNS
    injection_blocked: bool = False
    audio_base64: str | None = None


class DebriefTurn(BaseModel):
    """One turn with the judge's reasoning attached."""

    index: int
    player_message: str
    doorman_reply: str
    score_delta: int
    tactic: str
    reasoning: str


class Debrief(BaseModel):
    """Post-game reveal: what Marcus was actually scoring all along."""

    session_id: str
    status: GameStatus
    cumulative_score: int
    threshold: int
    turns_used: int
    best_turn: int | None
    worst_turn: int | None
    turns: list[DebriefTurn]


class SessionSummary(BaseModel):
    session_id: str
    cumulative_score: int
    turns_used: int
    status: GameStatus
    created_at: str
    updated_at: str


class Health(BaseModel):
    status: str
    provider: str
    offline: bool
    threshold: int
    max_turns: int
