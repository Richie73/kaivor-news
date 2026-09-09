from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import feedparser

app = Flask(__name__)

# Sample storage for feeds
feeds = [
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"}
]

@app.route('/')
def index():
    # Fetch market data (S&P 500, Bitcoin, Gold)
    market_data = {}
    try:
        tickers = {"SP500": "^GSPC", "Bitcoin": "BTC-USD", "Gold": "GC=F"}
        for name, symbol in tickers.items():
            t = yf.Ticker(symbol)
            todays_data = t.history(period="1d")
            if not todays_data.empty:
                price = todays_data['Close'].iloc[-1]
                market_data[name] = round(price, 2)
    except Exception as e:
        print("Market data error:", e)

    # Fetch news articles
    news_grouped = {}
    for feed_info in feeds:
        parsed = feedparser.parse(feed_info['url'])
        articles = []
        for entry in parsed.entries[:5]: # Top 5 per feed
            articles.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#")
            })
        news_grouped[feed_info['name']] = articles

    return render_template('index.html', news_grouped=news_grouped, market_data=market_data, feeds=feeds)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
