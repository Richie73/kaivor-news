import os
from flask import Flask, render_template, request, jsonify
import feedparser
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

CATEGORY_FEEDS = {
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
        "https://moxie.foxnews.com/feedburner/world.rss",
        "https://www.aljazeera.com/xml/rss/all.rss",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/en/top-stories/s-9097/rss"
    ],
    "Politics": [
        "https://www.foreignaffairs.com/rss.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://rss.politico.com/politics-news.xml"
    ],
    "Science": [
        "https://www.newscientist.com/feed/home/",
        "https://www.sciencedaily.com/rss/top.xml",
        "https://www.nature.com/nature.rss"
    ],
    "UK": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.independent.co.uk/news/uk/rss",
        "https://www.standard.co.uk/rss"
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss"
    ],
    "Business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://feeds.feedburner.com/reuters/businessNews"
    ],
    "Sport": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.skysports.com/rss/12110",
        "https://www.espn.com/espn/rss/football/news"
    ],
    "Music": [
        "https://pitchfork.com/feed/feed-news/rss",
        "https://www.rollingstone.com/music/music-news/feed/",
        "https://NME.com/feed"
    ],
    "Android": [
        "https://9to5google.com/feed/",
        "https://www.androidcentral.com/rss.xml",
        "https://www.androidpolice.com/feed/"
    ],
    "Puzzles": []
}

FEED_CACHE = {}
CACHE_TTL = 300

MASTER_PHOTO_POOL = [
    "1507413245164-6160d8298b31", "1532094349884-543bc11b234d", "1507668077129-56e32842fceb",
    "1518770660439-4636190af475", "1530497610245-94d3c16cda28", "1516321318423-f06f85e504b3",
    "1541872703-74c5e44368f9", "1529101091764-c3526daf38fe", "1521747116042-5a810fda9664",
    "1486406146926-c627a92ad1ab", "1555848962-6e79363ec58f", "1508873696983-2df5c920aac9",
    "1526374965328-7f61d4dc18c5", "1535378917042-10a22c95931a", "1550751827-4bd374c3f58b",
    "1519389950473-47ba0277781c", "1451187580459-43490279c0fa", "1611974789855-9c2a0a7236a3",
    "1590283603385-17ffb3a7f29f", "1460925895917-afdab827c52f", "1559526324-4b87b5e36e44",
    "1526304640581-d334cdbbf45e", "1508098682722-e99c43a406b2", "1574629810360-7efbbe195018",
    "1518091043644-c1d4457512c6", "1461896836934-ffe607ba8211", "1517649763962-0c623066013b",
    "1543326727-cf6c39e8f84c", "1511671782779-c97d3d27a1d4", "1470225620780-dba8ba36b745",
    "1514525253161-7a46d19cd819", "1511192336575-5a79af67a629", "1585829365295-ab7cd400c167",
    "1446776811953-b23d57bd21aa", "1509228468518-180dd4864904", "1551288049-bebda4e38f71",
    "1504384308090-c894fdcc538d", "1454165804606-c3d57bc86b40", "1517245386807-bb43f82c33c4",
    "1516321497487-e288fb19713f", "1522071820081-009f0129c71c", "1551836022-d5d88e9218df",
    "1503676260728-1c00da094a0b", "1517841905240-472988babdf9", "1531482615713-2afd69097998"
]

def fetch_guardian_articles(api_key, section="world", used_photos=None):
    if used_photos is None:
        used_photos = set()
    articles = []
    if not api_key or api_key.strip() == "":
        return articles
    
    url = f"https://content.guardianapis.com/search?section={section}&page-size=15&show-fields=thumbnail,trailText,byline&api-key={api_key.strip()}"
    try:
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            data = response.json()
            results = data.get("response", {}).get("results", [])
            for item in results:
                fields = item.get("fields", {})
                title = item.get("webTitle", "No Title")
                
                available_pool = [p for p in MASTER_PHOTO_POOL if p not in used_photos]
                if not available_pool:
                    available_pool = MASTER_PHOTO_POOL
                
                chosen_photo = available_pool[abs(hash(title)) % len(available_pool)]
                used_photos.add(chosen_photo)
                
                img = fields.get("thumbnail") or f"https://images.unsplash.com/photo-{chosen_photo}?w=300&auto=format&fit=crop&q=80"
                articles.append({
                    "title": title,
                    "link": item.get("webUrl", "#"),
                    "published": item.get("webPublicationDate", "Recent")[:10],
                    "summary": fields.get("trailText", "Comprehensive long-form investigative analysis and reporting..."),
                    "image": img,
                    "read_time": "12 min read"
                })
    except Exception as e:
        print(f"Guardian API Error: {e}")
    return articles

