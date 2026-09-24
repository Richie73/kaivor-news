with open('main.py', 'r') as f:
    content = f.read()

# Ensure feedparser is imported
if 'import feedparser' not in content:
    content = 'import feedparser\n' + content

# Define route cleanly
new_route = '''
@app.route('/api/add-rss', methods=['POST'])
def add_rss():
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        category = data.get('category', 'World')
        
        if not url:
            return jsonify({'success': False, 'error': 'RSS URL is required'}), 400
            
        feed = feedparser.parse(url)
        if not feed.entries:
            return jsonify({'success': False, 'error': 'No entries found in this RSS feed.'}), 400
            
        global FEEDS
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
        return jsonify({'success': False, 'error': str(e)}), 500
'''

if '/api/add-rss' not in content:
    content = content.replace("if __name__ == '__main__':", new_route + "\n\nif __name__ == '__main__':")
    with open('main.py', 'w') as f:
        f.write(content)
    print('Successfully added clean route to main.py!')
