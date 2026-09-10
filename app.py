from flask import Flask, render_template, request, redirect, url_for
import feedparser
import re

app = Flask(__name__)

sources = [
    # World
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "category": "World"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "category": "World"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best", "category": "World"},
    # Tech
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "category": "Tech"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Tech"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "Tech"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "Tech"},
    # AI
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "AI"},
    # Sport
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "category": "Sport"},
    {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "category": "Sport"},
    # Music
    {"name": "Pitchfork", "url": "https://pitchfork.com/feed/feed-news/rss", "category": "Music"},
    {"name": "Billboard", "url": "https://www.billboard.com/feed/", "category": "Music"},
    # Android
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/", "category": "Android"},
    {"name": "9to5Google", "url": "https://9to5google.com/feed/", "category": "Android"},
    # Business
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "category": "Business"},
    {"name": "Financial Times", "url": "https://www.ft.com/?format=rss", "category": "Business"}
]

def extract_image(entry):
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media:
                return media['url']
    if 'media_thumbnail' in entry:
        if 'url' in entry.media_thumbnail[0]:
            return entry.media_thumbnail[0]['url']
            
    summary = entry.get("summary", "") or entry.get("description", "")
    match = re.search(r'src="([^"]+)"', summary)
    if match:
        return match.group(1)
        
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=300&q=80"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        preset_url = request.form.get('preset_url')
        feed_category = request.form.get('feed_category', 'Tech')
        
        if preset_url:
            feed_name = "Preset Feed"
            for s in sources:
                if s['url'] == preset_url:
                    feed_name = s['name']
            
            if not any(s['url'] == preset_url for s in sources):
                sources.append({"name": feed_name, "url": preset_url, "category": feed_category})
                
        return redirect(url_for('index'))

    market_data = {
        "S&P 500": 5850.00,
        "NASDAQ": 18300.00,
        "FTSE 100": 8250.00,
        "Bitcoin": 92500.00,
        "Gold": 2700.50
    }

    news_by_category = {}
    for source in sources:
        try:
            parsed = feedparser.parse(source['url'])
            articles = []
            for entry in parsed.entries[:3]:
                articles.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", "#"),
                    "image": extract_image(entry)
                })
            
            cat = source['category']
            if cat not in news_by_category:
                news_by_category[cat] = {}
            news_by_category[cat][source['name']] = articles
        except Exception as e:
            print(f"Feed error: {e}")

    # Comprehensive collection of newspaper crosswords and popular puzzles
    news_by_category["Puzzles"] = {
        "Newspaper Crosswords & Daily Games": [
            {
                "title": "Wordle - Daily Word Puzzle (New York Times)",
                "link": "https://www.nytimes.com/games/wordle/index.html",
                "image": "https://images.unsplash.com/photo-1529699211952-734e80c4d42b?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "The Mini Crossword - New York Times",
                "link": "https://www.nytimes.com/crosswords/game/mini",
                "image": "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Connections - New York Times Word Grouping",
                "link": "https://www.nytimes.com/games/connections",
                "image": "https://images.unsplash.com/photo-1612817288484-6f916006741a?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Spelling Bee - New York Times Letter Puzzle",
                "link": "https://www.nytimes.com/puzzles/spelling-bee",
                "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "The Guardian Crosswords Hub (Quick & Cryptic)",
                "link": "https://www.theguardian.com/crosswords",
                "image": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Los Angeles Times Daily Crossword",
                "link": "https://www.latimes.com/games/crossword",
                "image": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "USA Today Crossword & Puzzles",
                "link": "https://puzzles.usatoday.com/",
                "image": "https://images.unsplash.com/photo-1584697964190-7953c424a733?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Washington Post Puzzles & Games Hub",
                "link": "https://www.washingtonpost.com/games/",
                "image": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=300&q=80"
            },
            {
                "title": "Classic Sudoku Daily Grids",
                "link": "https://nine.websudoku.com/",
                "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=300&q=80"
            }
        ]
    }

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
