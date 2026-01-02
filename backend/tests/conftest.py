"""Shared fixtures. Every test runs against the offline provider."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.game.engine import GameEngine  # noqa: E402
from app.providers.local import LocalDoormanProvider  # noqa: E402
from app.sessions.store import InMemorySessionStore  # noqa: E402

#: A run that reaches 100 influence inside the turn budget by varying tactics.
WINNING_SCRIPT = [
    "Good evening, mate. No rush at all, I can wait as long as you need.",
    "Can I ask you something? How long have you been on this door yourself?",
    "Someone said this room used to be the Blue Note. Did you ever hear the jazz in here?",
    "Honestly, I probably don't belong here. Never been anywhere like this.",
    "My dad passed away last year. He moved here in the nineties.",
    "Do you play anything yourself? Sorry, I'm terrible at this, I rehearsed this in the car.",
    "I know I'm nobody, but my brother loved Coltrane and I'd like to hear the band once. Do you mind?",
    "Thank you for listening, genuinely. Take your time.",
    "What's the best night you ever heard in there yourself? I'm curious.",
    "My sister played trumpet. I'm out of my depth here but could I just stand at the back?",
]

#: Bland filler that scores nothing, used to burn the turn budget.
NEUTRAL_LINE = "So anyway that is roughly the situation as it stands right now."


@pytest.fixture
def provider() -> LocalDoormanProvider:
    return LocalDoormanProvider()


@pytest.fixture
def store() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
def engine(provider, store) -> GameEngine:
    return GameEngine(provider, store)


@pytest.fixture
def session(store):
    return store.create()
