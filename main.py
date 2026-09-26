import threading

import urllib.request
import json

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

    try:
        req = urllib.request.urlopen("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=2)
        c_data = json.loads(req.read().decode('utf-8'))
        if 'bitcoin' in c_data and 'usd' in c_data['bitcoin']:
            data["bitcoin"] = f"${int(c_data['bitcoin']['usd']):,}"
        if 'ethereum' in c_data and 'usd' in c_data['ethereum']:
            data["ethereum"] = f"${int(c_data['ethereum']['usd']):,}"
    except Exception as e:
        print("Crypto fetch error (using fallback):", e)

    return data











import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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
        "https://www.physorg.com/rss-feed/",
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
        "https://feeds.feedburner.com/oreilly/radar/atom",
        "https://www.wired.com/feed/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml"
    ]
}

FEED_CACHE = {}

def prefetch_all_feeds():
    print("Pre-fetching all category feeds into memory for instant switching...")
    used_photos = set()
    with ThreadPoolExecutor(max_workers=12) as executor:
        for cat, urls in CATEGORY_FEEDS.items():
            for url in urls:
                executor.submit(parse_single_feed, url, cat, used_photos)
    print("All category feeds cached successfully!")

# Trigger prefetch on startup in a background thread
threading.Thread(target=prefetch_all_feeds, daemon=True).start()

CACHE_TTL = 900

MASTER_PHOTO_POOL = [
    "1507413245164-6160d8298b31", "1532094349884-543bc11b234d", "1507668077129-56e32842fceb",
    "1518770660439-4636190af475", "1530497610245-94d3c16cda28", "1516321318423-f06f85e504b3",
    "1541872703-74c5e44368f9", "1529101091764-c3526daf38fe", "1521747116042-5a810fda9664",
    "1486406146926-c627a92ad1ab", "1555848962-6e79363ec58f", "1508873696983-2df5c920aac9",
    "1526374965328-7f61d4dc18c5", "1535378917042-10a22c95931a", "1550751827-4bd374c3f58b",
    "1519389950473-47ba0277781c", "1451187580459-43490279c0fa", "1611974789855-9c2a0a7236a3",
    "1590283603385-17ffb3a7f29f", "1460925895917-afdab827c52f", "1559526324-4b87b5e36e44",
    "1526304640581-d334cdbbf45e", "1508098682722-e99c43a406b2", "1574629810360-7efbbe195018",
    "1518091043644-c1d4457512c6", "1461896836934-ffe607ba8211", "1517649763962-0c623066013b",
    "1543326727-cf6c39e8f84c", "1511671782779-c97d3d27a1d4", "1470225620780-dba8ba36b745",
    "1514525253161-7a46d19cd819", "1511192336575-5a79af67a629", "1585829365295-ab7cd400c167",
    "1446776811953-b23d57bd21aa", "1509228468518-180dd4864904", "1551288049-bebda4e38f71",
    "1504384308090-c894fdcc538d", "1454165804606-c3d57bc86b40", "1517245386807-bb43f82c33c4",
    "1516321497487-e288fb19713f", "1522071820081-009f0129c71c", "1551836022-d5d88e9218df",
    "1503676260728-1c00da094a0b", "1517841905240-472988babdf9", "1531482615713-2afd69097998"
]

def fetch_guardian_articles(api_key, section="world", used_photos=None):
    if used_photos is None:
        used_photos = set()
    articles = []
    if not api_key or api_key.strip() == "":
        return articles
    
    url = f"https://content.guardianapis.com/search?section={section}&page-size=15&show-fields=thumbnail,trailText,byline&api-key={api_key.strip()}"
    try:
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            data = response.json()
            results = data.get("response", {}).get("results", [])
            for item in results:
                fields = item.get("fields", {})
                title = item.get("webTitle", "No Title")
                
                available_pool = [p for p in MASTER_PHOTO_POOL if p not in used_photos]
                if not available_pool:
                    available_pool = MASTER_PHOTO_POOL
                
                chosen_photo = available_pool[abs(hash(title)) % len(available_pool)]
                used_photos.add(chosen_photo)
                
                img = fields.get("thumbnail") or f"https://images.unsplash.com/photo-{chosen_photo}?w=300&auto=format&fit=crop&q=80"
                articles.append({
                    "title": title,
                    "link": item.get("webUrl", "#"),
                    "published": item.get("webPublicationDate", "Recent")[:10],
                    "summary": fields.get("trailText", "Comprehensive long-form investigative analysis and reporting..."),
                    "image": img,
                    "read_time": "12 min read"
                })
    except Exception as e:
        print(f"Guardian API Error: {e}")
    return articles

def extract_image(entry, title="", used_photos=None):
    if used_photos is None:
        used_photos = set()

    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url')
            if url and url.startswith('http'):
                return url
                
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            url = thumb.get('url')
            if url and url.startswith('http'):
                return url

    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            url = enc.get('href')
            if url and url.startswith('http'):
                return url
    
    content = entry.get("summary", "")
    if hasattr(entry, 'content') and entry.content:
        for c in entry.content:
            content += c.get('value', '')
            
    soup = BeautifulSoup(content, "html.parser")
    img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src")
        if src and src.startswith('http'):
            return src

    available_pool = [p for p in MASTER_PHOTO_POOL if p not in used_photos]
    if not available_pool:
        available_pool = MASTER_PHOTO_POOL

    chosen_photo = available_pool[abs(hash(title)) % len(available_pool)]
    used_photos.add(chosen_photo)
    return f"https://images.unsplash.com/photo-{chosen_photo}?w=300&auto=format&fit=crop&q=80"

def calculate_read_time(text):
    words = len(text.split())
    if words < 30:
        return "4 min read"
    elif words < 70:
        return "7 min read"
    elif words < 120:
        return "11 min read"
    else:
        return "15 min read"


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
                
                # Clean HTML tags from summary
                import re
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
