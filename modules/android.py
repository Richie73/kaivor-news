from config.sources.android import ANDROID_FEEDS
from modules.news_category import show_news


def get_android_news():

    show_news(
        "Android",
        ANDROID_FEEDS,
    )
