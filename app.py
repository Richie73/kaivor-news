import sqlite3
import feedparser
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)

# --- DATABASE SETUP ---
def get_db():
    db = sqlite3.connect('news.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS feeds (id INTEGER PRIMARY KEY, name TEXT, url TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS saved (id INTEGER PRIMARY KEY, title TEXT, link TEXT, source TEXT)')
        db.commit()

init_db()

@app.route('/')
def index():
    db = get_db()
    feeds = db.execute('SELECT * FROM feeds').fetchall()
    saved = db.execute('SELECT * FROM saved ORDER BY id DESC').fetchall()
    
    news_grouped = {}
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed['url'])
            news_grouped[feed['name']] = [{'title': e.title, 'link': e.link} for e in parsed.entries[:8]]
        except: continue
            
    return render_template('index.html', news_grouped=news_grouped, feeds=feeds, saved=saved)

@app.route('/add', methods=['POST'])
def add_feed():
    name, url = request.form.get('name'), request.form.get('url')
    if name and url:
        with get_db() as db:
            db.execute('INSERT INTO feeds (name, url) VALUES (?, ?)', (name, url))
    return redirect('/')

@app.route('/save', methods=['POST'])
def save_article():
    data = request.json
    with get_db() as db:
        db.execute('INSERT INTO saved (title, link, source) VALUES (?, ?, ?)', 
                   (data['title'], data['link'], data['source']))
    return jsonify({"status": "success"})

@app.route('/delete_feed/<int:id>')
def delete_feed(id):
    with get_db() as db:
        db.execute('DELETE FROM feeds WHERE id = ?', (id,))
    return redirect('/')

# PWA Support routes
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "short_name": "KaivorNews",
        "name": "Kaivor News Aggregator",
        "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/21/21601.png", "type": "image/png", "sizes": "512x512"}],
        "start_url": "/",
        "background_color": "#000000",
        "display": "standalone",
        "scope": "/",
        "theme_color": "#000000"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
