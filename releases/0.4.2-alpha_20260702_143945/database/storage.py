import json
import os


class Storage:

    def __init__(self):

        self.filename = "database/articles.json"

        if not os.path.exists(self.filename):

            with open(self.filename, "w") as f:
                json.dump([], f)

    def load(self):

        with open(self.filename, "r") as f:
            return json.load(f)

    def save(self, articles):

        with open(self.filename, "w") as f:
            json.dump(articles, f, indent=4)

    def add_articles(self, new_articles):

        articles = self.load()

        existing = {
            article["link"]
            for article in articles
        }

        for article in new_articles:

            if article.link not in existing:

                articles.append(
                    {
                        "source": article.source,
                        "title": article.title,
                        "published": article.published,
                        "link": article.link,
                    }
                )

        self.save(articles)
