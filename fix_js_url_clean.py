with open('templates/index.html', 'r') as f:
    html = f.read()

# Upgraded JavaScript function with automatic client-side URL cleaning
new_js = '''
    <script>
    function importCustomRSS() {
        const urlInput = document.getElementById('rssUrlInput');
        const catSelect = document.getElementById('rssCategorySelect');
        
        if (!urlInput || !catSelect) {
            alert('Error: RSS inputs missing from DOM');
            return;
        }
        
        let url = urlInput.value.trim();
        const category = catSelect.value;
        
        if (!url) {
            alert('Please enter a valid RSS URL.');
            return;
        }
        
        // Automatically clean markdown link formatting if pasted
        if (url.startsWith('[') && url.includes('](')) {
            const parts = url.split('](');
            if (parts.length > 1) {
                url = parts[1].replace(')', '').trim();
            }
        }
        url = url.replace(/^<|>$/g, '').trim();
        
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
# Remove old script block
html = re.sub(r'<script>\s*function importCustomRSS\(\).*?<\/script>', '', html, flags=re.DOTALL)

# Append new script before closing body
html = html.replace('</body>', new_js + '\n</body>')

with open('templates/index.html', 'w') as f:
    f.write(html)

print('Updated templates/index.html with automatic URL cleaner!')
