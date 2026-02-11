import pyautogui
import time
from eye_core import ProstheticEye, Certainty

def calibration_routine():
    print("=== PROSTHETIC EYE CALIBRATION (PHASE 2) ===")
    print("Initializing Vision System (connecting to Qwen)...")
    
    # Auto-detect loaded model
    import requests
    try:
        print("Checking loaded model...")
        model_id = requests.get("http://localhost:1234/v1/models", timeout=5).json()['data'][0]['id']
        print(f"Detected Model: {model_id}")
    except Exception as e:
        print(f"Could not detect model ({e}). Defaulting to 'moondream'.")
        model_id = "moondream"

    eye = ProstheticEye(model=model_id) 
    
    print("\nStarting Calibration...")
    print("Please open a window with clear buttons (e.g., Calculator or Explorer).")
    input("Press ENTER when ready to capture screen...")
    
    screenshot = pyautogui.screenshot()
    print("Screenshot captured. Analyzing...")
    
    # Test Case 1: Something obvious
    target_desc = "the 'Minimize' button (usually an underscore _ or dash - icon in top right)"
    
    target = eye.locate(target_desc, screenshot)
    
    print(f"\nTarget: {target_desc}")
    print(f"Result: {target.certainty.name} at ({target.x}, {target.y})")
    print(f"Source: {target.source}")
    print(f"Confidence: {target.confidence}")
    
    if target.certainty != Certainty.FAILED:
        print("\nMove mouse to target? (Safe check)")
        pyautogui.moveTo(target.x, target.y, duration=1.0)
        print("Mouse moved. Did it land correctly?")

if __name__ == "__main__":
    calibration_routine()
