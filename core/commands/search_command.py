"""
Kaivor Search Command
"""

from core.commands.base_command import BaseCommand


class SearchCommand(BaseCommand):
    """Handles knowledge and workspace search."""

    name = "search"
    aliases = []
    help_text = "Search the current workspace."

    def __init__(self, search, workspace):
        self.search = search
        self.workspace = workspace

    def execute(self, text=None):

        parts = text.split(maxsplit=1)

        if len(parts) < 2:

            print()
            print("Usage: search <text>")
            print()

            return

        query = parts[1]

        results = self.search.search(
            self.workspace.current(),
            query,
        )

        if not results:

            print()
            print("No results found.")
            print()

            return

        print()
        print(f"Found {len(results)} result(s)")
        print("-" * 60)

        for result in results:

            print(f"[{result['type']}] {result['name']}")
            print(result["path"])

        print()
