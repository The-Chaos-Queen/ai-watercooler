from hand_v2 import CyborgHand
from eye_core import ProstheticEye, Certainty
import time
import pyautogui
import requests

def run_arena_mission():
    print("=== CYBORG ARTIST: ARENA.AI MISSION ===")
    
    # 1. Initialize Systems
    hand = CyborgHand()
    
    # Auto-detect Vision Model
    try:
        model_id = requests.get("http://localhost:1234/v1/models", timeout=5).json()['data'][0]['id']
        print(f"[VISION] Detected Model: {model_id}")
    except:
        model_id = "qwen2-vl-2b-instruct"
        print(f"[VISION] Defaulting to: {model_id}")

    eye = ProstheticEye(model=model_id)

    # 2. Navigate (Tactile)
    # Try specific browsers in order (User requested Firefox)
    browsers = ["Firefox", "Brave", "Chrome", "Edge"]
    
    window = None
    for b in browsers:
        try:
             w = hand.desktop.window(title_re=f".*{b}.*", found_index=0)
             if w.exists():
                 print(f"[TACTILE] Found Browser: {b}")
                 window = w
                 break 
        except:
             pass
    
    if not window:
        print("FAIL: Please open Firefox!")
        return
    
    window.set_focus()
    pyautogui.hotkey('ctrl', 'l') 
    time.sleep(0.5)
    hand.type_text("https://arena.ai/") 
    pyautogui.press('enter')
    
    print("Waiting for page load (8s)...")
    time.sleep(8)

    # 2b. Anti-Popup Measure (Cookie Crusher)
    print("\n[STEP 1.5] Checking for Cookie Banners...")
    screenshot = pyautogui.screenshot()
    # Look for common accept buttons
    for keyword in ["Accept", "Allow", "Agree", "Consent", "Okay"]:
        target = eye.locate(f"the button labeled '{keyword}' or 'Close'", screenshot)
        if target.certainty != Certainty.FAILED:
            print(f"[VISION] Popup Detected! Clicking '{keyword}'... ({target.x}, {target.y})")
            pyautogui.moveTo(target.x, target.y, duration=0.5)
            pyautogui.click()
            time.sleep(2)
            screenshot = pyautogui.screenshot() # Refresh view
            break

    # 3. Vision Strategy: Ensure Clean State
    print("\n[STEP 2] Inspecting UI...")
    screenshot = pyautogui.screenshot()
    
    # Try 1: Look for 'Generate Images' directly
    # Try 2: Look for 'New Chat' (Top Left) to reset, then 'Generate Images'
    
    target_k = eye.locate("the 'New Chat' button (usually top left pencil/plus icon)", screenshot)
    if target_k.certainty != Certainty.FAILED:
        print(f"[VISION] Clicking 'New Chat' to reset... ({target_k.x}, {target_k.y})")
        pyautogui.moveTo(target_k.x, target_k.y, duration=0.5)
        pyautogui.click()
        time.sleep(3)
        screenshot = pyautogui.screenshot() # Refresh view
        
    print("Looking for 'Generate Images' mode...")
    target = eye.locate("the button labeled 'Generate Images'", screenshot)
    
    if target.certainty == Certainty.FAILED:
        print("Vision failed to see 'Generate Images'. Trying text input directly...")
    else:
        print(f"[VISION] Switching to Image Mode: {target.x}, {target.y}")
        pyautogui.moveTo(target.x, target.y, duration=1.0)
        pyautogui.click()
        time.sleep(2)

    # 4. Vision Step B: Input Box
    print("\n[STEP 3] Looking for Input Box...")
    screenshot = pyautogui.screenshot()
    target = eye.locate("the text input box that says 'Ask anything'", screenshot)
    
    if target.certainty == Certainty.FAILED:
        print("FAIL: Could not find the input box. Aborting.")
        # Fallback: maybe just type blindly if we clicked something?
        # No, too risky.
        return

    print(f"[VISION] Acquired Input: {target.x}, {target.y}")
    pyautogui.moveTo(target.x, target.y, duration=1.0)
    pyautogui.click()
    time.sleep(0.5)
    
    # 5. Type Prompt
    prompt = "A futuristic cyberpunk squirrel eating a glowing microchip, digital art"
    print(f"\n[STEP 4] Typing Surprise: '{prompt}'")
    hand.type_text(prompt)
    time.sleep(1)
    
    # 6. Execute
    print("[STEP 5] Launching...")
    pyautogui.press('enter')
    print("MISSION COMPLETE.")

if __name__ == "__main__":
    run_arena_mission()