def extract_image(entry, title="", used_photos=None):
    if used_photos is None:
        used_photos = set()

    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url')
            if url and url.startswith('http'):
                return url
                
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        for thumb in entry.media_thumbnail:
            url = thumb.get('url')
            if url and url.startswith('http'):
                return url

    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            url = enc.get('href')
            if url and url.startswith('http'):
                return url
    
    content = entry.get("summary", "")
    if hasattr(entry, 'content') and entry.content:
        for c in entry.content:
            content += c.get('value', '')
            
    soup = BeautifulSoup(content, "html.parser")
    img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src")
        if src and src.startswith('http'):
            return src

    available_pool = [p for p in MASTER_PHOTO_POOL if p not in used_photos]
    if not available_pool:
        available_pool = MASTER_PHOTO_POOL

    chosen_photo = available_pool[abs(hash(title)) % len(available_pool)]
    used_photos.add(chosen_photo)
    return f"https://images.unsplash.com/photo-{chosen_photo}?w=300&auto=format&fit=crop&q=80"

def calculate_read_time(text):
    words = len(text.split())
    if words < 30:
        return "4 min read"
    elif words < 70:
        return "7 min read"
    elif words < 120:
        return "11 min read"
    else:
        return "15 min read"

def parse_single_feed(url, category, used_photos):
    now = time.time()
    cache_key = f"{category}_{url}"
    if cache_key in FEED_CACHE:
        cached_data, timestamp = FEED_CACHE[cache_key]
        if now - timestamp < CACHE_TTL:
            return cached_data

    feed_articles = []
    try:
        parsed_feed = feedparser.parse(url)
        for entry in parsed_feed.entries[:8]:
            summary_text = entry.get("summary", "")
            clean_summary = BeautifulSoup(summary_text, "html.parser").get_text()
            title = entry.get("title", "No Title")
            image_url = extract_image(entry, title, used_photos)
            read_time = calculate_read_time(clean_summary)
            
            feed_articles.append({
                "title": title,
                "link": entry.get("link", "#"),
                "published": entry.get("published", "Recent")[:16],
                "summary": clean_summary[:140] + "...",
                "image": image_url,
                "read_time": read_time
            })
        FEED_CACHE[cache_key] = (feed_articles, now)
    except Exception as e:
        print(f"Feed Error ({url}): {e}")
    return feed_articles

@app.route("/")
def index():
    category = request.args.get("category", "World")
    custom_feed = request.args.get("custom_feed", "")
    guardian_key = request.args.get("guardian_key", "")
    
    articles = []
    used_photos = set()
    
    if category == "Puzzles":
        articles = [
            {"title": "The Independent - Daily Crosswords & Puzzles", "link": "https://www.independent.co.uk/life-style/puzzles", "published": "Daily Puzzles", "summary": "Play daily crosswords, word searches, and brain teasers from The Independent.", "image": "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=300&auto=format&fit=crop&q=80", "read_time": "15 min play"},
            {"title": "The Guardian - Daily Crosswords & Quiptic", "link": "https://www.theguardian.com/crosswords", "published": "Daily Puzzles", "summary": "Explore famous Guardian crosswords including Quick, Cryptic, and Quiptic puzzles.", "image": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=300&auto=format&fit=crop&q=80", "read_time": "12 min play"},
            {"title": "The New York Times - The Mini Crossword", "link": "https://www.nytimes.com/crosswords/game/mini", "published": "Daily Puzzle", "summary": "A snappy, miniature crossword puzzle designed to be solved in minutes.", "image": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=300&auto=format&fit=crop&q=80", "read_time": "5 min play"},
            {"title": "Wordle - Daily Word Guessing Game", "link": "https://www.nytimes.com/games/wordle/index.html", "published": "Daily Puzzle", "summary": "Guess the hidden 5-letter word in 6 tries with color-coded clues.", "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=300&auto=format&fit=crop&q=80", "read_time": "5 min play"},
            {"title": "Connections - Group Words by Common Thread", "link": "https://www.nytimes.com/games/connections", "published": "Daily Puzzle", "summary": "Find groups of four items that share something in common without making mistakes.", "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=300&auto=format&fit=crop&q=80", "read_time": "6 min play"},
            {"title": "Daily Sudoku - Number Placement Challenge", "link": "https://sudoku.com/", "published": "Daily Puzzle", "summary": "Fill the 9x9 grid so that each column, row, and section contains digits 1-9.", "image": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300&auto=format&fit=crop&q=80", "read_time": "10 min play"}
        ]
    else:
        if guardian_key:
            if category == "World":
                articles.extend(fetch_guardian_articles(guardian_key, section="world", used_photos=used_photos))
            elif category == "UK":
                articles.extend(fetch_guardian_articles(guardian_key, section="uk", used_photos=used_photos))
            elif category == "Sport":
                articles.extend(fetch_guardian_articles(guardian_key, section="sport", used_photos=used_photos))

        feed_urls = [custom_feed] if custom_feed else CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["World"])
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
            
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(parse_single_feed, url, category, used_photos): url for url in feed_urls}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    articles.extend(res)

    return render_template("index.html", category=category, categories=CATEGORY_FEEDS.keys(), articles=articles, custom_feed=custom_feed, guardian_key=guardian_key)

@app.route("/api/brief", methods=["POST"])
def ai_brief():
    data = request.get_json()
    title = data.get("title", "this article")
    summary = data.get("summary", "")
    api_key = data.get("apiKey", "")

    if not api_key:
        return jsonify({"brief": "Please enter your DeepSeek API key in the Manager panel above."})

    try:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kaivor-news.onrender.com",
            "X-Title": "Kaivor News"
        }
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional geopolitical and financial news analyst. Provide a sharp, concise 2-sentence executive brief analyzing the core structural impact of this news story."},
                {"role": "user", "content": f"Article Title: {title}\nSummary: {summary}"}
            ]
        }
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            brief_text = result["choices"][0]["message"]["content"]
            return jsonify({"brief": brief_text})
        else:
            print('OpenRouter Error Response:', response.text)
        return jsonify({"brief": f"API Error ({response.status_code}): {response.text}"})
    except Exception as e:
        return jsonify({"brief": f"Request Timeout / Failed: {str(e)}"})

