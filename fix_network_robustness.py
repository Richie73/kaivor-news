with open('main.py', 'r') as f:
    code = f.read()

# Replace or append the robust add_rss route
import re
code = re.sub(r'@app\.route\(\'/api/add-rss\',.*?(?=\n@app\.route|\nif __name__|\Z)', '', code, flags=re.DOTALL)

robust_route = '''
@app.route('/api/add-rss', methods=['POST'])
def add_rss():
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        category = data.get('category', 'World')
        
        if not url:
            return jsonify({'success': False, 'error': 'RSS URL is required'}), 400
            
        import urllib.request, feedparser
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read()
                feed = feedparser.parse(html_content)
        except Exception as net_err:
            return jsonify({'success': False, 'error': f'Connection failed: {str(net_err)}'}), 400
            
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

code = code.replace("if __name__ == '__main__':", robust_route + "\n\nif __name__ == '__main__':")

with open('main.py', 'w') as f:
    f.write(code)

# Also update templates/index.html fetch catch for detailed debugging
with open('templates/index.html', 'r') as f:
    html = f.read()

new_js = '''
    <script>
    function importCustomRSS() {
        const urlInput = document.getElementById('rssUrlInput');
        const catSelect = document.getElementById('rssCategorySelect');
        
        if (!urlInput || !catSelect) {
            alert('Error: RSS inputs missing from DOM');
            return;
        }
        
        let rawInput = urlInput.value.trim();
        const category = catSelect.value;
        
        if (!rawInput) {
            alert('Please enter a valid RSS URL.');
            return;
        }
        
        const urlMatch = rawInput.match(/https?:\\/\\/[^\\s\\)]+/);
        const url = urlMatch ? urlMatch[0] : rawInput;
        
        alert('Importing feed... Please wait.');
        
        fetch('/api/add-rss', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, category: category })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Failed to import RSS feed.'));
            }
        })
        .catch(err => {
            alert('Fetch Error: ' + err);
        });
    }
    </script>
'''

html = re.sub(r'<script>\s*function importCustomRSS\(\).*?<\/script>', '', html, flags=re.DOTALL)
html = html.replace('</body>', new_js + '\n</body>')

with open('templates/index.html', 'w') as f:
    f.write(html)

print('Updated main.py and templates/index.html successfully!')
