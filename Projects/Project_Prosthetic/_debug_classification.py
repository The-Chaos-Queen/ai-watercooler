import email
from email import policy
from pathlib import Path
from bs4 import BeautifulSoup
import sys

# hyper-verbose classification debug
sys.stdout.reconfigure(encoding='utf-8')

import html_to_markdown

input_file = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\html-to-convert\LMArena.mht")
html = html_to_markdown.extract_html_from_mht(input_file)
soup = BeautifulSoup(html, "html.parser")

platform = html_to_markdown.PLATFORMS["lmarena"]
user_sels = platform["user_selector"]
asst_sels = platform["assistant_selector"]
combined_sel = ", ".join(user_sels + asst_sels)
raw_nodes = soup.select(combined_sel)

# Fast Dedup
raw_nodes_ids = {id(n) for n in raw_nodes if n.name not in ("html", "body", "main", "section", "header", "footer")}
nodes = []
for n in raw_nodes:
    if n.name in ("html", "body", "main", "section", "header", "footer"): continue
    is_nested = False
    current = n.parent
    while current:
        if id(current) in raw_nodes_ids:
            is_nested = True
            break
        current = current.parent
    if not is_nested:
        nodes.append(n)

print(f"DEBUG: Found {len(nodes)} top-level nodes")

if nodes:
    # Check parentage of node 0 and node -1
    for idx in [0, len(nodes)//2, len(nodes)-1]:
        print(f"\nTrace for node [{idx}]:")
        curr = nodes[idx]
        for _ in range(5):
            print(f"  P{_}: <{curr.name}> classes={curr.get('class', [])}")
            curr = curr.parent
            if not curr: break
