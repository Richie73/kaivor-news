import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

# Expanded multiple RSS sources per category for richer feeds
CATEGORY_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://moxie.foxnews.com/feedburner/world.rss"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.independent.co.uk/news/uk/rss"
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/news/sport/rss.xml",
        "https://www.espn.com/espn/rss/news"
    ],
    "Music": [
        "https://pitchfork.com/feed/feed-news/rss",
        "https://www.rollingstone.com/music/music-news/feed/"
    ],
    "Android": [
        "https://9to5google.com/feed/",
        "https://www.androidcentral.com/rss.xml"
    ]
}

def fetch_guardian_articles(api_key, section="world"):
    """Fetches articles from The Guardian API and maps them to World or UK sections."""
    articles = []
    if not api_key or api_key.strip() == "":
        return articles
    
    url = f"https://content.guardianapis.com/search?section={section}&show-fields=thumbnail,trailText,byline&api-key={api_key.strip()}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            results = data.get("response", {}).get("results", [])
            for item in results:
                fields = item.get("fields", {})
                articles.append({
                    "title": item.get("webTitle", "No Title"),
                    "link": item.get("webUrl", "#"),
                    "published": item.get("webPublicationDate", "Recent")[:10],
                    "summary": fields.get("trailText", "Read full coverage on The Guardian..."),
                    "image": fields.get("thumbnail", None),
                    "read_time": "3 min read"
                })
    except Exception as e:
        print(f"Guardian API Error: {e}")
    return articles

def fetch_og_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                return og_img['content']
    except Exception:
        pass
    return None

def extract_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if 'url' in media and media['url'].startswith('http'):
                return media['url']
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            if 'url' in thumb and thumb['url'].startswith('http'):
                return thumb['url']
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'href' in enc and enc['href'].startswith('http'):
                return enc['href']
    content = entry.get("summary", "")
    if hasattr(entry, 'content') and entry.content:
        content += entry.content[0].get('value', '')
    soup = BeautifulSoup(content, "html.parser")
    img = soup.find("img")
    if img and img.get("src") and img["src"].startswith('http'):
        return img["src"]
    link = entry.get("link")
    if link:
        og = fetch_og_image(link)
        if og:
            return og
    return None

def calculate_read_time(text):
    words = len(text.split())
    minutes = max(1, round(words / 150))
    return f"{minutes} min read"

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    
    articles = []
    
    # 1. Pull Guardian API articles if key is present and category matches World or UK
    if guardian_key:
        if category == "World":
            articles.extend(fetch_guardian_articles(guardian_key, section="world"))
        elif category == "UK":
            articles.extend(fetch_guardian_articles(guardian_key, section="uk"))

    # 2. Pull from multi-source RSS feeds for the category
    feed_urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
    if isinstance(feed_urls, str):
        feed_urls = [feed_urls]
        
    for url in feed_urls:
        try:
            parsed_feed = feedparser.parse(url)
            for entry in parsed_feed.entries[:6]: # Pull a balanced mix from each source
                summary_text = entry.get("summary", "")
                clean_summary = BeautifulSoup(summary_text, "html.parser").get_text()
                image_url = extract_image(entry)
                read_time = calculate_read_time(clean_summary)
                
                articles.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", "#"),
                    "published": entry.get("published", "Recent"),
                    "summary": clean_summary[:120] + "...",
                    "image": image_url,
                    "read_time": read_time
                })
        except Exception as e:
            print(f"Feed Error ({url}): {e}")

    return render_template("index.html", category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key=guardian_key)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    return jsonify({"brief": f"AI Brief: '{title}' provides critical industry insights, highlighting core catalysts and structural market impacts."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
