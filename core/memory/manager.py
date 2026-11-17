"""
Kaivor Memory Manager
"""

from core.memory.database import get_connection, initialise_database
from core.memory.models import Memory

# FP112: every read selects the full eight columns, in the order
# Memory.from_row expects.
_COLUMNS = "id, category, title, content, created_at, importance, source, tags"


class MemoryManager:
    """Manage persistent memories."""

    def __init__(self):
        initialise_database()

    def add_memory(self, category, title, content, importance=3, source="manual", tags=""):
        conn = get_connection()

        cursor = conn.execute(
            """
            INSERT INTO memories
            (category, title, content, importance, source, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (category, title, content, importance, source, tags),
        )
        memory_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return memory_id

    def delete_memory(self, memory_id):
        """Delete one memory. Returns True when a row was removed."""
        conn = get_connection()
        cursor = conn.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def _rows_to_memories(self, rows):
        return [Memory.from_row(row) for row in rows]

    def get_memories(self):
        conn = get_connection()

        rows = conn.execute(
            f"""
            SELECT {_COLUMNS}
            FROM memories
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)

    def get_memories_by_category(self, category):
        conn = get_connection()

        rows = conn.execute(
            f"""
            SELECT {_COLUMNS}
            FROM memories
            WHERE category = ?
            ORDER BY created_at DESC, id DESC
            """,
            (category,),
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)

    def search_memories(self, keyword):
        conn = get_connection()

        rows = conn.execute(
            f"""
            SELECT {_COLUMNS}
            FROM memories
            WHERE title LIKE ?
               OR content LIKE ?
            ORDER BY created_at DESC, id DESC
            """,
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)
