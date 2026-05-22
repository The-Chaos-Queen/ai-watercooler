import os
import re
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import markdownify

url = "https://transformer-circuits.pub/2026/emotions/index.html"
base_dir = r"C:\Users\cerub\OneDrive\Dokumente\LLM\Research\emotions_paper_extracted"
images_dir = os.path.join(base_dir, "images")

os.makedirs(images_dir, exist_ok=True)

print("Fetching HTML...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html_content = urllib.request.urlopen(req).read().decode('utf-8')

soup = BeautifulSoup(html_content, 'html.parser')

print("Extracting and downloading images...")
img_tags = soup.find_all('img')
for img in img_tags:
    src = img.get('src')
    if not src or src.startswith('data:'):
        continue
    
    full_url = urljoin(url, src)
    # clean filename
    filename = src.split('/')[-1].split('?')[0]
    if not filename:
        filename = f"image_{img_tags.index(img)}.png"
        
    local_path = os.path.join(images_dir, filename)
    
    try:
        urllib.request.urlretrieve(full_url, local_path)
        # Update the src in the HTML to relative local path
        img['src'] = f"images/{filename}"
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed to download {full_url}: {e}")

print("Converting to Markdown...")
# Some Anthropic papers use custom tags like <d-figure>, <d-math>. We can convert them to string or just let markdownify handle them.
md_content = markdownify.markdownify(str(soup), heading_style="ATX", escape_asterisks=False)

md_file = os.path.join(base_dir, "emotions_paper.md")
with open(md_file, "w", encoding="utf-8") as f:
    f.write(md_content)
    
html_file = os.path.join(base_dir, "emotions_paper_local.html")
with open(html_file, "w", encoding="utf-8") as f:
    f.write(str(soup))

print(f"Successfully extracted {len(img_tags)} images and saved paper to: {base_dir}")
