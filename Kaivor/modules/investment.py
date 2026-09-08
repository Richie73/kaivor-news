from config.sources.investment import INVESTMENT_FEEDS
from modules.news_category import show_news


def get_investment_news():

    show_news(
        "Investment Research",
        INVESTMENT_FEEDS,
    )
