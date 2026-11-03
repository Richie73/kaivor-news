"""Inspect the FP049 agent registry and delegated task queue."""

from core.agents.kaivor_ai import KaivorAIAgent
from core.agents.orchestrator import AgentOrchestrator
from core.agents.registry import AgentRegistry


def run() -> None:
    registry = AgentRegistry()
    registry.register(KaivorAIAgent())
    orchestrator = AgentOrchestrator(registry=registry)

    print("\n========== KAIVOR AGENTS ==========")
    for agent in registry.list():
        print(f"  {agent['agent_id']:<18} {agent['display_name']} ({agent['type']})")

    print("\nRecent delegated tasks")
    tasks = orchestrator.list(limit=10)
    if not tasks:
        print("  No tasks recorded yet.")
    else:
        for item in tasks:
            print(f"  {item['status']:<18} {item['task_id']}  [{item['assigned_to']}]")
    print()
