with open('main.py', 'r') as f:
    code = f.read()

# Update the add_rss function to clean up markdown links if pasted
old_url_line = "url = data.get('url')"
new_url_lines = """
        url = data.get('url', '').strip()
        # Clean up markdown links if accidentally pasted, e.g., [url](url) or <url>
        if url.startswith('[') and '](' in url:
            url = url.split('](')[0][1:]
        elif url.startswith('<') and url.endswith('>'):
            url = url[1:-1]
        url = url.strip('\"\'')
"""

if 'Clean up markdown links' not in code:
    code = code.replace(old_url_line, new_url_lines)
    with open('main.py', 'w') as f:
        f.write(code)
    print('Added automatic URL cleaning to main.py!')
