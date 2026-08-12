import requests, feedparser, hashlib, json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from app.models.news import db, Article, Source

class IngestionService:
    @staticmethod
    def discover_candidates(query, openrouter_key):
        """Uses AI to find the website, then sniffs for RSS."""
        prompt = f"Find the official website and RSS feed for '{query}'. Return ONLY JSON: {{'name': '...', 'website': '...', 'feed': '...'}}"
        headers = {"Authorization": f"Bearer {openrouter_key}", "HTTP-Referer": "https://kaivor.io"}
        
        try:
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, 
                json={"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}]}).json()
            data = json.loads(re.search(r'\{.*\}', res['choices'][0]['message']['content'], re.DOTALL).group(0))
            return data
        except: return None

    @staticmethod
    def validate_and_normalize(source_url):
        """Fetches a feed and confirms it is valid."""
        try:
            r = requests.get(source_url, headers={'User-Agent': 'KaivorEngine/1.0'}, timeout=5)
            feed = feedparser.parse(r.content)
            if not feed.entries: return None
            return feed
        except: return None

    @staticmethod
    def ingest_source(source):
        """The Fetch -> Parse -> Validate -> Normalize -> Deduplicate loop."""
        feed_data = IngestionService.validate_and_normalize(source.feed_url)
        if not feed_data: return 0
        
        new_count = 0
        for entry in feed_data.entries[:20]:
            # Deduplication via URL Hash
            url = entry.link
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            
            if not Article.query.filter_by(hash=url_hash).first():
                img = entry.get('media_thumbnail', [{}])[0].get('url') or entry.get('media_content', [{}])[0].get('url')
                
                article = Article(
                    source_id=source.id,
                    title=entry.title,
                    description=entry.get('summary', ''),
                    article_url=url,
                    image_url=img,
                    published_at=datetime.now(), # Simplified for build
                    hash=url_hash
                )
                db.session.add(article)
                new_count += 1
        
        source.last_successful_import = datetime.utcnow()
        db.session.commit()
        return new_count
