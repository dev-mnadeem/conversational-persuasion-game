"""The server-owned record of a single run.

The client never sends a score. It sends a session id and a sentence: every
number in this dataclass is computed and stored here, on the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..game.rules import MAX_TURNS, GameStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Turn:
    """One player message, its verdict, and Marcus's reply."""

    index: int
    player_message: str
    doorman_reply: str
    score_delta: int
    reasoning: str
    tactic: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "player_message": self.player_message,
            "doorman_reply": self.doorman_reply,
            "score_delta": self.score_delta,
            "reasoning": self.reasoning,
            "tactic": self.tactic,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Turn":
        return cls(
            index=int(raw["index"]),
            player_message=raw["player_message"],
            doorman_reply=raw["doorman_reply"],
            score_delta=int(raw["score_delta"]),
            reasoning=raw.get("reasoning", ""),
            tactic=raw.get("tactic", "unknown"),
            created_at=raw.get("created_at", _now()),
        )


@dataclass
class Session:
    """A run of the game, addressed by an opaque server-issued id."""

    session_id: str
    cumulative_score: int = 0
    turns_used: int = 0
    status: GameStatus = GameStatus.IN_PROGRESS
    turns: list[Turn] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @property
    def turns_remaining(self) -> int:
        return max(0, MAX_TURNS - self.turns_used)

    def transcript(self) -> list[dict]:
        """Flatten turns into an alternating chat transcript."""
        messages: list[dict] = []
        for turn in self.turns:
            messages.append({"role": "user", "content": turn.player_message})
            messages.append({"role": "assistant", "content": turn.doorman_reply})
        return messages

    def touch(self) -> None:
        self.updated_at = _now()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "cumulative_score": self.cumulative_score,
            "turns_used": self.turns_used,
            "status": self.status.value,
            "turns": [turn.to_dict() for turn in self.turns],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Session":
        return cls(
            session_id=raw["session_id"],
            cumulative_score=int(raw.get("cumulative_score", 0)),
            turns_used=int(raw.get("turns_used", 0)),
            status=GameStatus(raw.get("status", GameStatus.IN_PROGRESS.value)),
            turns=[Turn.from_dict(item) for item in raw.get("turns", [])],
            created_at=raw.get("created_at", _now()),
            updated_at=raw.get("updated_at", _now()),
        )
