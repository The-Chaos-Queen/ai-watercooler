import urllib.request
import json

try:
    response = urllib.request.urlopen('http://localhost:9222/json/list')
    data = json.loads(response.read())

    count = 1
    with open(r'C:\Users\cerub\OneDrive\Dokumente\LLM\browser_tabs.md', 'w', encoding='utf-8') as out:
        out.write('# Open Browser Tabs\n\n')
        for t in data:
            url = t.get('url', '')
            if url and not url.startswith('devtools://') and not url.startswith('chrome-extension://'):
                title = t.get('title', 'No Title')
                out.write(f"{count}. **{title}**\n   - {url}\n\n")
                count += 1

    print(f"Successfully formatted {count-1} tabs.")
except Exception as e:
    print(f"Error: {e}")