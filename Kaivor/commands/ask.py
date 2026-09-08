"""
Kaivor Ask Command
"""

from core.ai.engine import AIEngine
from core.ai.tasks import AITasks


def run(question):
    """Ask Kaivor a question."""

    engine = AIEngine()

    print()
    print("=" * 60)
    print("KAIVOR")
    print("=" * 60)
    print()

    answer = engine.ask(
        task=AITasks.CHAT,
        prompt=question,
    )

    print(answer)

    sources = getattr(engine, "last_sources", [])

    if sources:

        print()
        print("-" * 60)
        print("Sources")
        print("-" * 60)

        shown = set()

        for source in sources:

            path = source["path"]

            if path in shown:
                continue

            shown.add(path)

            print(f"• {source['title']}")
            print(f"  {path}")
