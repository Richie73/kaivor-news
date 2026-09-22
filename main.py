import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "Tech": "https://www.theverge.com/rss/index.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/news/sport/rss.xml",
    "Music": "https://pitchfork.com/feed/feed-news/rss",
    "Android": "https://9to5google.com/feed/"
}

def fetch_og_image(url):
    """Scrapes the article webpage for an Open Graph image meta tag as a fallback."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                return og_img['content']
            twitter_img = soup.find('meta', name='twitter:image')
            if twitter_img and twitter_img.get('content'):
                return twitter_img['content']
    except Exception:
        pass
    return None

def extract_image(entry):
    # 1. Check media_content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if 'url' in media and media['url'].startswith('http'):
                return media['url']
                
    # 2. Check media_thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            if 'url' in thumb and thumb['url'].startswith('http'):
                return thumb['url']

    # 3. Check enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'href' in enc and enc['href'].startswith('http'):
                return enc['href']

    # 4. Check inline images in summary or content
    content = entry.get("summary", "")
    if hasattr(entry, 'content') and entry.content:
        content += entry.content[0].get('value', '')
    soup = BeautifulSoup(content, "html.parser")
    img = soup.find("img")
    if img and img.get("src") and img["src"].startswith('http'):
        return img["src"]

    # 5. Fallback: Scrape article Open Graph image from destination URL
    link = entry.get("link")
    if link:
        og_image = fetch_og_image(link)
        if og_image:
            return og_image

    return None

def calculate_read_time(text):
    words = len(text.split())
    minutes = max(1, round(words / 150))
    return f"{minutes} min read"

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    
    feed_url = custom_feed if custom_feed else FEEDS.get(category, FEEDS["World"])
    
    articles = []
    try:
        parsed_feed = feedparser.parse(feed_url)
        for entry in parsed_feed.entries[:12]:
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
        print(f"Error: {e}")

    return render_template("index.html", category=category, categories=FEEDS.keys(), articles=articles, custom_feed=custom_feed)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    return jsonify({"brief": f"AI Brief: '{title}' provides critical insights into ongoing developments, analyzing macroeconomic and sector-wide impacts."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
