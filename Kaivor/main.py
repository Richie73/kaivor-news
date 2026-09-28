import os
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

CATEGORY_FEEDS = {
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Politics": "https://rss.politico.com/politics-news.xml",
    "Science": "https://www.sciencedaily.com/rss/top.xml",
    "UK": "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Tech": "https://techcrunch.com/feed/"
}

def fetch_rss_native(url, category):
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            channel = root.find('channel')
            if channel is not None:
                for item in channel.findall('item')[:8]:
                    articles.append({
                        'title': item.find('title').text if item.find('title') is not None else 'No Title',
                        'link': item.find('link').text if item.find('link') is not None else '#',
                        'published': item.find('pubDate').text if item.find('pubDate') is not None else 'Recent',
                        'summary': item.find('description').text[:180] + "..." if item.find('description') is not None and item.find('description').text else '',
                        'category': category
                    })
    except Exception as e:
        print(f"RSS Error: {e}")
    return articles

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        feed_name = request.form.get("name")
        feed_url = request.form.get("url")
        if feed_name and feed_url:
            if not Feed.query.filter_by(url=feed_url).first():
                db.session.add(Feed(name=feed_name, url=feed_url))
                db.session.commit()
        return redirect(url_for("index"))

    category = request.args.get("category", "World")
    custom_feed_url = request.args.get("custom_url")
    
    if custom_feed_url:
        articles = fetch_rss_native(custom_feed_url, "Custom Feed")
        current_cat = "Custom Feed"
    else:
        feed_url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        articles = fetch_rss_native(feed_url, category)
        current_cat = category

    custom_feeds = Feed.query.all()
    saved_articles = Saved.query.all()

    return render_template("index.html", 
                           market={"weather": "13.6°C", "gold": "$4,125.00", "bitcoin": "$92,500"}, 
                           category=current_cat, 
                           categories=CATEGORY_FEEDS.keys(), 
                           articles=articles, 
                           custom_feeds=custom_feeds, 
                           saved_articles=saved_articles)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
