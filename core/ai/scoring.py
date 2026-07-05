"""
Kaivor AI Scoring Engine
"""

from core.ai.registry import get_models
from core.ai.settings import AIMode, get_mode


def score_models():
    """Return AI models sorted by score."""

    mode = get_mode()

    scored = []

    for name, model in get_models().items():

        score = 0

        # Quality
        score += model["quality"] * 10

        # Speed
        score += model["speed"] * 5

        # Context Window
        score += model["context"] // 50000

        # Cost Preference
        if mode == AIMode.FREE:

            if model["free"]:
                score += 1000
            else:
                score -= 1000

        elif mode == AIMode.ECONOMY:

            if model["free"]:
                score += 100

        elif mode == AIMode.BALANCED:

            if model["free"]:
                score += 25

        elif mode == AIMode.PREMIUM:

            if not model["free"]:
                score += 100

        scored.append((name, score))

    scored.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return scored
