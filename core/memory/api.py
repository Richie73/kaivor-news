"""
Kaivor Memory API
"""

from core.memory.manager import MemoryManager

# FP112: the manager is built on first use, not at import time, so
# importing this module never creates the database as a side effect.
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager


def remember(category, title, content, importance=3, source="manual", tags=""):
    """Store a new memory. Returns its id."""
    return _get_manager().add_memory(category, title, content, importance, source, tags)


def forget(memory_id):
    """Delete a memory. Returns True when one was removed."""
    return _get_manager().delete_memory(memory_id)


def recall():
    """Return all memories."""
    return _get_manager().get_memories()


def search(keyword):
    """Search memories."""
    return _get_manager().search_memories(keyword)


def category(name):
    """Return memories from a category."""
    return _get_manager().get_memories_by_category(name)
