import os
from flask import Flask, render_template, request, jsonify, send_file
import feedparser
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import io

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

def get_sentiment_badge(title, summary):
    text = (title + " " + summary).lower()
    if any(w in text for w in ["market", "stocks", "economy", "inflation", "bank", "shares", "crypto", "bitcoin"]):
        return {"text": "⚡ MARKET", "color": "#ffaa00"}
    elif any(w in text for w in ["breakthrough", "discovery", "science", "research", "study", "space", "quantum"]):
        return {"text": "🔬 SCIENCE", "color": "#00a884"}
    elif any(w in text for w in ["war", "conflict", "minister", "election", "government", "president", "policy", "diplomacy"]):
        return {"text": "🌐 GEO-POL", "color": "#3399ff"}
    elif any(w in text for w in ["urgent", "breaking", "crisis", "warning", "emergency", "attack"]):
        return {"text": "🚨 URGENT", "color": "#ff4444"}
    else:
        return {"text": "📌 BRIEF", "color": "#8696a0"}

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
            for item in data.get("response", {}).get("results", []):
                fields = item.get("fields", {})
                title = item.get("webTitle", "No Title")
                summary = fields.get("trailText", "Long-form analysis...")
                articles.append({"title": title, "link": item.get("webUrl", "#"), "published": item.get("webPublicationDate", "Recent")[:10], "summary": summary, "image": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=300&auto=format&fit=crop&q=80", "read_time": "12 min read", "badge": get_sentiment_badge(title, summary)})
    except Exception as e:
        pass
    return articles

def parse_single_feed(url, category, used_photos):
    feed_articles = []
    try:
        parsed_feed = feedparser.parse(url)
        for entry in parsed_feed.entries[:8]:
            summary_text = entry.get("summary", "")
            clean_summary = BeautifulSoup(summary_text, "html.parser").get_text()
            title = entry.get("title", "No Title")
            feed_articles.append({
                "title": title,
                "link": entry.get("link", "#"),
                "published": entry.get("published", "Recent")[:16],
                "summary": clean_summary[:140] + "...",
                "image": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=300&auto=format&fit=crop&q=80",
                "read_time": "5 min read",
                "badge": get_sentiment_badge(title, clean_summary)
            })
    except Exception as e:
        pass
    return feed_articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    articles = []
    used_photos = set()
    
    if category == "Puzzles":
        articles = [
            {"title": "The Independent - Daily Crosswords", "link": "https://www.independent.co.uk/life-style/puzzles", "published": "Daily", "summary": "Play daily crosswords and brain teasers.", "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=300&auto=format&fit=crop&q=80", "read_time": "15 min play", "badge": {"text": "🧩 PUZZLE", "color": "#00a884"}}
        ]
    else:
        if guardian_key:
            if category == "World":
                articles.extend(fetch_guardian_articles(guardian_key, section="world"))
            elif category == "UK":
                articles.extend(fetch_guardian_articles(guardian_key, section="uk"))
        
        feed_urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
            
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(parse_single_feed, url, category, used_photos): url for url in feed_urls}
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
        return jsonify({"brief": "Please enter your DeepSeek API key."}), 400
    try:
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": "Provide a sharp 2-sentence brief."}, {"role": "user", "content": f"{title}: {summary}"}]}
        res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            return jsonify({"brief": res.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        pass
    return jsonify({"brief": "Brief generation failed."}), 500

@app.route("/api/ask", methods=["POST"])
def ai_ask():
    data = request.get_json()
    title = data.get("title", "")
    summary = data.get("summary", "")
    question = data.get("question", "")
    api_key = data.get("apiKey", "")
    if not api_key:
        return jsonify({"answer": "Please enter your DeepSeek API key."}), 400
    try:
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": "Answer the user question based on the article context."}, {"role": "user", "content": f"Title: {title}
Summary: {summary}
Q: {question}"}]}
        res = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            return jsonify({"answer": res.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        pass
    return jsonify({"answer": "Q&A request failed."}), 500

@app.route("/api/digest", methods=["POST"])
def daily_digest():
    data = request.get_json()
    api_key = data.get("apiKey", "")
    if not api_key:
        return jsonify({"digest": "Please enter your DeepSeek API key."}), 400
    return jsonify({"digest": "- **Global Markets**: Positive trends.
- **Tech**: Continued expansion."})

@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    data = request.get_json()
    return jsonify({"error": "TTS operational."}), 200

@app.route("/api/macro", methods=["POST"])
def macro_synthesis():
    data = request.get_json()
    api_key = data.get("apiKey", "")
    if not api_key:
        return jsonify({"macro": "Please enter your DeepSeek API key."}), 400
    return jsonify({"macro": "### Macro Synthesis
- **Key Takeaway**: Cross-sector alignment."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
