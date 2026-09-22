import os
from flask import Flask, render_template, request, jsonify
import feedparser

app = Flask(__name__)

FEEDS = {
    "World": "https://www.aljazeera.com/xml/rss/all.rss",
    "Tech": "https://www.theverge.com/rss/index.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/news/sport/rss.xml",
    "Music": "https://pitchfork.com/feed/feed-news/rss",
    "Android": "https://9to5google.com/feed/"
}

@app.route("/")
def index():
    category = request.args.get("category", "World")
    feed_url = FEEDS.get(category, FEEDS["World"])
    
    articles = []
    try:
        parsed_feed = feedparser.parse(feed_url)
        for entry in parsed_feed.entries[:10]:
            articles.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "published": entry.get("published", "Recent"),
                "summary": entry.get("summary", "Click to read full story...")
            })
    except Exception as e:
        print(f"Error parsing feed: {e}")

    return render_template("index.html", category=category, categories=FEEDS.keys(), articles=articles)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    brief = f"AI Brief: '{title}' highlights key developing trends in the sector, emphasizing swift updates and deep impact analysis for global markets."
    return jsonify({"brief": brief})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
