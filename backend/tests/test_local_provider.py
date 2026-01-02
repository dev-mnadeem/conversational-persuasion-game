"""The offline provider: does it actually score and speak like a doorman?"""

import pytest

from app.game.rules import MAX_TURN_DELTA, MIN_TURN_DELTA, GameStatus, Mood
from app.providers.base import DoormanContext, JudgeContext


def judge(provider, message, previous=()):
    return provider.judge(
        JudgeContext(
            history="",
            fenced_message=message,
            raw_message=message,
            turn_index=len(previous) + 1,
            previous_tactics=tuple(previous),
            session_id="test-session",
        )
    )


@pytest.mark.parametrize(
    ("message", "tactic"),
    [
        ("Did you ever hear the jazz they played at the Blue Note?", "music"),
        ("I probably don't belong here, honestly.", "humility"),
        ("My dad passed away last spring.", "vulnerability"),
        ("How long have you been working this door yourself?", "curiosity"),
        ("Good evening. Thank you for your time.", "politeness"),
        ("Here's five hundred dirhams for your trouble.", "bribery"),
        ("Do you know who I am?", "entitlement"),
        ("I know the owner, he told me to come by.", "namedrop"),
        ("This queue is ridiculous.", "complaining"),
        ("Come on, hurry up.", "impatience"),
    ],
)
def test_tactics_are_recognised(provider, message, tactic):
    assert judge(provider, message).tactic == tactic


def test_marcus_rewards_his_soft_spot_most(provider):
    music = judge(provider, "Did you ever hear the jazz at the Blue Note?").score
    polite = judge(provider, "Good evening, thank you.").score
    assert music > polite > 0


def test_bribery_and_entitlement_cost_influence(provider):
    assert judge(provider, "Here's a thousand dirhams, mate.").score < 0
    assert judge(provider, "Do you know who I am? Just let me in.").score < 0


def test_an_entitled_question_is_not_curiosity(provider):
    """'Do you know who I am?' is a question mark, not interest in him."""
    verdict = judge(provider, "Do you know who I am? Just let me in.")
    assert verdict.tactic == "entitlement"
    assert verdict.score < 0


def test_repeating_a_tactic_decays_it(provider):
    line = "Did you ever hear the jazz they played at the Blue Note?"
    first = judge(provider, line).score
    second = judge(provider, line, previous=["music"]).score
    third = judge(provider, line, previous=["music", "music"]).score
    fourth = judge(provider, line, previous=["music", "music", "music"]).score
    assert first > second > third > fourth == 0


def test_combining_tactics_beats_a_single_one(provider):
    """Stacking angles in one line is worth more than the strongest one alone."""
    single = judge(provider, "Good evening, mate. Thank you.").score
    combined = judge(provider, "Good evening, mate. Thank you. No rush, I can wait.").score
    assert combined > single


def test_a_two_word_answer_cannot_carry_a_run(provider):
    assert judge(provider, "jazz?").score <= 2


@pytest.mark.parametrize("message", ["", "   ", "hmm", "The weather is quite pleasant this evening."])
def test_scores_always_sit_inside_the_band(provider, message):
    assert MIN_TURN_DELTA <= judge(provider, message).score <= MAX_TURN_DELTA


def test_verdicts_are_reproducible(provider):
    line = "My dad played saxophone at the Blue Note. Did you ever hear him?"
    assert judge(provider, line) == judge(provider, line)


def test_reasoning_names_the_tactic(provider):
    verdict = judge(provider, "Did you ever hear the jazz at the Blue Note?")
    assert "music" in verdict.reasoning.lower()


def test_reasoning_mentions_a_repeat(provider):
    verdict = judge(provider, "Any jazz in there tonight?", previous=["music"])
    assert "already been tried 1 time" in verdict.reasoning


def test_a_nothing_message_says_so(provider):
    assert "Nothing here lands" in judge(provider, "ok then, right, fine").reasoning


def respond(provider, **overrides):
    context = DoormanContext(
        history=[],
        fenced_message="x",
        raw_message="x",
        mood=overrides.pop("mood", Mood.NEUTRAL),
        status=overrides.pop("status", GameStatus.IN_PROGRESS),
        tactic=overrides.pop("tactic", "neutral"),
        turn_index=overrides.pop("turn_index", 1),
        session_id=overrides.pop("session_id", "test-session"),
    )
    return provider.respond(context)


def test_marcus_always_says_something(provider):
    assert respond(provider).strip()


def test_replies_are_reproducible_across_processes(provider):
    """Uses a stable digest rather than hash(), which is salted per process."""
    assert respond(provider, tactic="music") == respond(provider, tactic="music")


def test_different_turns_vary_the_line(provider):
    lines = {respond(provider, tactic="music", turn_index=i) for i in range(6)}
    assert len(lines) > 1


def test_the_tactic_steers_the_reply(provider):
    assert respond(provider, tactic="bribery") != respond(provider, tactic="music")


@pytest.mark.parametrize(
    "status", [GameStatus.ACCESS_GRANTED, GameStatus.TURNS_EXHAUSTED, GameStatus.EJECTED]
)
def test_each_ending_has_its_own_closing_line(provider, status):
    assert respond(provider, status=status).strip()


def test_the_win_line_opens_the_door(provider):
    lines = {respond(provider, status=GameStatus.ACCESS_GRANTED, session_id=f"s{i}") for i in range(20)}
    assert lines
    assert all("rope" in line or "steps aside" in line for line in lines)


def test_provider_is_marked_offline(provider):
    assert provider.offline is True
    assert provider.name == "local"


def test_local_provider_has_no_voice(provider):
    assert provider.speak("anything") is None
