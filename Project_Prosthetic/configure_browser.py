# C.H.E.E.S.E. Browser Configuration Tool
# Launches the Persistent Browser so the user can install extensions/login.

from web_sense import WebSense
import time

def configure():
    print("=== EXOCORTEX BROWSER CONFIGURATION ===")
    print("Launching Persistent Profile...")
    
    bot = WebSense(headless=False)
    bot.goto("https://www.google.com")
    
    print("\n" + "="*50)
    print("BROWSER IS OPEN.")
    print("1. Install 'I Don't Care About Cookies' or 'uBlock Origin'.")
    print("2. Log in to Google/YouTube if desired.")
    print("3. When finished, come back here and press ENTER to save.")
    print("="*50 + "\n")
    
    input("Press ENTER to close the browser and save profile...")
    
    bot.context.close()
    bot.playwright.stop()
    print("Profile Saved.")

if __name__ == "__main__":
    configure()
