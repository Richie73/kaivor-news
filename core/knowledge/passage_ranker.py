"""
Kaivor Passage Ranker
"""

import re


class PassageRanker:
    """Ranks passages inside a document."""

    WINDOW = 500
    STEP = 250

    @classmethod
    def best_passage(cls, text, query):

        keywords = [
            word.lower()
            for word in re.findall(r"\w+", query)
            if len(word) > 2
        ]

        if not keywords:
            return text[:cls.WINDOW]

        best_score = -1
        best_text = text[:cls.WINDOW]

        for start in range(0, len(text), cls.STEP):

            passage = text[start:start + cls.WINDOW]

            lower = passage.lower()

            score = 0

            for keyword in keywords:

                score += lower.count(keyword)

            if score > best_score:

                best_score = score
                best_text = passage

        return best_text.strip()
