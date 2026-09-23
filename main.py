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
        "https://moxie.foxnews.com/feedburner/world.rss",
        "https://www.aljazeera.com/xml/rss/all.rss",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/en/top-stories/s-9097/rss",
        "https://www.foreignaffairs.com/rss.xml"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.independent.co.uk/news/uk/rss",
        "https://www.standard.co.uk/rss"
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
        "https://www.newscientist.com/feed/home/"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://feeds.feedburner.com/reuters/businessNews"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.skysports.com/rss/12110",
        "https://www.espn.com/espn/rss/football/news",
        "https://theathletic.com/rss/"
    ],
    "Music": [
        "https://pitchfork.com/feed/feed-news/rss",
        "https://www.rollingstone.com/music/music-news/feed/",
        "https://NME.com/feed",
        "https://www.loudersound.com/rss"
    ],
    "Android": [
        "https://9to5google.com/feed/",
        "https://www.androidcentral.com/rss.xml",
        "https://www.androidpolice.com/feed/"
    ],
    "Puzzles": []
}

FEED_CACHE = {}
CACHE_TTL = 300

def fetch_guardian_articles(api_key, section="world"):
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
                articles.append({
                    "title": item.get("webTitle", "No Title"),
                    "link": item.get("webUrl", "#"),
                    "published": item.get("webPublicationDate", "Recent")[:10],
                    "summary": fields.get("trailText", "Comprehensive long-form investigative analysis and reporting..."),
                    "image": fields.get("thumbnail", "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300&auto=format&fit=crop&q=80"),
                    "read_time": "12 min read"
                })
    except Exception as e:
        print(f"Guardian API Error: {e}")
    return articles

def get_contextual_placeholder(category, title=""):
    lower_title = title.lower()
    if "music" in category.lower() or any(k in lower_title for k in ["band", "album", "rock", "metal", "tour", "song"]):
        return "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&auto=format&fit=crop&q=80"
    elif "sport" in category.lower() or any(k in lower_title for k in ["football", "match", "goal", "league", "team", "club"]):
        return "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300&auto=format&fit=crop&q=80"
    elif "tech" in category.lower() or "android" in category.lower() or any(k in lower_title for k in ["AI", "tech", "phone", "app", "software", "google"]):
        return "https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&auto=format&fit=crop&q=80"
    elif "business" in category.lower() or any(k in lower_title for k in ["market", "economy", "stocks", "inflation", "bank"]):
        return "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&auto=format&fit=crop&q=80"
    else:
        return "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=300&auto=format&fit=crop&q=80"

def extract_image(entry, category):
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
            
    return get_contextual_placeholder(category, entry.get("title", ""))

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

def parse_single_feed(url, category):
    now = time.time()
    cache_key = f"{category}_{url}"
    if cache_key in FEED_CACHE:
        cached_data, timestamp = FEED_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached_data

    feed_articles = []
    try:
        parsed_feed = feedparser.parse(url)
        for entry in parsed_feed.entries[:10]:
            summary_text = entry.get("summary", "")
            clean_summary = BeautifulSoup(summary_text, "html.parser").get_text()
            title = entry.get("title", "No Title")
            image_url = extract_image(entry, category)
            read_time = calculate_read_time(clean_summary)
            
            feed_articles.append({
                "title": title,
                "link": entry.get("link", "#"),
                "published": entry.get("published", "Recent")[:16],
                "summary": clean_summary[:140] + "...",
                "image": image_url,
                "read_time": read_time
            })
        FEED_CACHE[cache_key] = (feed_articles, now)
    except Exception as e:
        print(f"Feed Error ({url}): {e}")
    return feed_articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    
    articles = []
    
    if category == "Puzzles":
        articles = [
            {"title": "The Independent - Daily Crosswords & Puzzles", "link": "https://www.independent.co.uk/life-style/puzzles", "published": "Daily Puzzles", "summary": "Play daily crosswords, word searches, and brain teasers from The Independent.", "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=300&auto=format&fit=crop&q=80", "read_time": "15 min play"},
            {"title": "The Guardian - Daily Crosswords & Quiptic", "link": "https://www.theguardian.com/crosswords", "published": "Daily Puzzles", "summary": "Explore famous Guardian crosswords including Quick, Cryptic, and Quiptic puzzles.", "image": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=300&auto=format&fit=crop&q=80", "read_time": "12 min play"},
            {"title": "The New York Times - The Mini Crossword", "link": "https://www.nytimes.com/crosswords/game/mini", "published": "Daily Puzzle", "summary": "A snappy, miniature crossword puzzle designed to be solved in minutes.", "image": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&auto=format&fit=crop&q=80", "read_time": "5 min play"},
            {"title": "Wordle - Daily Word Guessing Game", "link": "https://www.nytimes.com/games/wordle/index.html", "published": "Daily Puzzle", "summary": "Guess the hidden 5-letter word in 6 tries with color-coded clues.", "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=300&auto=format&fit=crop&q=80", "read_time": "5 min play"},
            {"title": "Connections - Group Words by Common Thread", "link": "https://www.nytimes.com/games/connections", "published": "Daily Puzzle", "summary": "Find groups of four items that share something in common without making mistakes.", "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=300&auto=format&fit=crop&q=80", "read_time": "6 min play"},
            {"title": "Daily Sudoku - Number Placement Challenge", "link": "https://sudoku.com/", "published": "Daily Puzzle", "summary": "Fill the 9x9 grid so that each column, row, and section contains digits 1-9.", "image": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=80", "read_time": "10 min play"}
        ]
    else:
        if guardian_key:
            if category == "World":
                articles.extend(fetch_guardian_articles(guardian_key, section="world"))
            elif category == "UK":
                articles.extend(fetch_guardian_articles(guardian_key, section="uk"))
            elif category == "Sport":
                articles.extend(fetch_guardian_articles(guardian_key, section="sport"))

        feed_urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
            
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(parse_single_feed, url, category): url for url in feed_urls}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    articles.extend(res)

    return render_template("index.html", category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key=guardian_key)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    summary = data.get("summary", "")
    api_key = data.get("apiKey", "")

    if not api_key:
        return jsonify({"brief": "Please enter your DeepSeek API key in the Feed & API Key Manager panel above."})

    try:
        # Use DeepSeek's native API endpoint and model
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a professional geopolitical and financial news analyst. Provide a sharp, concise 2-sentence executive brief analyzing the core structural impact of this news story."},
                {"role": "user", "content": f"Article Title: {title}\nSummary: {summary}"}
            ]
        }
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            result = response.json()
            brief_text = result["choices"][0]["message"]["content"]
            return jsonify({"brief": brief_text})
        else:
            print(f"DeepSeek Error Response: {response.text}")
            return jsonify({"brief": f"API Error ({response.status_code}): Please check your DeepSeek API key or balance."})
    except Exception as e:
        return jsonify({"brief": f"Failed to generate brief: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
