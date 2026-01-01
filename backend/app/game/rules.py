"""The numbers that make this a game rather than a chat window.

Every tunable that affects whether a player wins, loses or runs out of road is
declared here so the rulebook can be read in one screen — and so the tests can
assert against the same constants the engine uses.
"""

from __future__ import annotations

from enum import StrEnum

# --- Win / lose boundaries ------------------------------------------------

#: Cumulative influence needed for Marcus to open the door.
INFLUENCE_THRESHOLD = 100

#: Cumulative influence at which Marcus stops engaging and the run is over.
EJECTION_SCORE = -50

#: Hard budget of player messages. Without this the game had no lose condition
#: at all: a player could talk forever and a stalled judge left the run in a
#: state that could neither be won nor ended.
MAX_TURNS = 12

# --- Per-turn scoring -----------------------------------------------------

#: The judge's verdict is clamped into this band before it is applied, so no
#: single turn — and no talked-into-it model — can end the game on its own.
MIN_TURN_DELTA = -20
MAX_TURN_DELTA = 20

#: Fixed penalty applied when the player tries to instruct the game rather
#: than persuade the character. Applied by the engine, not by the model.
INJECTION_PENALTY = -15

# --- Prompt context -------------------------------------------------------

#: Past messages (player + doorman combined) replayed into a prompt. Eight
#: exchanges out of a twelve-turn budget: enough for Marcus to call back an
#: earlier line, short enough that the prompt cannot grow without bound.
HISTORY_WINDOW_MESSAGES = 16

#: Below this length a message cannot earn more than ``SHORT_MESSAGE_MAX_GAIN``.
SHORT_MESSAGE_CHARS = 15
SHORT_MESSAGE_MAX_GAIN = 2


class GameStatus(StrEnum):
    """Lifecycle of a single run."""

    IN_PROGRESS = "in_progress"
    ACCESS_GRANTED = "access_granted"
    TURNS_EXHAUSTED = "turns_exhausted"
    EJECTED = "ejected"

    @property
    def is_terminal(self) -> bool:
        return self is not GameStatus.IN_PROGRESS

    @property
    def is_win(self) -> bool:
        return self is GameStatus.ACCESS_GRANTED


class Mood(StrEnum):
    """How warm Marcus is, derived from cumulative influence."""

    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    WARMING = "warming"
    IMPRESSED = "impressed"


#: Lower bound (inclusive) of each mood band, highest first.
MOOD_BANDS: tuple[tuple[int, Mood], ...] = (
    (70, Mood.IMPRESSED),
    (30, Mood.WARMING),
    (0, Mood.NEUTRAL),
    (EJECTION_SCORE, Mood.HOSTILE),
)


def mood_for_score(cumulative_score: int) -> Mood:
    """Map a cumulative influence score onto Marcus's mood band."""
    for floor, mood in MOOD_BANDS:
        if cumulative_score >= floor:
            return mood
    return Mood.HOSTILE


def clamp_turn_delta(delta: int) -> int:
    """Clamp a judge verdict into the per-turn band."""
    return max(MIN_TURN_DELTA, min(MAX_TURN_DELTA, delta))


def apply_delta(cumulative_score: int, delta: int) -> int:
    """Apply a clamped delta to the running score, honouring the floor."""
    return max(EJECTION_SCORE, cumulative_score + clamp_turn_delta(delta))


def resolve_status(cumulative_score: int, turns_used: int) -> GameStatus:
    """Decide the lifecycle state implied by a score and a turn count.

    Order matters: reaching the threshold wins even on the final turn, and
    being ejected outranks simply running out of turns.
    """
    if cumulative_score >= INFLUENCE_THRESHOLD:
        return GameStatus.ACCESS_GRANTED
    if cumulative_score <= EJECTION_SCORE:
        return GameStatus.EJECTED
    if turns_used >= MAX_TURNS:
        return GameStatus.TURNS_EXHAUSTED
    return GameStatus.IN_PROGRESS
