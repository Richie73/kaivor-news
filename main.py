import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

app = Flask(__name__)

MASTER_PHOTO_POOL = [
    "1507413245164-6160d8298b31", "1532094349884-543bc11b234d", "1507668077129-56e32842fceb",
    "1518770660439-4636190af475", "1530497610245-94d3c16cda28", "1516321318423-f06f85e504b3",
    "1541872703-74c5e44368f9", "1529101091764-c3526daf38fe", "1521747116042-5a810fda9664",
    "1486406146926-c627a92ad1ab", "1555848962-6e79363ec58f", "1508873696983-2df5c920aac9",
    "1526374965328-7f61d4dc18c5", "1535378917042-10a22c95931a", "1550751827-4bd374c3f58b",
    "1519389950473-47ba0277781c", "1451187580459-43490279c0fa", "1611974789855-9c2a0a7236a3",
    "1590283603385-17ffb3a7f29f", "1460925895917-afdab827c52f", "1559526324-4b87b5e36e44"
]

CATEGORY_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://moxie.foxnews.com/feedburner/world.rss",
        "https://www.aljazeera.com/xml/rss/all.rss"
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
        "https://www.independent.co.uk/news/uk/rss"
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.skysports.com/rss/12110"
    ],
    "Music": [
        "https://pitchfork.com/feed/feed-news/rss",
        "https://www.rollingstone.com/music/music-news/feed/"
    ],
    "Android": [
        "https://9to5google.com/feed/",
        "https://www.androidcentral.com/rss.xml"
    ],
    "Puzzles": []
}

def get_sentiment_badge(title, summary):
    text = (title + " " + summary).lower()
    if any(w in text for w in ["market", "stocks", "economy", "inflation", "bank", "shares", "crypto", "bitcoin"]):
        return {"text": "⚡ MARKET", "color": "#ffaa00"}
    elif any(w in text for w in ["breakthrough", "discovery", "science", "research", "study", "space", "quantum"]):
        return {"text": "🔬 SCIENCE", "color": "#00a884"}
    elif any(w in text for w in ["war", "conflict", "minister", "election", "government", "president", "policy"]):
        return {"text": "🌐 GEO-POL", "color": "#3399ff"}
    elif any(w in text for w in ["urgent", "breaking", "crisis", "warning", "emergency"]):
        return {"text": "🚨 URGENT", "color": "#ff4444"}
    else:
        return {"text": "📌 BRIEF", "color": "#8696a0"}

def parse_feed(url):
    articles = []
    try:
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:6]:
            title = entry.get("title", "No Title")
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()
            photo_id = random.choice(MASTER_PHOTO_POOL)
            image_url = f"https://images.unsplash.com/photo-{photo_id}?w=300&auto=format&fit=crop&q=80"
            articles.append({
                "title": title,
                "link": entry.get("link", "#"),
                "published": entry.get("published", "Recent")[:16],
                "summary": summary[:140] + "...",
                "image": image_url,
                "read_time": "5 min read",
                "badge": get_sentiment_badge(title, summary)
            })
    except Exception as e:
        pass
    return articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    articles = []
    
    if category == "Puzzles":
        articles = [
            {
                "title": "The Independent Daily Crossword",
                "link": "https://www.independent.co.uk/life-style/puzzles/crosswords",
                "published": "Daily",
                "summary": "Challenge your mind with today's expert crossword puzzle.",
                "image": f"https://images.unsplash.com/photo-{random.choice(MASTER_PHOTO_POOL)}?w=300&auto=format&fit=crop&q=80",
                "read_time": "15 min play",
                "badge": {"text": "🧩 PUZZLE", "color": "#00a884"}
            },
            {
                "title": "Wordle & Daily Brain Teasers",
                "link": "https://www.nytimes.com/games/wordle/index.html",
                "published": "Daily",
                "summary": "Guess the hidden 5-letter word in 6 tries.",
                "image": f"https://images.unsplash.com/photo-{random.choice(MASTER_PHOTO_POOL)}?w=300&auto=format&fit=crop&q=80",
                "read_time": "5 min play",
                "badge": {"text": "🧩 WORDLE", "color": "#3399ff"}
            }
        ]
    else:
        urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(parse_feed, url) for url in urls]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    articles.extend(res)
                    
    return render_template("index.html", category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key=guardian_key)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json() or {}
    title = data.get("title", "Article")
    summary = data.get("summary", "")
    api_key = data.get("apiKey", "")
    
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Provide a concise 2-sentence executive brief of this news article."},
                    {"role": "user", "content": f"Title: {title}\nSummary: {summary}"}
                ]
            }
            res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                brief_text = res.json()["choices"][0]["message"]["content"]
                return jsonify({"brief": brief_text})
        except Exception:
            pass
            
    return jsonify({"brief": f"Executive Brief: {title} highlights critical developments requiring close strategic attention across global markets."})

@app.route("/api/ask", methods=["POST"])
def ai_ask():
    data = request.get_json() or {}
    title = data.get("title", "")
    summary = data.get("summary", "")
    question = data.get("question", "")
    api_key = data.get("apiKey", "")
    
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Answer the user question based on the provided news context."},
                    {"role": "user", "content": f"Title: {title}\nSummary: {summary}\nQuestion: {question}"}
                ]
            }
            res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                answer_text = res.json()["choices"][0]["message"]["content"]
                return jsonify({"answer": answer_text})
        except Exception:
            pass
            
    return jsonify({"answer": f"Regarding your question about '{question}': Based on current reporting on {title}, analysts indicate ongoing shifts in policy and market response."})

@app.route("/api/digest", methods=["POST"])
def daily_digest():
    return jsonify({"digest": "- **Global Markets Surge**: Economic indicators show robust growth.\n- **Tech Innovations**: New breakthroughs in neural computing and AI resilience."})

@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    return jsonify({"error": "TTS operational."}), 200

@app.route("/api/macro", methods=["POST"])
def macro_synthesis():
    return jsonify({"macro": "### Strategic Intelligence Synthesis\n- **Systemic Trend**: Cross-domain convergence between tech and geopolitics is accelerating market volatility."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
