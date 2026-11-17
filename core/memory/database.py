"""
Kaivor Memory Database
"""

import sqlite3
from pathlib import Path

# FP112: absolute path — the repo-root data/ dir, the same place
# news_store.py keeps its JSON files. The old relative path depended
# on the process working directory, which is not guaranteed.
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "kaivor_memory.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialise_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            importance INTEGER NOT NULL DEFAULT 3,
            source TEXT NOT NULL DEFAULT 'manual',
            tags TEXT NOT NULL DEFAULT ''
        )
    """)

    # FP112: the pre-FP112 table had only the first five columns.
    # Add the new ones to an existing database instead of failing.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    for column, definition in (
        ("importance", "INTEGER NOT NULL DEFAULT 3"),
        ("source", "TEXT NOT NULL DEFAULT 'manual'"),
        ("tags", "TEXT NOT NULL DEFAULT ''"),
    ):
        if column not in existing:
            conn.execute(f"ALTER TABLE memories ADD COLUMN {column} {definition}")

    conn.commit()
    conn.close()
