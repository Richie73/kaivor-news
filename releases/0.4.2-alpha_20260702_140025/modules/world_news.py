from config.sources.world import WORLD_FEEDS
from modules.news_category import show_news


def get_world_news():

    show_news(
        "World News",
        WORLD_FEEDS,
    )
