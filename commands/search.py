"""
Kaivor Search Command
"""

from textwrap import fill

from core.knowledge.search_service import SearchService


def run(query):
    """Search the knowledge base."""

    service = SearchService()

    results = service.search(query)

    print()
    print("=" * 60)
    print(f'Search Results: "{query}"')
    print("=" * 60)
    print()

    if not results:
        print("No matching documents found.")
        return

    print(f"Found {len(results)} document(s):\n")

    for result in results:

        document = result["document"]
        excerpt = result["excerpt"]

        print(f"📄 {document.title}")
        print(f"   {document.path}")
        print()

        if excerpt:
            print(fill(excerpt, width=72))
        else:
            print("(No preview available)")

        print()
        print("-" * 60)
        print()
