from config.sources.technology import TECH_FEEDS
from modules.news_category import show_news


def get_technology_news():

    show_news(
        "Technology",
        TECH_FEEDS,
    )
