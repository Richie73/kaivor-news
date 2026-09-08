"""
Kaivor Test Suite
"""

import sys
from pathlib import Path

# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.ai.engine import AIEngine
from core.ai.tasks import AITasks
from core.providers.manager import ProviderManager
from core.ai.resource_manager import AIResourceManager
from core.memory.manager import MemoryManager


def test_provider_manager():
    manager = ProviderManager()

    assert manager.primary() is not None
    assert len(manager.list()) > 0

    print("✓ Provider Manager")


def test_resource_manager():
    manager = AIResourceManager()

    assert manager.get_mode() is not None

    print("✓ Resource Manager")


def test_memory():
    memory = MemoryManager()

    assert memory.get_memories() is not None

    print("✓ Memory")


def test_ai_engine():
    engine = AIEngine()

    reply = engine.ask(
        AITasks.CHAT,
        "Reply with exactly: PASS"
    )

    assert "PASS" in reply.upper()

    print("✓ AI Engine")


def main():
    print("\n==============================")
    print(" KAIVOR TEST SUITE")
    print("==============================\n")

    test_provider_manager()
    test_resource_manager()
    test_memory()
    test_ai_engine()

    print("\n==============================")
    print(" ALL TESTS PASSED")
    print("==============================\n")


if __name__ == "__main__":
    main()
