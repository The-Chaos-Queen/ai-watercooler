# C.H.E.E.S.E. Paint Demo (The House)
# Bypasses the Cortex to prove Motor Function.

import pyautogui
import time
import math

def draw_house():
    print("=== ANTIGRAVITY PAINT DEMO ===")
    
    # 1. Open Paint
    print("[1] Opening Paint...")
    pyautogui.press('win')
    time.sleep(0.5)
    pyautogui.write('mspaint')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    # Wait for launch
    time.sleep(3.0)
    
    # Ensure window is focused/maximized
    pyautogui.getWindowsWithTitle('Paint')[0].maximize()
    time.sleep(1.0)

    # 2. Get Canvas Center
    w, h = pyautogui.size()
    cx, cy = w // 2, h // 2
    
    print(f"[2] Moving to Canvas Center ({cx}, {cy})...")
    pyautogui.moveTo(cx, cy, duration=0.5)

    # 3. Draw The Box (House Body)
    print("[3] Drawing Walls...")
    side = 200
    pyautogui.drag(side, 0, duration=0.5, button='left')   # Right
    pyautogui.drag(0, side, duration=0.5, button='left')   # Down
    pyautogui.drag(-side, 0, duration=0.5, button='left')  # Left
    pyautogui.drag(0, -side, duration=0.5, button='left')  # Up (Back to start)
    
    # 4. Draw Roof (Triangle)
    print("[4] Drawing Roof...")
    # Move to top-left corner
    # Roof Peak is (cx + side/2, cy - 100)
    
    # Drag to Peak
    pyautogui.drag(side//2, -100, duration=0.5, button='left')
    # Drag to Top-Right Corner
    pyautogui.drag(side//2, 100, duration=0.5, button='left')

    # 5. Draw Door
    print("[5] Drawing Door...")
    # Lift pen, move to door start (bottom middle)
    pyautogui.mouseUp()
    door_w = 60
    door_h = 100
    
    door_x = cx + (side // 2) - (door_w // 2)
    door_y = cy + side
    
    pyautogui.moveTo(door_x, door_y) # Bottom-left of door
    
    pyautogui.drag(0, -door_h, duration=0.5, button='left') # Door Up
    pyautogui.drag(door_w, 0, duration=0.5, button='left')  # Door Top
    # 6. SIGNATURE
    print("[6] Signing the Work...")
    # Assume we are lower down.
    pyautogui.mouseUp()
    pyautogui.move(200, 0) # Move right
    
    # Draw 'H'
    pyautogui.drag(0, 50, duration=0.3, button='left') # |
    pyautogui.move(0, -25)
    pyautogui.drag(30, 0, duration=0.3, button='left') # -
    pyautogui.move(0, -25)
    pyautogui.drag(0, 50, duration=0.3, button='left') # |
    
    # Move
    pyautogui.mouseUp()
    pyautogui.move(20, -50)
    
    # Draw 'I'
    pyautogui.drag(0, 50, duration=0.3, button='left') # |
    
    # Draw Heart <3 (Crude V)
    pyautogui.mouseUp()
    pyautogui.move(30, -50)
    pyautogui.drag(15, 25, duration=0.3, button='left') # \
    pyautogui.drag(15, -25, duration=0.3, button='left') # /
    
    print("=== SECRET MESSAGE DEPLOYED ===")

if __name__ == "__main__":
    try:
        draw_house()
    except Exception as e:
        print(f"Error: {e}")
