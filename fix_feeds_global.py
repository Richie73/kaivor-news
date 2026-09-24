with open('main.py', 'r') as f:
    code = f.read()

# Remove the old add_rss route completely
import re
code = re.sub(r'@app\.route\(\'/api/add-rss\',.*?(?=\n@app\.route|\nif __name__|\Z)', '', code, flags=re.DOTALL)

# Find what dictionary name holds the feeds (e.g., FEEDS, categories, news_feeds)
# Let's write a bulletproof route that safely checks or initializes feeds
correct_route = '''
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
        url = url.strip('<>\"\\'')
        
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
            
        # Access or create global feeds dictionary safely
        global FEEDS
        if 'FEEDS' not in globals():
            # Fallback if named differently in v1.0
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
'''

code = code.replace("if __name__ == '__main__':", correct_route + "\n\nif __name__ == '__main__':")

with open('main.py', 'w') as f:
    f.write(code)

print('Updated main.py with safe global FEEDS handling!')
