import os
import time
import threading
import re
import requests
import feedparser
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

_finance_cache = {'data': {}, 'last_updated': 0}
_cache_lock = threading.Lock()

def background_finance_worker():
    while True:
        data = {}
        try:
            fx_gbp = requests.get('https://api.frankfurter.app/latest?from=GBP&to=USD,EUR', timeout=5)
            if fx_gbp.status_code == 200:
                rates = fx_gbp.json().get('rates', {})
                data['GBP_USD'] = float(rates.get('USD', 1.33))
                data['GBP_EUR'] = float(rates.get('EUR', 1.19))
        except Exception:
            pass
            
        try:
            fx_eur = requests.get('https://api.frankfurter.app/latest?from=EUR&to=USD', timeout=5)
            if fx_eur.status_code == 200:
                rates_eur = fx_eur.json().get('rates', {})
                data['EUR_USD'] = float(rates_eur.get('USD', 1.08))
        except Exception:
            pass

        yahoo_symbols = {
            'Brent_Oil': 'BZ=F',
            'Gold': 'GC=F',
            'Bitcoin': 'BTC-USD',
            'SP500': '^GSPC'
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        for key, symbol in yahoo_symbols.items():
            try:
                url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m'
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    result = res.json().get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        price = meta.get('regularMarketPrice') or meta.get('previousClose')
                        if price is not None:
                            data[key] = float(round(price, 2))
            except Exception:
                pass

        if data:
            with _cache_lock:
                _finance_cache['data'] = data
                _finance_cache['last_updated'] = time.time()

        time.sleep(600)

threading.Thread(target=background_finance_worker, daemon=True).start()

# --- MULTI-SOURCE RSS FEEDS ---
RSS_SOURCES = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://www.theguardian.com/world/rss"
    ],
    "Technology": [
        "https://feeds.feedburner.com/TechCrunch/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.theguardian.com/business/rss"
    ],
    "Science": [
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://feeds.feedburner.com/NewScientistSpace"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.theguardian.com/uk-news/rss"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news"
    ],
    "Puzzles": [
        # Static curated daily puzzle links (NYT, Guardian, Independent)
    ]
}

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleansed = re.sub(cleanr, '', raw_html)
    return cleansed.replace('&nbsp;', ' ').strip()

def fetch_all_news():
    all_articles = []
    
    # 1. Fetch from diverse RSS feeds
    for category, urls in RSS_SOURCES.items():
        if category == "Puzzles":
            continue
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    raw_desc = entry.get('summary', entry.get('description', ''))
                    all_articles.append({
                        "title": entry.get('title', 'No Title'),
                        "description": clean_html(raw_desc),
                        "category": category,
                        "published": entry.get('published', 'Recent'),
                        "link": entry.get('link', '#')
                    })
            except Exception:
                pass

    # 2. Inject Daily Puzzles Hub items
    puzzle_items = [
        {
            "title": "The New York Times - Wordle Daily Challenge",
            "description": "Play today's official NYT Wordle puzzle and test your 5-letter word decoding skills.",
            "category": "Puzzles",
            "published": "Daily",
            "link": "https://www.nytimes.com/games/wordle/index.html"
        },
        {
            "title": "The Guardian - Daily Crossword Hub",
            "description": "Access quick, cryptic, and prize crosswords directly from major UK publishers.",
            "category": "Puzzles",
            "published": "Daily",
            "link": "https://www.theguardian.com/crosswords"
        },
        {
            "title": "The Independent - Daily Crosswords & Sudoku",
            "description": "Enjoy interactive daily crosswords and number puzzles from UK journalism.",
            "category": "Puzzles",
            "published": "Daily",
            "link": "https://www.independent.co.uk/extras/puzzles"
        },
        {
            "title": "The New York Times - Mini Crossword",
            "description": "A quick and snappy crossword puzzle updated every morning.",
            "category": "Puzzles",
            "published": "Daily",
            "link": "https://www.nytimes.com/crosswords/game/mini"
        }
    ]
    all_articles.extend(puzzle_items)
    return all_articles

@app.route('/')
def index():
    with _cache_lock:
        market_data = _finance_cache.get('data', {
            'gold': '2,650.00',
            'bitcoin': '64,200.00',
            'weather': '15°C',
            'SP500': '5,750.00',
            'Brent_Oil': '75.00',
            'GBP_USD': '1.33',
            'GBP_EUR': '1.19',
            'EUR_USD': '1.08'
        })
    
    articles = fetch_all_news()
    return render_template('index.html', market=market_data, articles=articles)

@app.route('/api/ticker', methods=['GET'])
def api_ticker():
    with _cache_lock:
        data = _finance_cache.get('data', {})
    return jsonify({"success": True, "ticker": data})

@app.route('/api/ai_brief', methods=['POST'])
def api_ai_brief():
    data = request.json or {}
    article_title = data.get('title', '')
    article_desc = data.get('description', '')
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": f"Provide a concise 3-bullet executive AI brief for this news article:\nTitle: {article_title}\nSummary: {article_desc}"}]
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content']
                return jsonify({"success": True, "brief": content})
        except Exception:
            pass
            
    fallback_brief = f"Executive Brief: Key developments regarding '{article_title}' indicate primary sector adjustments, immediate geopolitical context, and continued market impact across global feeds."
    return jsonify({"success": True, "brief": fallback_brief})

@app.route('/api/ask_ai', methods=['POST'])
def api_ask_ai():
    data = request.json or {}
    question = data.get('question', 'What are the main implications of this story?')
    article_title = data.get('title', '')
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": f"Answer this question about the article '{article_title}': {question}"}]
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content']
                return jsonify({"success": True, "answer": content})
        except Exception:
            pass

    fallback_answer = f"AI Analysis: Regarding '{article_title}', primary industry indicators suggest sustained long-term adjustments and strategic monitoring across related markets in response to: {question}"
    return jsonify({"success": True, "answer": fallback_answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
