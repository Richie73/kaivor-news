from config.sources.ai import AI_FEEDS
from modules.news_category import show_news


def get_ai_news():

    show_news(
        "AI Intelligence",
        AI_FEEDS,
    )
