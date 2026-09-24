with open('main.py', 'r') as f:
    code = f.read()

# Replace the URL extraction in add_rss to aggressively clean markdown
old_url_extract = "url = data.get('url', '').strip()"
new_url_extract = """
        raw_url = data.get('url', '').strip()
        # Aggressively extract pure URL if markdown formatting was pasted
        if '[' in raw_url and '](' in raw_url:
            parts = raw_url.split('](')
            url = parts[1].replace(')', '').strip() if len(parts) > 1 else parts[0].replace('[', '').strip()
        else:
            url = raw_url
        url = url.strip('<>\"\\'')
"""

if 'Aggressively extract pure URL' not in code:
    code = code.replace(old_url_extract, new_url_extract)
    with open('main.py', 'w') as f:
        f.write(code)
    print('Added aggressive markdown URL stripping to backend!')
