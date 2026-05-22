import urllib.request
import json
import asyncio
import websockets
import re
import os

out_dir = r"C:\Users\cerub\OneDrive\Dokumente\LLM\Research"

async def extract_text(ws_url):
    try:
        async with websockets.connect(ws_url) as ws:
            # Send evaluate command
            cmd = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                }
            }
            await ws.send(json.dumps(cmd))
            
            # Wait for response
            while True:
                response = await ws.recv()
                data = json.loads(response)
                if data.get("id") == 1:
                    result = data.get("result", {}).get("result", {}).get("value", "")
                    return result
    except Exception as e:
        print(f"WS error: {e}")
        return ""

async def main():
    req = urllib.request.Request('http://localhost:9222/json/list')
    with urllib.request.urlopen(req) as response:
        tabs = json.loads(response.read())
        
    print(f"Found {len(tabs)} tabs.")
    closed_spam = 0
    archived_reddit = 0
    
    for t in tabs:
        url = t.get('url', '')
        tab_id = t.get('id')
        title = t.get('title', 'No Title')
        
        # 1. Close Spam
        if any(x in url for x in ["recaptcha/enterprise", "sw.js", "chrome://newtab", "startpage.com/do/search"]):
            try:
                urllib.request.urlopen(f'http://localhost:9222/json/close/{tab_id}')
                closed_spam += 1
            except Exception as e:
                pass
            continue
            
        # 2. Extract Reddit
        if "reddit.com/r/" in url and "/comments/" in url:
            ws_url = t.get('webSocketDebuggerUrl')
            if ws_url:
                print(f"Extracting: {title}")
                content = await extract_text(ws_url)
                if content:
                    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title[:60])
                    filename = f"2026-05-11_Reddit_{safe_title}.md"
                    filepath = os.path.join(out_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"# {title}\n\n**Source:** {url}\n\n---\n\n{content}")
                        
                    print(f"Saved {filename}")
                    archived_reddit += 1
                    
                    # Close the tab
                    try:
                        urllib.request.urlopen(f'http://localhost:9222/json/close/{tab_id}')
                    except:
                        pass
                else:
                    print(f"Failed to extract content for: {title}")

    print(f"Finished. Closed {closed_spam} spam tabs. Archived {archived_reddit} Reddit threads.")

asyncio.run(main())