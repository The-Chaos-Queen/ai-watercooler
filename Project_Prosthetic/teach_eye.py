import pyautogui
from eye_core import ProstheticEye, Certainty
import cv2
import numpy as np
import requests

def teach_eye():
    print("=== CYBORG LEARNING MODE ===")
    
    # Auto-detect model
    try:
        model_id = requests.get("http://localhost:1234/v1/models", timeout=5).json()['data'][0]['id']
    except:
        model_id = "qwen2-vl-2b-instruct"
        
    eye = ProstheticEye(model=model_id)
    
    target_desc = "the 'Minimize' button (usually an underscore _ or dash - icon in top right)"
    
    print(f"\nTarget to Learn: '{target_desc}'")
    print("Please arrange window. Press ENTER to scan...")
    # input() 
    # Use direct execution for now since we are running via agent tools
    
    # 1. Capture
    screenshot = pyautogui.screenshot()
    
    # 2. VLM Locate
    print("Asking VLM for location...")
    target = eye.locate(target_desc, screenshot)
    
    if target.certainty == Certainty.FAILED:
        print("VLM failed to find it. Cannot learn.")
        return

    print(f"VLM Guess: ({target.x}, {target.y})")
    
    # 3. Verify (Simulated for this script, normally we'd show a GUI)
    # We will assume for this test that we want to save a 40x40 box around that center
    # In a real app, I'd pop up a window. 
    # Here I'll just save it and let the user test if it works.
    
    print("Memorizing this location as a template (40x40px)...")
    
    # Create valid bbox
    x, y = target.x - 20, target.y - 20
    bbox = (x, y, 40, 40)
    
    # Memorize
    eye.library.memorize(target_desc, screenshot, bbox)
    print("SUCCESS: Target added to Visual Memory.")
    print("Next time, the Eye should use OpenCV (PRECISE) instead of VLM.")

if __name__ == "__main__":
    teach_eye()
