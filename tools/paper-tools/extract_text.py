from playwright.sync_api import sync_playwright
import os

url = "https://transformer-circuits.pub/2026/emotions/index.html"
output_path = r"C:\Users\cerub\OneDrive\Dokumente\LLM\Research\emotions_paper_extracted\innerText.txt"

print("Starting Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"Navigating to {url}...")
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    
    print("Extracting innerText...")
    content = page.evaluate("document.body.innerText")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    browser.close()

print(f"Saved innerText ({len(content)} chars) to {output_path}")
