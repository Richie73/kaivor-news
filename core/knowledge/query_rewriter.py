"""
Kaivor Query Rewriter
"""

import re


class QueryRewriter:
    """Converts natural language questions into search queries."""

    STOP_WORDS = {
        "what", "does", "do", "my", "the", "a", "an",
        "about", "say", "tell", "me", "is", "are",
        "in", "of", "to", "library", "knowledge",
        "documentation", "document", "documents",
        "please", "can", "could", "would", "show",
        "find",
    }

    SYNONYMS = {
        "qualification": [
            "qualification",
            "qualifications",
            "certificate",
            "certificates",
            "training",
            "smsts",
            "cscs",
            "ipaf",
            "npors",
            "first aid",
        ],
        "qualifications": [
            "qualification",
            "qualifications",
            "certificate",
            "training",
            "smsts",
            "cscs",
            "ipaf",
            "npors",
            "first aid",
        ],
    }

    @classmethod
    def rewrite(cls, question):
        """Return a list of candidate search queries."""

        words = re.findall(
            r"[A-Za-z0-9]+",
            question.lower(),
        )

        keywords = []

        for word in words:

            if word in cls.STOP_WORDS:
                continue

            keywords.append(word)

        queries = []

        if keywords:
            queries.append(" ".join(keywords))

        for keyword in keywords:

            if keyword not in queries:
                queries.append(keyword)

            if keyword in cls.SYNONYMS:

                for synonym in cls.SYNONYMS[keyword]:

                    if synonym not in queries:
                        queries.append(synonym)

        return queries
