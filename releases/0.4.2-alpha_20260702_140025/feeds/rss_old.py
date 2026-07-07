import feedparser


class RSSReader:
    def __init__(self):
        self.timeout = 10

    def fetch(self, url):
        try:
            feed = feedparser.parse(url)

            articles = []

            for item in feed.entries[:10]:
                articles.append({
                    "title": item.get("title", "No title"),
                    "link": item.get("link", ""),
                    "published": item.get("published", "Unknown"),
                })

            return articles

        except Exception as e:
            print(f"RSS Error: {e}")
            return []