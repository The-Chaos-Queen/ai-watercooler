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

print("Unwrapping custom Distill web components...")
# Convert custom <d-*> tags to standard divs or spans so markdownify doesn't strip them
for tag in soup.find_all(re.compile("^d-")):
    tag.name = "div"

# Remove all inline scripts, styles, svgs that clutter the markdown
for script in soup(["script", "style", "svg", "nav", "footer"]):
    script.extract()

print("Extracting and downloading images...")
img_tags = soup.find_all('img')
count = 0
for img in img_tags:
    src = img.get('src')
    if not src or src.startswith('data:'):
        continue
    
    full_url = urljoin(url, src)
    filename = src.split('/')[-1].split('?')[0]
    if not filename:
        filename = f"image_{count}.png"
        
    local_path = os.path.join(images_dir, filename)
    
    try:
        if not os.path.exists(local_path):
            urllib.request.urlretrieve(full_url, local_path)
            print(f"Downloaded: {filename}")
        img['src'] = f"images/{filename}"
        count += 1
    except Exception as e:
        print(f"Failed to download {full_url}: {e}")

print("Converting to Markdown...")
# Use markdownify with strip=None to preserve text inside unknown tags just in case
md_content = markdownify.markdownify(str(soup), heading_style="ATX", escape_asterisks=False, strip=None)

# Cleanup extra newlines
md_content = re.sub(r'\n{3,}', '\n\n', md_content)

md_file = os.path.join(base_dir, "emotions_paper_full.md")
with open(md_file, "w", encoding="utf-8") as f:
    f.write(md_content)
    
print(f"Successfully extracted paper to: {md_file}")
print(f"File size: {os.path.getsize(md_file)} bytes")
