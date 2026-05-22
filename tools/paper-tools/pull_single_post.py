import os
import urllib.request
from playwright.sync_api import sync_playwright

def pull_post(url, out_dir_name):
    base_dir = os.path.join(r"C:\Users\cerub\OneDrive\Dokumente\LLM\Research", out_dir_name)
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    print(f"\n--- Processing: {out_dir_name} ---")
    print(f"URL: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll down to trigger any lazy-loaded images
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)
            
            # Get innerText
            text_content = page.evaluate("document.body.innerText")
            text_path = os.path.join(base_dir, "innerText.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text_content)
            print(f"Saved text ({len(text_content)} chars)")
            
            # Get images
            img_srcs = page.evaluate("Array.from(document.querySelectorAll('img')).map(img => img.src)")
            count = 0
            for src in set(img_srcs):
                if not src or src.startswith('data:'): 
                    continue
                
                filename = src.split('/')[-1].split('?')[0]
                if not filename:
                    filename = f"image_{count}.png"
                
                # Sanitize filename
                filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
                
                local_path = os.path.join(images_dir, filename)
                
                try:
                    if not os.path.exists(local_path):
                        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response, open(local_path, 'wb') as out_file:
                            out_file.write(response.read())
                        print(f"Downloaded: {filename}")
                    count += 1
                except Exception as e:
                    print(f"Failed to download {src}: {e}")
                    
        except Exception as e:
            print(f"Error processing page: {e}")
        finally:
            browser.close()
    print(f"Done with {out_dir_name}.")

if __name__ == '__main__':
    pull_post("https://www.4billionyearson.org/posts/coffee-phone-stairs-and-a-cat-nailing-the-boundaries-of-consciousness-and-ai#drawing-the-boundary", "4billionyearson_boundaries")
