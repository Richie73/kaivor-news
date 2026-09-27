import os
import urllib.request
import json
import requests
import feedparser
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

CATEGORY_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Politics": "https://rss.politico.com/politics-news.xml",
    "Science": "https://www.sciencedaily.com/rss/top.xml",
    "UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Tech": "https://techcrunch.com/feed/"
}

def get_live_market_data():
    return {
        "weather": "13.6°C",
        "gold": "$4,125.00",
        "bitcoin": "$92,500",
        "ethereum": "$3,420.00",
        "oil": "$74.20"
    }

@app.route("/")
def index():
    try:
        category = request.args.get("category", "World")
        custom_feed = request.args.get("custom_feed", "")
        guardian_key = request.args.get("guardian_key", "")
        market_data = get_live_market_data()
        
        articles = [
            {
                'title': 'Kaivor News Aggregator Live',
                'link': '#',
                'published': 'Just now',
                'summary': 'Your responsive news aggregator is successfully online and operational.',
                'category': category
            }
        ]

        return render_template(
            "index.html", 
            market=market_data, 
            category=category, 
            categories=CATEGORY_FEEDS.keys(), 
            articles=articles, 
            custom_feed=custom_feed, 
            guardian_key=guardian_key
        )
    except Exception as e:
        import traceback
        return f"<h3>Error:</h3><pre>{traceback.format_exc()}</pre>", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
