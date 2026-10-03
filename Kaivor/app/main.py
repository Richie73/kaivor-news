import os
import time
import threading
import re
import requests
import feedparser
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# --- FINANCE CACHE & WORKER ---
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


# --- NEWS CACHE & BACKGROUND WORKER (Prevents Hanging) ---
_news_cache = {'articles': [], 'last_updated': 0}
_news_lock = threading.Lock()

RSS_SOURCES = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss"
    ],
    "Technology": [
        "https://feeds.feedburner.com/TechCrunch/",
        "https://www.theverge.com/rss/index.xml"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html"
    ],
    "Science": [
        "https://www.sciencedaily.com/rss/top/science.xml"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.theguardian.com/uk-news/rss"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news"
    ]
}

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleansed = re.sub(cleanr, '', raw_html)
    return cleansed.replace('&nbsp;', ' ').strip()

def background_news_worker():
    while True:
        all_articles = []
        for category, urls in RSS_SOURCES.items():
            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:4]:
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

        # Add Puzzles Hub items
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

        if all_articles:
            with _news_lock:
                _news_cache['articles'] = all_articles
                _news_cache['last_updated'] = time.time()

        time.sleep(1800) # Refresh news every 30 mins in background

threading.Thread(target=background_news_worker, daemon=True).start()


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
    
    with _news_lock:
        articles = _news_cache.get('articles', [])
    
    if not articles:
        articles = [{
            "title": "Global Markets React to New Economic Data",
            "description": "Live tickers update automatically.",
            "category": "World",
            "published": "Recent",
            "link": "#"
        }]

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
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior geopolitical and financial intelligence analyst. Provide a comprehensive, in-depth executive brief structured with: 1) Core Context & Breakdown, 2) Broader Market/Sector Implications, and 3) Forward-Looking Outlook."
                    },
                    {
                        "role": "user",
                        "content": f"Generate a comprehensive intelligence brief for this news article:\nTitle: {article_title}\nSummary: {article_desc}"
                    }
                ],
                "temperature": 0.3
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content']
                return jsonify({"success": True, "brief": content})
        except Exception:
            pass
            
    fallback_brief = f"Comprehensive Executive Brief:\n• Core Analysis: Detailed evaluation of '{article_title}' reveals immediate shifts in policy and market dynamics.\n• Sector Impact: Industry stakeholders face secondary adjustments across related supply chains.\n• Outlook: Sustained monitoring required as broader macroeconomic trends unfold."
    return jsonify({"success": True, "brief": fallback_brief})

@app.route('/api/ask_ai', methods=['POST'])
def api_ask_ai():
    data = request.json or {}
    question = data.get('question', 'What are the broader contextual implications?')
    article_title = data.get('title', '')
    article_desc = data.get('description', '')
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert AI investigative analyst connected via OpenRouter. Use your comprehensive training data and broader analytical reasoning to answer user questions about current events with depth, external context, and strategic insight."
                    },
                    {
                        "role": "user",
                        "content": f"Article Context - Title: {article_title}\nSummary: {article_desc}\n\nUser Question: {question}"
                    }
                ],
                "temperature": 0.4
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                content = res.json()['choices'][0]['message']['content']
                return jsonify({"success": True, "answer": content})
        except Exception:
            pass

    fallback_answer = f"External Context Analysis: Regarding '{article_title}', addressing '{question}' requires evaluating historical precedent, regulatory responses, and macroeconomic indicators across global markets."
    return jsonify({"success": True, "answer": fallback_answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
