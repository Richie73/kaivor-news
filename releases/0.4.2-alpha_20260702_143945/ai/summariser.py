"""
Kaivor AI Summariser
"""

from ai.brain import Brain
from ai.prompts import PromptLibrary


class Summariser:

    def __init__(self):

        self.brain = Brain()

    def daily_brief(self, articles):

        prompt = PromptLibrary.daily_brief(articles)

        return self.brain.run(
            task="daily_brief",
            prompt=prompt,
        )

    def article(self, article):

        prompt = PromptLibrary.article_summary(article)

        return self.brain.run(
            task="article_summary",
            prompt=prompt,
        )