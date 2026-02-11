from hand_v2 import CyborgHand
import time
import pyautogui

def run_browser_mission():
    print("=== CYBORG EXPLORER (BROWSER) ===")
    
    hand = CyborgHand()
    
    # 1. Connect
    print("\n[STEP 1] Looking for Browser...")
    # Try specific browsers in order
    browsers = ["Chrome", "Edge", "Firefox", "Brave"]
    window = None
    
    for b in browsers:
        try:
             w = hand.desktop.window(title_re=f".*{b}.*", found_index=0) # Take the FIRST match
             if w.exists():
                 print(f"[TACTILE] Found Browser: {b}")
                 window = w
                 break 
        except:
             pass
    
    if not window:
        print("FAIL: Please open a web browser first!")
        return

    window.set_focus()
    time.sleep(1)

    # 2. Navigate (Tactile: Address Bar)
    print("\n[STEP 2] Navigating to Google...")
    
    # CTRL+L or ALT+D usually focus address bar
    pyautogui.hotkey('ctrl', 'l') 
    time.sleep(0.5)
    
    hand.type_text("www.google.com")
    pyautogui.press('enter')
    
    # Wait for page load (Ideally check visually, but we'll just wait)
    print("Waiting for page load (2s)...")
    time.sleep(2)
    
    # 3. Search (Tactile: Address Bar)
    print("\n[STEP 3] Searching via Omnibox (Bypassing Popups)...")
    
    # Use the Address Bar directly for search (Universal Browser Feature)
    pyautogui.hotkey('ctrl', 'l') 
    time.sleep(0.5)
    
    hand.type_text("Acme Labs search")
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("\n[STEP 4] Mission Complete: Acme Labs Searched.")

if __name__ == "__main__":
    run_browser_mission()
