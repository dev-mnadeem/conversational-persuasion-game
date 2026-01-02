"""Game rules, prompts, injection screening and turn resolution.

Only the rulebook is re-exported here. ``engine`` imports the provider port,
which imports the rulebook, so eagerly importing the engine from this module
would close an import cycle — import ``app.game.engine`` directly instead.
"""

from .rules import INFLUENCE_THRESHOLD, MAX_TURNS, GameStatus, Mood

__all__ = ["INFLUENCE_THRESHOLD", "MAX_TURNS", "GameStatus", "Mood"]
