"""
Kaivor AI Daily Brief

Reads the latest articles from the local database,
sends them to the AI summariser and displays
a formatted executive briefing.
"""

import json

from ai.summariser import Summariser
from core.display import banner


def get_ai_daily_brief():
    """Generate and display the AI Daily Brief."""

    try:
        with open("database/articles.json", "r", encoding="utf-8") as f:
            articles = json.load(f)

    except Exception as e:
        print(f"\nError loading article database:\n{e}")
        return

    if not articles:
        print("\nDatabase is empty.")
        return

    text = ""

    for article in articles[:10]:

        title = article.get("title", "")
        summary = article.get("summary", "")

        text += f"Title: {title}\n"

        if summary:
            text += f"Summary: {summary}\n"

        text += "\n"

    print()
    print("Loading latest articles...")
    print("Preparing executive briefing...")
    print("Contacting AI provider...")
    print("Generating intelligence report...\n")

    summariser = Summariser()

    response = summariser.daily_brief(text)

    if response.success:

        banner("KAIVOR EXECUTIVE INTELLIGENCE BRIEF")

        print(response.content)

        print()
        print(f"Model      : {response.model}")
        print(f"Provider   : {response.provider}")
        print(f"Time Taken : {response.elapsed} seconds")

        banner("END OF BRIEF")

    else:

        banner("AI ERROR")

        print(response.error)