@app.route("/api/ask", methods=["POST"])
def ai_ask():
    data = request.get_json()
    title = data.get("title", "")
    summary = data.get("summary", "")
    question = data.get("question", "")
    api_key = data.get("apiKey", "")

    if not api_key:
        return jsonify({"answer": "Please enter your DeepSeek API key in the Manager panel."})

    try:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kaivor-news.onrender.com",
            "X-Title": "Kaivor News"
        }
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an expert intelligence analyst answering specific user questions about a news article. Be concise, objective, and insightful."},
                {"role": "user", "content": f"Article: {title}\nSummary: {summary}\n\nQuestion: {question}"}
            ]
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            return jsonify({"answer": result["choices"][0]["message"]["content"]})
        else:
            return jsonify({"answer": "API Error: Check your OpenRouter API key or model credits."})
    except Exception as e:
        return jsonify({"answer": f"Request failed: {str(e)}"})

@app.route("/api/digest", methods=["POST"])
def daily_digest():
    data = request.get_json()
    titles = data.get("titles", [])
    api_key = data.get("apiKey", "")

    if not api_key:
        return jsonify({"digest": "Please enter your DeepSeek API key in the Manager panel."})

    headlines_text = "\n".join([f"- {t}" for t in titles])

    try:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kaivor-news.onrender.com",
            "X-Title": "Kaivor News"
        }
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an elite chief intelligence briefing officer for global markets and geopolitics. Provide a rigorous, highly professional 5-bullet executive synthesis analyzing macro trends, cross-industry correlations, and strategic takeaways across these headlines. Format each bullet cleanly with a bold title and concise explanation."},
                {"role": "user", "content": f"Today's Top Headlines:\n{headlines_text}"}
            ]
        }
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            result = response.json()
            digest_text = result["choices"][0]["message"]["content"]
            return jsonify({"digest": digest_text})
        else:
            return jsonify({"digest": f"API Error: Check your OpenRouter API key or model credits."})
    except Exception as e:
        return jsonify({"digest": f"Failed: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json()
    text = data.get("text", "")
    api_key = data.get("apiKey", "")
    if not api_key:
        return jsonify({"error": "Please enter your OpenAI API key."}), 400
    try:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1-hd",
            "input": text,
            "voice": "alloy"
        }
        resp = requests.post("https://api.openai.com/v1/audio/speech", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.content, 200, {"Content-Type": "audio/mpeg"}
        return jsonify({"error": f"OpenAI TTS Error: {resp.text}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# RSS route active



@app.route('/api/add-rss', methods=['POST'])
def add_rss():
    try:
        data = request.get_json() or {}
        raw_url = data.get('url', '').strip()
        category = data.get('category', 'World')
        
        if '[' in raw_url and '](' in raw_url:
            parts = raw_url.split('](')
            url = parts[1].replace(')', '').strip() if len(parts) > 1 else parts[0].replace('[', '').strip()
        else:
            url = raw_url
        url = url.strip('<>"''')
        
        if not url:
            return jsonify({'success': False, 'error': 'RSS URL is required'}), 400
            
        import urllib.request, feedparser
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                feed = feedparser.parse(response.read())
        except Exception as net_err:
            return jsonify({'success': False, 'error': f'Connection failed: {str(net_err)}'}), 400
            
        if not feed.entries:
            return jsonify({'success': False, 'error': 'No entries found in this RSS feed.'}), 400
            
        global FEEDS
        if 'FEEDS' not in globals():
            global feeds
            FEEDS = globals().get('feeds', {})
            
        if category not in FEEDS:
            FEEDS[category] = []
            
        imported = 0
        for entry in feed.entries[:15]:
            article = {
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', '#'),
                'summary': entry.get('summary', entry.get('description', 'No summary available.')),
                'published': entry.get('published', 'Today')
            }
            if not any(a['link'] == article['link'] for a in FEEDS[category]):
                FEEDS[category].insert(0, article)
                imported += 1
                
        return jsonify({'success': True, 'message': f'Successfully imported {imported} articles into {category}!'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server Error: {str(e)}'}), 500



