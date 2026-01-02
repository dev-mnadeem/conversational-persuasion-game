"""The rulebook in isolation: bands, clamping and lifecycle resolution."""

import pytest

from app.game.rules import (
    EJECTION_SCORE,
    INFLUENCE_THRESHOLD,
    MAX_TURN_DELTA,
    MAX_TURNS,
    MIN_TURN_DELTA,
    GameStatus,
    Mood,
    apply_delta,
    clamp_turn_delta,
    mood_for_score,
    resolve_status,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-50, Mood.HOSTILE),
        (-1, Mood.HOSTILE),
        (0, Mood.NEUTRAL),
        (29, Mood.NEUTRAL),
        (30, Mood.WARMING),
        (69, Mood.WARMING),
        (70, Mood.IMPRESSED),
        (250, Mood.IMPRESSED),
    ],
)
def test_mood_bands_cover_the_whole_range(score, expected):
    assert mood_for_score(score) is expected


@pytest.mark.parametrize(("raw", "expected"), [(999, MAX_TURN_DELTA), (-999, MIN_TURN_DELTA), (7, 7)])
def test_turn_delta_is_clamped(raw, expected):
    assert clamp_turn_delta(raw) == expected


def test_no_single_turn_can_win_from_zero():
    """A talked-into-it judge still cannot end the game in one move."""
    assert apply_delta(0, 10_000) < INFLUENCE_THRESHOLD


def test_score_never_falls_below_the_ejection_floor():
    assert apply_delta(EJECTION_SCORE, -20) == EJECTION_SCORE


def test_reaching_the_threshold_wins_even_on_the_final_turn():
    assert resolve_status(INFLUENCE_THRESHOLD, MAX_TURNS) is GameStatus.ACCESS_GRANTED


def test_hitting_the_floor_ejects_before_turns_run_out():
    assert resolve_status(EJECTION_SCORE, 2) is GameStatus.EJECTED


def test_running_out_of_turns_is_a_loss_not_a_stall():
    """Without this the game had no lose condition and no way to end."""
    assert resolve_status(50, MAX_TURNS) is GameStatus.TURNS_EXHAUSTED


def test_mid_run_is_in_progress():
    status = resolve_status(50, 3)
    assert status is GameStatus.IN_PROGRESS
    assert not status.is_terminal


@pytest.mark.parametrize(
    "status",
    [GameStatus.ACCESS_GRANTED, GameStatus.TURNS_EXHAUSTED, GameStatus.EJECTED],
)
def test_every_end_state_is_terminal(status):
    assert status.is_terminal


def test_only_access_granted_is_a_win():
    wins = [status for status in GameStatus if status.is_win]
    assert wins == [GameStatus.ACCESS_GRANTED]
