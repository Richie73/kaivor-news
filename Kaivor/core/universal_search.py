"""
Kaivor Universal Search
"""

from pathlib import Path

from core.knowledge.retrieval_service import RetrievalService


class UniversalSearch:
    """Unified search across Kaivor."""

    SEARCH_LOCATIONS = (
        "knowledge",
        "notes",
        "projects",
        "tasks",
        "documents",
        "agents",
        "chats",
    )

    TEXT_EXTENSIONS = {
        ".txt",
        ".md",
        ".json",
        ".csv",
        ".py",
    }

    def __init__(self):
        self.retrieval = RetrievalService()

    def workspace(self, workspace_path, query):

        query = query.lower()

        results = []

        workspace = Path(workspace_path)

        for location in self.SEARCH_LOCATIONS:

            root = workspace / location

            if not root.exists():
                continue

            for file in root.rglob("*"):

                if not file.is_file():
                    continue

                if file.suffix.lower() not in self.TEXT_EXTENSIONS:
                    continue

                try:
                    text = file.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                except Exception:
                    continue

                if query in text.lower():

                    results.append(
                        {
                            "type": location.title(),
                            "name": file.name,
                            "path": str(file),
                        }
                    )

        return results

    def knowledge(self, query):

        passages = self.retrieval.knowledge(
            query=query,
            limit=5,
        )

        results = []

        for item in passages:

            results.append(
                {
                    "type": "Knowledge",
                    "name": item["title"],
                    "path": item["path"],
                }
            )

        return results

    def search(self, workspace_path, query):

        results = []

        results.extend(
            self.workspace(
                workspace_path,
                query,
            )
        )

        results.extend(
            self.knowledge(query)
        )

        return results
