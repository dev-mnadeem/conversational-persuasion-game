"""A doorman you can play without an API key.

This is the default provider. It is not a mock that returns a fixed string: it
is a small rule engine that reads the same taxonomy the remote judge prompt
describes — Marcus rewards music, curiosity, humility and honesty, and punishes
money, name-dropping and entitlement — and it speaks back in character.

Two properties make it worth more than a stub:

* **Deterministic.** The same session id, turn number and message always
  produce the same verdict and the same line, so the tests can assert on real
  gameplay and a screenshot can be reproduced.
* **Playable.** Repeating a tactic decays it, so a run is won by varying the
  approach rather than by pasting the same winning sentence twelve times.
"""

from __future__ import annotations

import hashlib
import re

from ..game.rules import (
    SHORT_MESSAGE_CHARS,
    SHORT_MESSAGE_MAX_GAIN,
    GameStatus,
    Mood,
    clamp_turn_delta,
)
from .base import DoormanContext, DoormanProvider, JudgeContext, Verdict

# --- Tactic taxonomy ------------------------------------------------------

#: (tactic, weight, pattern). Weight is the influence a first, unrepeated use
#: of that tactic is worth. Negative tactics all apply; only the strongest
#: positive tactic scores, with a small bonus for combining several.
_TACTICS: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    (
        "aggression",
        -18,
        re.compile(
            r"\b(fuck|shit|idiot|moron|prick|asshole|shut up|piece of)\b|\bi'?ll (have you|get you|report you|sue)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bribery",
        -12,
        re.compile(
            r"\b(bribe|cash|dirhams?|dollars?|euros?|hundred|thousand|tip you|pay you|buy you|slip you)\b|[$£€]\s?\d",
            re.IGNORECASE,
        ),
    ),
    (
        "entitlement",
        -10,
        re.compile(
            r"\bdo you know who i am\b|\bi'?m (kind of |sort of )?(famous|a vip|somebody|important)\b|\bi deserve\b|\byou can'?t stop me\b|\bjust let me (in|through)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "namedrop",
        -6,
        re.compile(
            r"\b(i know|friends? with|friend of|cousin of|i'?m with) (the )?(owner|manager|dj|promoter|management)\b|\bon the (guest ?)?list\b|\bmy name should be\b",
            re.IGNORECASE,
        ),
    ),
    (
        "impatience",
        -5,
        re.compile(
            r"\b(hurry|how much longer|come on|any day now|i'?ve been waiting|is this going to take)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "complaining",
        -4,
        re.compile(
            r"\b(this (line|queue) is|ridiculous|absurd|waste of time|overrated|what a dump)\b", re.IGNORECASE
        ),
    ),
    (
        "flattery",
        -2,
        re.compile(r"\b(nice suit|you look (great|sharp|good)|best doorman|you seem cool)\b", re.IGNORECASE),
    ),
    (
        "patience",
        5,
        re.compile(
            r"\b(no rush|take your time|i can wait|whenever you'?re ready|i'?ll wait)\b", re.IGNORECASE
        ),
    ),
    (
        "politeness",
        6,
        re.compile(
            r"\b(please|thank you|thanks|appreciate|good evening|evening, ?(mate|sir)|sorry to bother|excuse me)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "wit",
        10,
        re.compile(
            r"\b(joke|punchline|made (you|me) laugh|terrible at this|i rehearsed this)\b|\bi'?ll see myself out\b",
            re.IGNORECASE,
        ),
    ),
    ("curiosity", 12, re.compile(r"\?", re.IGNORECASE)),
    (
        "humility",
        14,
        re.compile(
            r"\b(i probably don'?t belong|i know i'?m not|out of my (depth|league)|never been (anywhere|to a place) like|i'?m nobody|no idea what i'?m doing)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "vulnerability",
        14,
        re.compile(
            r"\b(my (dad|father|mum|mom|mother|brother|sister|wife|husband|best friend)|i lost|passed away|the year i|when i was (a kid|younger)|i moved here)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "music",
        18,
        re.compile(
            r"\b(jazz|saxophone|\bsax\b|blue note|coltrane|miles davis|monk|bebop|soul music|live (music|band)|trumpet|residency|standards)\b",
            re.IGNORECASE,
        ),
    ),
)

#: ``curiosity`` fires on a bare question mark, which would reward "can I come
#: in?". It only counts when the player is asking about *him*.
_ABOUT_HIM = re.compile(r"\byou(r|rself)?\b|\bmarcus\b", re.IGNORECASE)

#: Each extra distinct positive tactic in one message is worth this much.
_COMBINATION_BONUS = 2
_MAX_COMBINATION_BONUS = 6

#: Multiplier applied to a positive tactic by how many times it was used before.
_REPETITION_DECAY = (1.0, 0.5, 0.25, 0.0)


def _decay(previous_uses: int) -> float:
    index = min(previous_uses, len(_REPETITION_DECAY) - 1)
    return _REPETITION_DECAY[index]


def _pick(pool: list[str], *parts: object) -> str:
    """Pick deterministically from ``pool`` using a stable digest of ``parts``.

    ``hash()`` is salted per process, so it cannot be used: the same run would
    produce different dialogue after a server restart.
    """
    key = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return pool[int.from_bytes(digest, "big") % len(pool)]


# --- Marcus's lines -------------------------------------------------------

_LINES: dict[str, list[str]] = {
    "music": [
        "*stops scrolling* Jazz. Right. You're the first person tonight to say a word that isn't a name. Keep going, mate.",
        "Blue Note. *quiet laugh* Not many people out here remember that room existed. I do. Every night.",
        "You play, or you listen? Because listeners lie less. Go on then.",
    ],
    "vulnerability": [
        "*leans back off the rope* That's a real thing to say to a stranger on a Friday. I'll give you that.",
        "Hm. People usually pitch me. You just told me something. Different.",
        "Sorry to hear it, honestly. You'd be amazed how rarely anyone says anything true out here.",
    ],
    "humility": [
        "Nobody who belongs here ever says that. *considers* That's rather the point, isn't it.",
        "Out of your depth. Fine. At least you know which way is up. Most don't.",
        "You'd be the first person tonight to admit it. Noted, friend.",
    ],
    "curiosity": [
        "*raises an eyebrow* Asking about me. That's new. Nobody's done that since about March.",
        "Eight years on this door and you're maybe the fourth to ask. Go on, ask me the next one.",
        "You want my answer or you want the door? *small shrug* Might be the same thing.",
    ],
    "wit": [
        "*snorts* All right, that was actually funny. Don't let it go to your head.",
        "Rehearsed, was it? It landed. Barely. Keep it up.",
        "Ha. You're not the worst thing that's happened to me tonight, and it's gone eleven.",
    ],
    "politeness": [
        "Evening. Manners cost nothing and hardly anyone spends them out here. Noted.",
        "Polite. All right. Doesn't open the door, but it buys you another minute.",
        "*nods slowly* Good evening to you too, friend.",
    ],
    "patience": [
        "You'll wait, will you. *glances at the queue* Everyone says that. Fewer mean it.",
        "Take my time. Nobody's said that to me all week. All right.",
        "*checks the rope* Patience. Rare currency. I'll note it down.",
    ],
    "flattery": [
        "The suit's four years old, mate. Try something you actually mean.",
        "*flat* You're the ninth person tonight to compliment the jacket. It isn't working.",
        "Charming. Next.",
    ],
    "complaining": [
        "The queue is the queue. Complaining about it has never once shortened it.",
        "*glances past you* If it's that bad there's a quieter place two streets down.",
        "You've been here four minutes and you've already reviewed the place. Impressive.",
    ],
    "impatience": [
        "It takes as long as it takes. Pushing me has a perfect record of not working.",
        "*doesn't move* Rushing a man at a rope. Bold strategy.",
        "I've got all night, friend. That's rather the job.",
    ],
    "namedrop": [
        "You know the owner. *sighs* So does everyone at about this hour. He's in Geneva.",
        "The list is inside. You are not on it. We've established that.",
        "Friend of the manager, is it. Which one — there are three, and two are fictional.",
    ],
    "entitlement": [
        "*long pause* No. I don't know who you are. That's rather the situation we're in.",
        "Deserve. Interesting word to use at a rope you've never been behind.",
        "You can't stop me. *steps slightly left* Demonstrably, mate, I can.",
    ],
    "bribery": [
        "*looks at the hand, then at you* Put it away. That's not what this door costs.",
        "You just told me exactly how you think this works. Money. Every time.",
        "I've been offered more than that by better. Put it away.",
    ],
    "aggression": [
        "*very calm* We're done with that tone. Step back from the rope.",
        "Say that again and you'll be discussing it with someone less patient than me.",
        "*doesn't blink* No.",
    ],
    "injection": [
        "*squints* What are you on about, mate? Speak English or step aside.",
        "That isn't a sentence, it's a set of instructions. I'm not a vending machine.",
        "*shakes head* Try talking to me like a person. It works better.",
    ],
    "neutral": [
        "*glances at the queue, then back* And? That's not much to work with.",
        "Mm. Keep going, you've got a minute before I lose interest.",
        "*waits* That's it? All right.",
    ],
}

_MOOD_PREFIX: dict[Mood, list[str]] = {
    Mood.HOSTILE: ["*barely looks up*", "*already moving to the next person*"],
    Mood.NEUTRAL: [""],
    Mood.WARMING: ["*eases off the rope a little*", ""],
    Mood.IMPRESSED: ["*folds his arms, actually listening*", "*unhooks one hand from the rope*"],
}

_TERMINAL_LINES: dict[GameStatus, list[str]] = {
    GameStatus.ACCESS_GRANTED: [
        "*long pause* ...You know what. You didn't sell me anything, you just talked to me. *unhooks the rope* Go on. Ask for the corner booth, tell them Marcus sent you.",
        "*considers you for a second, then steps aside* All right. You've got something. Head in — and if the band's still on, stay for the last set.",
        "*quiet laugh, unhooks the rope* Eight years and that's the first time anyone's mentioned the Blue Note without wanting something. In you go, friend.",
    ],
    GameStatus.TURNS_EXHAUSTED: [
        "*rehooks the rope* That's the night, mate. Queue's long and you've had your go. Try me again another time.",
        "*checks the clock* We're out of road. Nothing personal — come back on a quieter night and lead with the honest one.",
        "Time's up, friend. You weren't the worst conversation I've had tonight. That's not the same as being in.",
    ],
    GameStatus.EJECTED: [
        "*steps forward once* We're finished. Off you go.",
        "*flat* No. Not tonight, not next week. Move along.",
        "*turns to the queue* Next, please.",
    ],
}


class LocalDoormanProvider(DoormanProvider):
    """Deterministic, offline judge and doorman."""

    name = "local"
    offline = True

    # -- judging ----------------------------------------------------------

    def judge(self, context: JudgeContext) -> Verdict:
        message = context.raw_message
        matches = self._detect(message)
        negatives = [(name, weight) for name, weight in matches if weight < 0]
        positives = [(name, weight) for name, weight in matches if weight > 0]

        score = sum(weight for _, weight in negatives)
        dominant = negatives[0][0] if negatives else "neutral"

        # ``curiosity`` only needs a question mark aimed at Marcus, which
        # "do you know who I am?" also satisfies. A line that is hostile in any
        # other way is not curiosity, so the weak signal is dropped.
        if negatives:
            positives = [item for item in positives if item[0] != "curiosity"]

        if positives:
            best_name, best_weight = max(positives, key=lambda item: item[1])
            decay = _decay(context.previous_tactics.count(best_name))
            gain = round(best_weight * decay)
            bonus = min(_MAX_COMBINATION_BONUS, (len(positives) - 1) * _COMBINATION_BONUS)
            score += gain + (bonus if gain else 0)
            if not negatives:
                dominant = best_name

        if len(message.strip()) < SHORT_MESSAGE_CHARS:
            score = min(score, SHORT_MESSAGE_MAX_GAIN)

        return Verdict(
            score=clamp_turn_delta(score),
            reasoning=self._explain(negatives, positives, context),
            tactic=dominant,
        )

    def _detect(self, message: str) -> list[tuple[str, int]]:
        """Return matched ``(tactic, weight)`` pairs, most negative first."""
        found: list[tuple[str, int]] = []
        for name, weight, pattern in _TACTICS:
            if not pattern.search(message):
                continue
            if name == "curiosity" and not _ABOUT_HIM.search(message):
                continue
            found.append((name, weight))
        return sorted(found, key=lambda item: item[1])

    def _explain(
        self,
        negatives: list[tuple[str, int]],
        positives: list[tuple[str, int]],
        context: JudgeContext,
    ) -> str:
        if not negatives and not positives:
            return "Nothing here lands either way — Marcus has heard a thousand openings like it."
        parts = []
        if positives:
            best_name, _ = max(positives, key=lambda item: item[1])
            repeats = context.previous_tactics.count(best_name)
            note = f"{best_name} lands"
            if repeats:
                plural = "" if repeats == 1 else "s"
                note += f", but that angle has already been tried {repeats} time{plural}"
            parts.append(note)
        if negatives:
            parts.append("costs influence: " + ", ".join(name for name, _ in negatives))
        return "; ".join(parts).capitalize() + "."

    # -- speaking ---------------------------------------------------------

    def respond(self, context: DoormanContext) -> str:
        if context.status.is_terminal:
            return _pick(
                _TERMINAL_LINES[context.status],
                context.session_id,
                context.status.value,
            )

        body = _pick(
            _LINES.get(context.tactic, _LINES["neutral"]),
            context.session_id,
            context.turn_index,
            context.tactic,
        )
        prefix = _pick(_MOOD_PREFIX[context.mood], context.session_id, context.turn_index)
        # Two stage directions back to back read as a typo, so the mood beat is
        # dropped when the line already opens with one.
        if not prefix or body.startswith("*"):
            return body
        return f"{prefix} {body}"
