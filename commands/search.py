"""
Kaivor Knowledge Search Command
"""

import sys

from core.knowledge.store import KnowledgeStore


def run():
    """Search the knowledge directory."""

    if len(sys.argv) < 3:
        print("Usage:")
        print("python kaivor.py search <query>")
        return

    query = " ".join(sys.argv[2:])

    store = KnowledgeStore()

    store.load_directory("knowledge")

    results = store.search(query)

    if not results:
        print(f'No documents found for "{query}".')
        return

    print(f"\nFound {len(results)} document(s):\n")

    
for document in results:
    print(f"• {document.title}")
    print(f"  Path: {document.path}")
    print()
