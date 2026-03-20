import pyautogui
from PIL import Image

def check_scaling():
    # 1. Logical Size (What PyAutoGUI thinks the screen is)
    logical_w, logical_h = pyautogui.size()
    
    # 2. Physical Size (What the screenshot actually is)
    screenshot = pyautogui.screenshot()
    physical_w, physical_h = screenshot.size
    
    scale_x = physical_w / logical_w
    scale_y = physical_h / logical_h
    
    print(f"Logical Size (PyAutoGUI): {logical_w}x{logical_h}")
    print(f"Physical Size (Screenshot): {physical_w}x{physical_h}")
    print(f"Calculated Scale Factor: {scale_x:.2f}, {scale_y:.2f}")
    
    if scale_x != 1.0 or scale_y != 1.0:
        print("\nMISMATCH DETECTED!")
        print("The VLM sees 'Physical' pixels, but PyAutoGUI moves in 'Logical' points.")
        print("Fix: We must divide VLM coordinates by the Scale Factor.")

if __name__ == "__main__":
    check_scaling()
