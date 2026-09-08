"""
Kaivor Provider Recommendation
"""

from core.ai.router import AIRouter
from core.ai.tasks import AITasks


def run():

    router = AIRouter()

    print("\n========== AI RECOMMENDATIONS ==========\n")

    tasks = (
        AITasks.CHAT,
        AITasks.CODING,
        AITasks.RESEARCH,
        AITasks.WRITING,
        AITasks.RAMS,
        AITasks.EMAIL,
        AITasks.NEWS,
        AITasks.VISION,
    )

    for task in tasks:

        try:
            provider = router.select(task)

            print(
                f"{task:<12} -> {provider.name}"
            )

        except Exception:

            print(
                f"{task:<12} -> No Provider"
            )

    print()
