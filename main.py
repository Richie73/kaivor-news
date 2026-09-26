import os
import threading
import time
import urllib.request
import json
import requests
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

CATEGORY_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://www.aljazeera.com/xml/rss/all.rss",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/en/top-stories/s-9097/rss",
        "https://www.theguardian.com/world/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.npr.org/1004/rss.xml",
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"
    ],
    "Politics": [
        "https://www.foreignaffairs.com/rss.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://rss.politico.com/politics-news.xml",
        "https://www.theguardian.com/politics/rss",
        "https://thehill.com/policy/internal/feed/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.npr.org/1014/rss.xml"
    ],
    "Science": [
        "https://www.newscientist.com/feed/home/",
        "https://www.sciencedaily.com/rss/top.xml",
        "https://www.nature.com/nature.rss",
        "https://rss.sciencedirect.com/publication/science/00368075",
        "https://feeds.feedburner.com/sciencedaily/most_recent",
        "https://feeds.npr.org/1007/rss.xml"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.theguardian.com/uk-news/rss",
        "https://www.telegraph.co.uk/news/rss.xml",
        "https://www.independent.co.uk/news/uk/rss",
        "https://news.sky.com/rss/uk-10993"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.theguardian.com/sport/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "https://www.skysports.com/rss/12040"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://rss.cnn.com/rss/edition_business.rss",
        "https://www.theguardian.com/business/rss",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
    ],
    "Tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml"
    ]
}

def get_live_market_data():
    data = {
        "weather": "13.6°C",
        "gold": "$4,125.00",
        "bitcoin": "$92,500",
        "ethereum": "$3,420.00",
        "oil": "$74.20"
    }
    try:
        req = urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=51.5085&current=temperature_2m", timeout=2)
        w_data = json.loads(req.read().decode('utf-8'))
        if 'current' in w_data:
            data["weather"] = f"{w_data['current']['temperature_2m']}°C"
    except Exception as e:
        print("Weather fetch error:", e)
    return data

def parse_single_feed(url, category, used_photos):
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KaivorNews/1.3"}
        response = requests.get(url, headers=headers, timeout=5, verify=True)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:5]:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                published = entry.get('published', 'Recent')
                summary = entry.get('summary', entry.get('description', ''))
                
                clean_summary = re.sub('<[^<]+?>', '', summary)
                if len(clean_summary) > 200:
                    clean_summary = clean_summary[:200] + "..."
                
                articles.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'summary': clean_summary,
                    'category': category
                })
    except Exception as e:
        print(f"Handled feed error for {url}: {e}")
    return articles


FEED_CACHE = {}

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    market_data = get_live_market_data()

    if category in FEED_CACHE and not custom_feed:
        articles = FEED_CACHE[category]
    else:
        articles = []
        used_photos = set()
        feed_urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
            
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(parse_single_feed, url, category, used_photos): url for url in feed_urls}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    articles.extend(res)
        
        if not custom_feed:
            FEED_CACHE[category] = articles

    return render_template("index.html", market=market_data, category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key=guardian_key)

@app.route("/api/articles")
def api_articles():
    category = request.args.get("category", "World")
    if category in FEED_CACHE:
        articles = FEED_CACHE[category]
    else:
        articles = []
        used_photos = set()
        feed_urls = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
        for url in feed_urls:
            res = parse_single_feed(url, category, used_photos)
            if res:
                articles.extend(res)
        FEED_CACHE[category] = articles
    return jsonify({"category": category, "articles": articles})
