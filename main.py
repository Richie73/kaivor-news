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
        "https://www.dw.com/en/top-stories/s-9097/rss"
    ],
    "Politics": [
        "https://www.foreignaffairs.com/rss.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://rss.politico.com/politics-news.xml"
    ],
    "Science": [
        "https://www.newscientist.com/feed/home/",
        "https://www.sciencedaily.com/rss/top.xml",
        "https://www.nature.com/nature.rss"
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
        "https://www.wired.com/feed/rss"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://feeds.feedburner.com/reuters/businessNews"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.skysports.com/rss/12110",
        "https://www.espn.com/espn/rss/football/news"
    ],
    "Music": [
        "https://pitchfork.com/feed/feed-news/rss",
        "https://www.rollingstone.com/music/music-news/feed/",
        "https://NME.com/feed"
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
                title = item.get("webTitle", "No Title")
                img = fields.get("thumbnail") or f"https://images.unsplash.com/photo-{1500000 + (abs(hash(title)) % 500000)}?w=300&auto=format&fit=crop&q=80"
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

def extract_image(entry, title=""):
    # 1. Check RSS media/enclosures
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

    # 2. GUARANTEED FALLBACK: If publisher provides no image, generate a unique, high-res hash image instantly
    photo_id = 1500000 + (abs(hash(title)) % 700000)
    return f"https://images.unsplash.com/photo-{photo_id}?w=300&auto=format&fit=crop&q=80"

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
        for entry in parsed_feed.entries[:8]:
            summary_text = entry.get("summary", "")
            clean_summary = BeautifulSoup(summary_text, "html.parser").get_text()
            title = entry.get("title", "No Title")
            image_url = extract_image(entry, title)
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
            
        with ThreadPoolExecutor(max_workers=8) as executor:
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
        return jsonify({"brief": "Please enter your DeepSeek API key in the Manager panel above."})

    try:
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
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            brief_text = result["choices"][0]["message"]["content"]
            return jsonify({"brief": brief_text})
        else:
            return jsonify({"brief": f"API Error ({response.status_code}): Please check your DeepSeek balance or API key."})
    except Exception as e:
        return jsonify({"brief": f"Request Timeout / Failed: {str(e)}"})

@app.route("/api/digest", methods=["POST"])
def daily_digest():
    data = request.get_json()
    titles = data.get("titles", [])
    api_key = data.get("apiKey", "")

    if not api_key:
        return jsonify({"digest": "Please enter your DeepSeek API key in the Manager panel."})

    headlines_text = "\n".join([f"- {t}" for t in titles])

    try:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an elite chief intelligence briefing officer for global markets and geopolitics. Provide a rigorous, highly professional 5-bullet executive synthesis analyzing macro trends, cross-industry correlations, and strategic takeaways across these headlines. Format each bullet cleanly with a bold title and concise explanation."},
                {"role": "user", "content": f"Today's Top Headlines:\n{headlines_text}"}
            ]
        }
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            result = response.json()
            digest_text = result["choices"][0]["message"]["content"]
            return jsonify({"digest": digest_text})
        else:
            return jsonify({"digest": f"API Error: Check your DeepSeek credits."})
    except Exception as e:
        return jsonify({"digest": f"Failed: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
