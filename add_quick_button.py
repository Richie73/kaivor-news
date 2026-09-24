with open('templates/index.html', 'r') as f:
    html = f.read()

# Replace the RSS input row with one that includes a quick-fill button for Hacker News
old_ui = '''
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <input type="text" id="rssUrlInput" placeholder="https://news.ycombinator.com/rss" style="flex: 1; min-width: 150px; padding: 6px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 4px; font-size: 0.8rem;">
'''

new_ui = '''
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <input type="text" id="rssUrlInput" placeholder="https://news.ycombinator.com/rss" style="flex: 1; min-width: 150px; padding: 6px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 4px; font-size: 0.8rem;">
            <button type="button" onclick="document.getElementById('rssUrlInput').value='https://news.ycombinator.com/rss'; document.getElementById('rssCategorySelect').value='Tech';" style="background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 8px; border-radius: 4px; cursor: pointer; font-size: 0.75rem;">Load HN</button>
'''

if 'Load HN' not in html:
    html = html.replace(old_ui.strip(), new_ui.strip())
    with open('templates/index.html', 'w') as f:
        f.write(html)
    print('Added Load HN quick-fill button!')
