from feeds.feed_manager import FeedManager
from core.news_engine import NewsEngine
from database.storage import Storage


def show_news(title, feeds):

    manager = FeedManager()
    engine = NewsEngine()
    storage = Storage()

    articles = manager.fetch_multiple(feeds)

    added = storage.add_articles(articles)

    print(f"\n💾 Added {added} new article(s) to the Kaivor database.\n")

    engine.display(title, articles)
