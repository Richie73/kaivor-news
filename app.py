from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import feedparser
import re

app = Flask(__name__)

feeds = [
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"}
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
        
    return None

@app.route('/')
def index():
    # Comprehensive financial markets tracking
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

    news_grouped = {}
    for feed_info in feeds:
        parsed = feedparser.parse(feed_info['url'])
        articles = []
        for entry in parsed.entries[:5]:
            articles.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "image": extract_image(entry)
            })
        news_grouped[feed_info['name']] = articles

    return render_template('index.html', news_grouped=news_grouped, market_data=market_data, feeds=feeds)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
