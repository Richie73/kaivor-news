"""
Kaivor Knowledge Retriever
"""

from pathlib import Path

from core.knowledge.query_rewriter import QueryRewriter
from core.knowledge.search_service import SearchService
from core.debug import Debug

class KnowledgeRetriever:
    """Retrieves relevant knowledge for AI."""

    IGNORED_FOLDERS = {
        "test",
        "tests",
        "demo",
        "examples",
        "__pycache__",
    }

    def __init__(self):
        self.search = SearchService()

    def ignored(self, path):
        """Return True if the document should be ignored."""

        parts = {
            part.lower()
            for part in Path(path).parts
        }

        return bool(parts & self.IGNORED_FOLDERS)

    def retrieve(
        self,
        query,
        directory="knowledge",
        limit=5,
    ):
        """Return relevant document excerpts."""

        candidates = QueryRewriter.rewrite(query)

        if isinstance(candidates, str):
            candidates = [candidates]

        if Debug.enabled:
            print()
            print("=" * 60)
            print("=" * 60)
            print(f"Original Question : {query}")
            print(f"Candidate Queries : {candidates}")
            print()

        merged = {}

        for candidate in candidates:

            results = self.search.search(
                query=candidate,
                directory=directory,
                limit=limit,
            )

            if Debug.enabled:
                print(f'"{candidate}" -> {len(results)} result(s)')

            for result in results:

                document = result["document"]

                if self.ignored(document.path):
                    continue

                key = document.path

                if key not in merged:

                    merged[key] = {
                        "document": document,
                        "excerpt": result["excerpt"],
                        "score": 0,
                    }

                merged[key]["score"] += 1

        ranked = sorted(
            merged.values(),
            key=lambda item: item["score"],
            reverse=True,
        )

        passages = []

        if Debug.enabled:
            print()
            print("Ranking")
            print("-" * 60)

        for item in ranked[:limit]:

            document = item["document"]

            if Debug.enabled:
                print(
                    f'{item["score"]:>2} ★  {document.title}'
                )

            passages.append(
                {
                    "title": document.title,
                    "path": document.path,
                    "excerpt": item["excerpt"],
                    "score": item["score"],
                }
            )

        if Debug.enabled:
            print()
            print(f"Passages built: {len(passages)}")
            print("=" * 60)
            print()

        return passages
