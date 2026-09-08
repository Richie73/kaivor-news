import feedparser
from core.article import Article


class RSSReader:

    def fetch(self, source_name, url):

        feed = feedparser.parse(url)

        articles = []

        for item in feed.entries[:10]:

            articles.append(
                Article(
                    source=source_name,
                    title=item.get("title", "No title"),
                    link=item.get("link", ""),
                    published=item.get("published", "Unknown"),
                )
            )

        return articles
