from playwright.sync_api import sync_playwright
import time

class WebSense:
    """
    The 'Third Sense' of the Cyborg: Direct DOM Manipulation.
    Uses Playwright to interact with web pages reliably, bypassing vision limitations.
    """
    def __init__(self, headless=False):
        self.playwright = sync_playwright().start()
        
        # Path for Persistent Profile
        self.user_data_dir = r"C:\Users\cerub\OneDrive\Dokumente\LLM\Project_Prosthetic\chrome_profile"
        
        print(f"=== WEB SENSE ONLINE (Stealth Mode: Edge) ===")
        # Microsoft Edge is the most reliable automation target on Windows.
        # It supports extensions and codecs better than bare Chromium.
        
        self.context = self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=headless,
            channel="msedge", # Use user's Edge installation
            viewport={"width": 1280, "height": 720},
            ignore_default_args=["--enable-automation"],
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # In persistent context, pages[0] exists by default
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def ensure_active(self):
        """Checks if page is closed and reopens if needed."""
        try:
            if self.page.is_closed():
                print("[WEB] Page closed. Reopening...")
                self.page = self.context.new_page()
        except:
             print("[WEB] Browser context lost. Restarting...")
             # Re-launch
             self.context = self.playwright.chromium.launch_persistent_context(
                self.user_data_dir, headless=False 
             )
             self.page = self.context.pages[0]

    def goto(self, url):
        """Navigates to a URL and handles basic popups."""
        self.ensure_active()
        if not url.startswith("http"):
            url = "https://" + url
        print(f"[WEB] Navigating to: {url}")
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle") # Wait for stability
        self.handle_popups()

    def handle_popups(self):
        """Attempts to click common cookie/consent buttons."""
        print("[WEB] Checking for popups...")
        # Common selectors for cookie banners
        # Common selectors for cookie banners
        candidates = [
            "text=Accept all",
            "text=Accept All",
            "text=I agree",
            "text=Agree",
            "text=Allow all",
            "text=Allow selection",
            "button[id*='cookie']",
            "button[class*='cookie']",
            "[aria-label='Accept all']",
            "[aria-label='Accept the use of cookies and other data for the purposes described']", # YouTube/Google
            "button:has-text('Accept all')",
            "button:has-text('Reject all')", # Sometimes reject is faster/safer
            "yt-button-shape:has-text('Accept all')", # YouTube Material
        ]
        
        for sel in candidates:
            try:
                # Use a short timeout so we don't block if no popup
                if self.page.locator(sel).count() > 0:
                     btn = self.page.locator(sel).first
                     if btn.is_visible():
                         print(f"[WEB] Smashing Popup: '{sel}'")
                         btn.click()
                         time.sleep(1)
                         return True
            except:
                pass
        return False

    def click(self, selector):
        """Clicks an element by CSS selector or text content."""
        print(f"[WEB] Clicking: '{selector}'")
        try:
            # Try specific selector first
            if self.page.locator(selector).count() > 0:
                self.page.locator(selector).first.click()
                return True
            
            # Try text match (Playwright pseudoselector)
            # "text=submit" matches generic text. Use exact=False for fuzzy match.
            if self.page.locator(f"text={selector}").count() > 0:
                self.page.locator(f"text={selector}").first.click()
                return True
                
            return False
        except Exception as e:
            print(f"[WEB] Click Failed: {e}")
            return False

    def type(self, selector, text):
        """Types text into an input field."""
        print(f"[WEB] Typing '{text}' into '{selector}'")
        try:
            target = None
            
            # 1. If it's a specific CSS selector, use it
            if self.page.locator(selector).count() > 0:
                target = self.page.locator(selector).first
            
            # 2. Heuristics for generic 'search' request
            elif selector.lower() in ["search", "input", "box"]:
                # Try common search inputs in order of likelihood
                candidates = [
                    "input[name='q']",       # Google
                    "input[type='search']",  # Standard HTML5
                    "input[name='search_query']", # YouTube specific
                    "input[aria-label='Search']", # Accessibility (Specific to INPUT)
                    "textarea[name='q']",    # New Google
                    "[aria-label='Search']", # Generic (Fallback - Risky)
                    "[aria-label='Suche']",  # German
                    "input",                 # Last resort
                    "textarea"
                ]
                for c in candidates:
                    loc = self.page.locator(c)
                    if loc.count() > 0:
                        el = loc.first
                        if el.is_visible() and el.is_editable(): # Check editable!
                            target = el
                            print(f"   > Auto-detected input: {c}")
                            break

            if target:
                target.fill(text)
                return True
            else:
                print(f"[WEB] Error: Could not find input for '{selector}'")
                return False

        except Exception as e:
            print(f"[WEB] Type Failed: {e}")
            return False
            
    def press(self, key):
        """Presses a key (e.g., 'Enter')."""
        print(f"[WEB] Pressing: {key}")
        self.page.keyboard.press(key)

    def close(self):
        self.browser.close()
        self.playwright.stop()

if __name__ == "__main__":
    # Test
    bot = WebSense(headless=False)
    bot.goto("www.google.com")
    # Handle cookie popup (Common ones)
    try:
        bot.click("Accept all") 
    except:
        pass
        
    bot.type("search", "Playwright Python")
    bot.press("Enter")
    time.sleep(5)
    bot.close()
