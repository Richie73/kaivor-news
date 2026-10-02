import os
import traceback
import re
import requests
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kaivor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(300), unique=True, nullable=False)

class Saved(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(300), nullable=False)

with app.app_context():
    db.create_all()

# Expanded and diversified high-reliability news sources
CATEGORY_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Politics": "https://rss.politico.com/politics-news.xml",
    "Science": "https://www.sciencedaily.com/rss/top.xml",
    "UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Tech": "https://techcrunch.com/feed/",
    "AI": "https://www.technologyreview.com/feed/",
    "Puzzles": "" # Special interactive category
}

def fetch_rss_native(url, category):
    articles = []
    if not url:
        return articles
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            if channel is not None:
                for idx, item in enumerate(channel.findall('item')[:8]):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pub_date = item.find('pubDate')
                    desc = item.find('description')
                    
                    title = title_elem.text if title_elem is not None else 'No Title'
                    link = link_elem.text if link_elem is not None else '#'
                    published = pub_date.text if pub_date is not None else 'Recent'
                    desc_raw = desc.text if desc is not None and desc.text else ''
                    
                    summary_text = re.sub('<[^<]+?>', '', desc_raw)[:180] + "..." if desc_raw else ''
                    
                    # Professional Picsum seed-based image generation for guaranteed high polish & relevance
                    seed_slug = re.sub(r'[^a-zA-Z0-9]', '', title)[:15] or f"kaivor{idx}"
                    img_url = f"https://picsum.photos/seed/{seed_slug}/600/400"

                    articles.append({
                        'title': title,
                        'link': link,
                        'published': published,
                        'summary': summary_text,
                        'image': img_url,
                        'category': category
                    })
    except Exception as e:
        print(f"RSS Error: {e}")
    return articles

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":
            feed_name = request.form.get("name")
            feed_url = request.form.get("url")
            if feed_name and feed_url:
                if not Feed.query.filter_by(url=feed_url).first():
                    db.session.add(Feed(name=feed_name, url=feed_url))
                    db.session.commit()
            return redirect(url_for("index"))

        category = request.args.get("category", "World")
        custom_feed_url = request.args.get("custom_feed")

        news_grouped = {}
        for cat_name, cat_url in CATEGORY_FEEDS.items():
            if cat_url:
                news_grouped[cat_name] = fetch_rss_native(cat_url, cat_name)
            else:
                news_grouped[cat_name] = []

        if custom_feed_url:
            articles = fetch_rss_native(custom_feed_url, "Custom Feed")
            current_cat = "Custom Feed"
            news_grouped["Custom Feed"] = articles
        else:
            articles = news_grouped.get(category, news_grouped.get("World", []))
            current_cat = category

        custom_feeds_db = Feed.query.all()
        for f in custom_feeds_db:
            news_grouped[f.name] = fetch_rss_native(f.url, f.name)

        custom_feeds = custom_feeds_db
        saved_articles = Saved.query.all()

        return render_template("index.html",
                               market={"weather": "13.6°C", "gold": "$4,125.00", "bitcoin": "$92,500"},
                               category=current_cat,
                               categories=CATEGORY_FEEDS.keys(),
                               articles=articles,
                               news_grouped=news_grouped,
                               custom_feeds=custom_feeds,
                               saved_articles=saved_articles,
                               custom_feed=custom_feed_url or "")
    except Exception as e:
        return f"<pre style='color: red; font-size: 1rem; padding: 20px;'>{traceback.format_exc()}</pre>", 500

@app.route("/save", methods=["POST"])
def save_article():
    title = request.form.get("title")
    link = request.form.get("link")
    if title and link:
        if not Saved.query.filter_by(link=link).first():
            db.session.add(Saved(title=title, link=link))
            db.session.commit()
    return redirect(request.referrer or url_for("index"))

@app.route("/delete/<int:id>")
def delete_feed(id):
    feed = Feed.query.get(id)
    if feed:
        db.session.delete(feed)
        db.session.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
