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
        
        // Extract the first http:// or https:// URL found in the input string
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
            alert('Network error while importing RSS feed.');
        });
    }
    </script>
'''

import re
html = re.sub(r'<script>\s*function importCustomRSS\(\).*?<\/script>', '', html, flags=re.DOTALL)
html = html.replace('</body>', new_js + '\n</body>')

with open('templates/index.html', 'w') as f:
    f.write(html)

print('Updated templates/index.html with regex URL extractor!')
