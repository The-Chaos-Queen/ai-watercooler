import pyautogui
from hand_v2 import CyborgHand
import os

def archive_art():
    print("=== ARCHIVING FIRST ARTWORK ===")
    hand = CyborgHand()
    
    # 1. Connect
    print("Looking for Paint...")
    window = hand.connect_app(title_regex=".*Paint.*")
    if not window:
        print("FAIL: Please keep Paint open!")
        return
        
    # 2. Focus & Capture
    window.set_focus()
    rect = window.rectangle()
    
    screenshot = pyautogui.screenshot(region=(rect.left, rect.top, rect.width(), rect.height()))
    
    # 3. Save
    save_path = r"C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\gallery\001_first_smiley.png"
    screenshot.save(save_path)
    print(f"SUCCESS: Masterpiece saved to: {save_path}")

if __name__ == "__main__":
    archive_art()
