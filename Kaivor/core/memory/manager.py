"""
Kaivor Memory Manager
"""

from core.memory.database import get_connection, initialise_database
from core.memory.models import Memory


class MemoryManager:
    """Manage persistent memories."""

    def __init__(self):
        initialise_database()

    def add_memory(self, category, title, content):
        conn = get_connection()

        conn.execute(
            """
            INSERT INTO memories
            (category, title, content)
            VALUES (?, ?, ?)
            """,
            (category, title, content),
        )

        conn.commit()
        conn.close()

    def _rows_to_memories(self, rows):
        return [
            Memory(
                id=row[0],
                category=row[1],
                title=row[2],
                content=row[3],
                created_at=row[4],
            )
            for row in rows
        ]

    def get_memories(self):
        conn = get_connection()

        rows = conn.execute(
            """
            SELECT id, category, title, content, created_at
            FROM memories
            ORDER BY created_at DESC
            """
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)

    def get_memories_by_category(self, category):
        conn = get_connection()

        rows = conn.execute(
            """
            SELECT id, category, title, content, created_at
            FROM memories
            WHERE category = ?
            ORDER BY created_at DESC
            """,
            (category,),
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)

    def search_memories(self, keyword):
        conn = get_connection()

        rows = conn.execute(
            """
            SELECT id, category, title, content, created_at
            FROM memories
            WHERE title LIKE ?
               OR content LIKE ?
            ORDER BY created_at DESC
            """,
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()

        conn.close()

        return self._rows_to_memories(rows)
