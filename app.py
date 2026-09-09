from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import feedparser
import re
from feed_seeker import find_feed_url

app = Flask(__name__)

sources = [
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "category": "World"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "category": "World"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "category": "Tech"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "Tech"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "AI"},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "category": "Sport"},
    {"name": "Pitchfork", "url": "https://pitchfork.com/feed/feed-news/rss", "category": "Music"},
    {"name": "Android Police", "url": "https://www.androidpolice.com/feed/", "category": "Android"},
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html", "category": "Business"}
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
        custom_input = request.form.get('custom_input')
        feed_category = request.form.get('feed_category', 'Tech')
        
        target_url = ""
        feed_name = ""
        
        if preset_url:
            target_url = preset_url
            for s in sources:
                if s['url'] == preset_url:
                    feed_name = s['name']
            if not feed_name:
                feed_name = "Preset Feed"
        elif custom_input:
            search_target = custom_input.strip()
            if not search_target.startswith("http"):
                search_target = "https://" + search_target
            
            discovered = find_feed_url(search_target)
            if discovered:
                target_url = discovered
                feed_name = search_target.replace("https://", "").replace("http://", "").split("/")[0].capitalize()
            else:
                target_url = search_target
                feed_name = "Custom Feed"
                
        if target_url and not any(s['url'] == target_url for s in sources):
            sources.append({"name": feed_name, "url": target_url, "category": feed_category})
            
        return redirect(url_for('index'))

    market_data = {}
    try:
        tickers = {
            "S&P 500": "^GSPC", 
            "NASDAQ": "^IXIC",
            "FTSE 100": "^FTSE", 
            "Bitcoin": "BTC-USD", 
            "Ethereum": "ETH-USD", 
            "Gold": "GC=F",
            "Oil": "CL=F",
            "GBP/USD": "GBPUSD=X", 
            "EUR/USD": "EURUSD=X"
        }
        for name, symbol in tickers.items():
            t = yf.Ticker(symbol)
            todays_data = t.history(period="1d")
            if not todays_data.empty:
                price = todays_data['Close'].iloc[-1]
                market_data[name] = round(price, 4) if "USD" in name or "/" in name else round(price, 2)
    except Exception as e:
        print("Market data error:", e)

    news_by_category = {}
    for source in sources:
        parsed = feedparser.parse(source['url'])
        articles = []
        for entry in parsed.entries[:4]:
            articles.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "image": extract_image(entry)
            })
        
        cat = source['category']
        if cat not in news_by_category:
            news_by_category[cat] = {}
        news_by_category[cat][source['name']] = articles

    return render_template('index.html', news_by_category=news_by_category, market_data=market_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
