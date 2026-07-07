from datetime import timezone
from email.utils import parsedate_to_datetime

from feeds.rss import RSSReader


class FeedManager:

    def __init__(self):
        self.reader = RSSReader()

    def fetch_multiple(self, feeds):

        articles = []

        for source, url in feeds:

            try:
                fetched = self.reader.fetch(source, url)
                articles.extend(fetched)

            except Exception:
                print(f"Warning: Could not load {source}")
                continue

        def article_date(article):

            try:
                dt = parsedate_to_datetime(article.published)

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt

            except Exception:
                return parsedate_to_datetime(
                    "Thu, 01 Jan 1970 00:00:00 GMT"
                )

        articles.sort(
            key=article_date,
            reverse=True
        )

        # Remove duplicate articles (same title)
        unique = []
        seen_titles = set()

        for article in articles:

            title = article.title.strip().lower()

            if title not in seen_titles:
                seen_titles.add(title)
                unique.append(article)

        return unique[:10]
