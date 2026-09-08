import os
import requests
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
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

def discover_rss(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        res = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code != 200:
            return url
        soup = BeautifulSoup(res.text, 'html.parser')
        rss_link = soup.find('link', type='application/rss+xml') or soup.find('link', type='application/atom+xml')
        if rss_link and rss_link.get('href'):
            href = rss_link['href']
            return urllib.parse.urljoin(url, href)
    except:
        pass
    return url

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_url = request.form.get('url')
        if input_url:
            actual_feed_url = discover_rss(input_url)
            parsed = feedparser.parse(actual_feed_url)
            feed_name = parsed.feed.title if hasattr(parsed, 'feed') and hasattr(parsed.feed, 'title') else input_url
            if not Feed.query.filter_by(url=actual_feed_url).first():
                new_feed = Feed(name=feed_name, url=actual_feed_url)
                db.session.add(new_feed)
                db.session.commit()
        return redirect(url_for('index'))

    try:
        feeds = Feed.query.all()
    except:
        feeds = []

    try:
        saved = Saved.query.order_by(Saved.id.desc()).all()
    except:
        saved = []

    news_grouped = {}
    
    try:
        market_parsed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^IXIC,AAPL,MSFT")
        items = []
        for e in market_parsed.entries[:6]:
            t = getattr(e, 'title', 'Market Update')
            if not isinstance(t, str):
                t = str(t)
            if not t.startswith("[$]"):
                t = f"[$] {t}"
            link = getattr(e, 'link', '#')
            items.append({'title': t, 'link': link, 'img': None})
        news_grouped['Markets'] = items
    except: 
        news_grouped['Markets'] = [{'title': '[$] Market data temporarily unavailable', 'link': '#', 'img': None}]

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed.url)
            articles = []
            for e in parsed.entries[:6]:
                title = getattr(e, 'title', 'Untitled')
                if not isinstance(title, str):
                    title = str(title)
                if not title.startswith("[$]"):
                    title = f"[$] {title}"
                link = getattr(e, 'link', '#')
                articles.append({'title': title, 'link': link, 'img': None})
            news_grouped[feed.name] = articles
        except: 
            continue
            
    return render_template('index.html', news_grouped=news_grouped, feeds=feeds, saved=saved)

@app.route('/delete/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    db.session.delete(feed)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Feed.query.count() == 0:
            default_feeds = [
                Feed(name="BBC World", url="http://feeds.bbci.co.uk/news/world/rss.xml"),
                Feed(name="TechCrunch", url="https://techcrunch.com/feed/"),
                Feed(name="Hacker News", url="https://news.ycombinator.com/rss"),
                Feed(name="Reuters", url="https://news.google.com/rss/search?q=Reuters"),
                Feed(name="The Verge", url="https://www.theverge.com/rss/index.xml")
            ]
            db.session.add_all(default_feeds)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)

