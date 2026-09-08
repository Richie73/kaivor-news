from config.sources.music import MUSIC_FEEDS
from modules.news_category import show_news


def get_music_news():

    show_news(
        "Music",
        MUSIC_FEEDS,
    )
