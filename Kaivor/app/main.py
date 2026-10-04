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
        "https://feeds.bbci.co.uk/news/uk/rss.xml"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news"
    ]
}

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleansed = re.sub(cleanr, '', raw_html)
    text = cleansed.replace('&nbsp;', ' ').strip()
    if len(text) > 160:
        text = text[:157] + '...'
    return text

def find_rss_via_brave(query):
    brave_key = os.environ.get('BRAVE_API_KEY')
    if not brave_key:
        return None
    try:
        headers = {"X-Subscription-Token": brave_key}
        res = requests.get(f"https://api.search.brave.com/res/v1/web/search?q={query} RSS feed URL", headers=headers, timeout=5)
        if res.status_code == 200:
            results = res.json().get('web', {}).get('results', [])
            for r in results:
                link = r.get('url', '')
                if 'rss' in link or 'feed' in link or '.xml' in link:
                    return link
            if results:
                return results[0].get('url')
    except Exception:
        pass
    return None

def fetch_guardian_articles(category):
    articles = []
    guardian_key = os.environ.get('GUARDIAN_API_KEY')
    if not guardian_key:
        return articles
    try:
        url = f"https://content.guardianapis.com/search?section={category.lower()}&api-key={guardian_key}&show-fields=trailText"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            results = res.json().get('response', {}).get('results', [])
            for item in results[:5]:
                fields = item.get('fields', {})
                desc = fields.get('trailText', 'Guardian coverage update.')
                articles.append({
                    "title": item.get('webTitle', 'Guardian Article'),
                    "description": clean_html(desc),
                    "category": category,
                    "published": item.get('webPublicationDate', 'Recent')[:10],
                    "link": item.get('webUrl', '#')
                })
    except Exception:
        pass
    return articles

def fetch_fresh_news():
    all_articles = []
    for category, urls in RSS_SOURCES.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    raw_desc = entry.get('summary', entry.get('description', ''))
                    all_articles.append({
                        "title": entry.get('title', 'No Title'),
                        "description": clean_html(raw_desc),
                        "category": category,
                        "published": entry.get('published', 'Recent')[:16],
                        "link": entry.get('link', '#')
                    })
            except Exception:
                pass
        
        guardian_items = fetch_guardian_articles(category)
        all_articles.extend(guardian_items)

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

_news_cache = {'articles': fetch_fresh_news(), 'last_updated': time.time()}
_news_lock = threading.Lock()

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

    return render_template('index.html', market=market_data, articles=articles)

@app.route('/api/ticker', methods=['GET'])
def api_ticker():
    with _cache_lock:
        data = _finance_cache.get('data', {})
    return jsonify({"success": True, "ticker": data})

@app.route('/api/add_feed', methods=['POST'])
def api_add_feed():
    data = request.json or {}
    name = data.get('name', '').strip()
    url_input = data.get('url', '').strip()
    
    if name and url_input:
        target_url = url_input
        # If user typed a publication name instead of a URL, use Brave Search API to find it!
        if not url_input.startswith('http'):
            found_url = find_rss_via_brave(url_input)
            if found_url:
                target_url = found_url

        if name not in RSS_SOURCES:
            RSS_SOURCES[name] = []
        RSS_SOURCES[name].append(target_url)
        
        with _news_lock:
            _news_cache['articles'] = fetch_fresh_news()
        return jsonify({"success": True, "resolved_url": target_url})
    return jsonify({"success": False}), 400

@app.route('/api/set_key', methods=['POST'])
def api_set_key():
    data = request.json or {}
    key_type = data.get('type', '').strip()
    api_key = data.get('api_key', '').strip()
    if api_key:
        if key_type == 'guardian':
            os.environ['GUARDIAN_API_KEY'] = api_key
        elif key_type == 'openai':
            os.environ['OPENAI_API_KEY'] = api_key
        elif key_type == 'brave':
            os.environ['BRAVE_API_KEY'] = api_key
        else:
            os.environ['OPENROUTER_API_KEY'] = api_key
        
        with _news_lock:
            _news_cache['articles'] = fetch_fresh_news()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/ai_brief', methods=['POST'])
def api_ai_brief():
    data = request.json or {}
    article_title = data.get('title', '')
    article_desc = data.get('description', '')
    
    # Try OpenRouter first, then OpenAI as fallback
    api_key = os.environ.get('OPENROUTER_API_KEY')
    openai_key = os.environ.get('OPENAI_API_KEY')
    
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Provide a short 3-bullet summary: 1) What happened, 2) Why it matters, 3) Next outlook."},
                    {"role": "user", "content": f"Summarize:\nTitle: {article_title}\nSummary: {article_desc}"}
                ],
                "temperature": 0.3
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                return jsonify({"success": True, "brief": res.json()['choices'][0]['message']['content']})
        except Exception:
            pass

    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Provide a short 3-bullet summary: 1) What happened, 2) Why it matters, 3) Next outlook."},
                    {"role": "user", "content": f"Summarize:\nTitle: {article_title}\nSummary: {article_desc}"}
                ],
                "temperature": 0.3
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                return jsonify({"success": True, "brief": res.json()['choices'][0]['message']['content']})
        except Exception:
            pass
            
    fallback_brief = f"• What happened: Key updates regarding '{article_title}'.\n• Significance: Immediate operational and market adjustments.\n• Outlook: Continued monitoring advised."
    return jsonify({"success": True, "brief": fallback_brief})

@app.route('/api/ask_ai', methods=['POST'])
def api_ask_ai():
    data = request.json or {}
    question = data.get('question', 'What are the implications?')
    article_title = data.get('title', '')
    article_desc = data.get('description', '')
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    openai_key = os.environ.get('OPENAI_API_KEY')
    
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Answer the question concisely using context."},
                    {"role": "user", "content": f"Article: {article_title} - {article_desc}\n\nQuestion: {question}"}
                ],
                "temperature": 0.4
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                return jsonify({"success": True, "answer": res.json()['choices'][0]['message']['content']})
        except Exception:
            pass

    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Answer the question concisely using context."},
                    {"role": "user", "content": f"Article: {article_title} - {article_desc}\n\nQuestion: {question}"}
                ],
                "temperature": 0.4
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                return jsonify({"success": True, "answer": res.json()['choices'][0]['message']['content']})
        except Exception:
            pass

    fallback_answer = f"Analysis: Regarding '{article_title}', addressing '{question}' points to standard industry trends."
    return jsonify({"success": True, "answer": fallback_answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
