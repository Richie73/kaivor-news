import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request

app = Flask(__name__, template_folder='templates', static_folder='static')

CATEGORY_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Politics": "https://rss.politico.com/politics-news.xml",
    "Science": "https://www.sciencedaily.com/rss/top.xml",
    "UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Tech": "https://techcrunch.com/feed/"
}

def fetch_rss(url, category):
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item')[:6]:
                    title = item.find('title')
                    link = item.find('link')
                    pubDate = item.find('pubDate')
                    description = item.find('description')
                    
                    articles.append({
                        'title': title.text if title is not None else 'No Title',
                        'link': link.text if link is not None else '#',
                        'published': pubDate.text if pubDate is not None else 'Recent',
                        'summary': description.text[:180] + "..." if description is not None and description.text else '',
                        'category': category
                    })
    except Exception as e:
        print(f"Feed parse error: {e}")
    return articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    
    market_data = {
        "weather": "13.6°C",
        "gold": "$4,125.00",
        "bitcoin": "$92,500",
        "ethereum": "$3,420.00",
        "oil": "$74.20"
    }
    
    feed_url = custom_feed if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
    articles = fetch_rss(feed_url, category)

    return render_template(
        "index.html", 
        market=market_data, 
        category=category, 
        categories=CATEGORY_FEEDS.keys(), 
        articles=articles, 
        custom_feed=custom_feed, 
        guardian_key=guardian_key
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
