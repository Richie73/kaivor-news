from config.sources.football import FOOTBALL_FEEDS
from modules.news_category import show_news


def get_football_news():

    show_news(
        "Football",
        FOOTBALL_FEEDS,
    )
