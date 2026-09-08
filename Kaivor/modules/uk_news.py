from config.sources.uk import UK_FEEDS
from modules.news_category import show_news


def get_uk_news():

    show_news(
        "UK News",
        UK_FEEDS,
    )
