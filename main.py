import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup

app = Flask(__name__)

FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Tech": "https://www.theverge.com/rss/index.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/news/sport/rss.xml",
    "Music": "https://pitchfork.com/feed/feed-news/rss",
    "Android": "https://9to5google.com/feed/"
}

def extract_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if 'url' in media:
                return media['url']
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'href' in enc:
                return enc['href']
    summary = entry.get("summary", "")
    soup = BeautifulSoup(summary, "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return None

def calculate_read_time(text):
    words = len(text.split())
    minutes = max(1, round(words / 150))
    return f"{minutes} min read"

@app.route("/")
def index():
    category = request.args.get("category", "World")
    feed_url = FEEDS.get(category, FEEDS["World"])
    
    articles = []
    try:
        parsed_feed = feedparser.parse(feed_url)
        for entry in parsed_feed.entries[:10]:
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

    return render_template("index.html", category=category, categories=FEEDS.keys(), articles=articles)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    return jsonify({"brief": f"AI Brief: '{title}' provides critical insights into ongoing developments, analyzing macroeconomic and sector-wide impacts."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
