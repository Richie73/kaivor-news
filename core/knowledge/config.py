"""
Kaivor Knowledge Configuration
"""


class KnowledgeConfig:
    """Configuration for the knowledge system."""

    # Folder containing indexed documents
    DIRECTORY = "knowledge"

    # Maximum number of search results
    SEARCH_LIMIT = 10

    # Maximum passages supplied to AI
    RETRIEVAL_LIMIT = 5

    # Passage ranking
    PASSAGE_WINDOW = 500
    PASSAGE_STEP = 250

    # Query rewriting
    MIN_KEYWORD_LENGTH = 3
