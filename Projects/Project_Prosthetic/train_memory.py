import pyautogui
import requests
import time
from eye_core import ProstheticEye, Certainty
import cv2
import numpy as np

def train_memory_interactive():
    print("=== CYBORG MEMORY TRAINER ===")
    
    # Initialize Eye (Auto-detect model)
    try:
        model_id = requests.get("http://localhost:1234/v1/models", timeout=2).json()['data'][0]['id']
    except:
        model_id = "qwen3-vl-2b-instruct" # Assume Qwen3 if we can't check
    
    eye = ProstheticEye(model=model_id)
    
    while True:
        print("\n" + "="*40)
        target_name = input("Enter name of button to learn (or 'q' to quit): ").strip()
        if target_name.lower() == 'q':
            break
            
        print(f"Please point your mouse at the center of the '{target_name}' button.")
        print("Waiting 5 seconds... get ready!")
        time.sleep(5)
        
        # Get Mouse Position (Ground Truth)
        mouse_x, mouse_y = pyautogui.position()
        print(f"Captured Mouse Position: ({mouse_x}, {mouse_y})")
        
        # Capture Screenshot
        screenshot = pyautogui.screenshot()
        
        # Define Template Size (e.g., 64x64 pixel box around mouse)
        # Verify boundarie
        width, height = screenshot.size
        box_size = 64
        half_box = box_size // 2
        
        x = max(0, mouse_x - half_box)
        y = max(0, mouse_y - half_box)
        
        # Ensure we don't go off screen
        if x + box_size > width: x = width - box_size
        if y + box_size > height: y = height - box_size
        
        bbox = (x, y, box_size, box_size)
        
        # Memorize
        eye.library.memorize(target_name, screenshot, bbox)
        print("SUCCESS: Template Saved.")
        
        # Verify immediately
        print("Verifying Recall...")
        target = eye.locate(target_name, screenshot)
        if target.certainty == Certainty.PRECISE:
            print(f"VERIFIED! Vision System found it at ({target.x}, {target.y}) with confidence {target.confidence:.2f}")
        else:
            print("WARNING: Immediate recall failed. Template might be too generic.")

if __name__ == "__main__":
    train_memory_interactive()
