"""
Kaivor Memory API
"""

from core.memory.manager import MemoryManager

_manager = MemoryManager()


def remember(category, title, content):
    """Store a new memory."""
    _manager.add_memory(category, title, content)


def recall():
    """Return all memories."""
    return _manager.get_memories()


def search(keyword):
    """Search memories."""
    return _manager.search_memories(keyword)


def category(name):
    """Return memories from a category."""
    return _manager.get_memories_by_category(name)
