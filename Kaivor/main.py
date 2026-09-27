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
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item')[:6]:
                    articles.append({
                        'title': item.find('title').text if item.find('title') is not None else 'No Title',
                        'link': item.find('link').text if item.find('link') is not None else '#',
                        'published': item.find('pubDate').text if item.find('pubDate') is not None else 'Recent',
                        'summary': item.find('description').text[:180] + "..." if item.find('description') is not None and item.find('description').text else '',
                        'category': category
                    })
    except Exception as e:
        print(f"Error: {e}")
    return articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    feed_url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
    articles = fetch_rss(feed_url, category)
    return render_template("index.html", market={"weather": "13.6°C", "gold": "$4,125.00", "bitcoin": "$92,500"}, category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed="", guardian_key="")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
