import math
import time
import pyautogui
from hand_v2 import CyborgHand

def draw_circle(center_x, center_y, radius, steps=50):
    """Draws a circle using mouse drags."""
    # Move to start
    start_x = center_x + radius # 0 degrees
    start_y = center_y
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown()
    
    for i in range(steps + 1):
        angle = (2 * math.pi * i) / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        pyautogui.dragTo(x, y, duration=0.01) # fast strokes
    
    pyautogui.mouseUp()

def draw_arc(center_x, center_y, radius, start_angle, end_angle, steps=30):
    """Draws an arc (for the smile)."""
    # Convert angles to radians
    start_rad = math.radians(start_angle)
    
    # Move to start
    start_x = center_x + radius * math.cos(start_rad)
    start_y = center_y + radius * math.sin(start_rad)
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown()
    
    for i in range(steps + 1):
        # Interpolate angle
        t = i / steps
        angle_deg = start_angle + t * (end_angle - start_angle)
        angle_rad = math.radians(angle_deg)
        
        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)
        pyautogui.dragTo(x, y, duration=0.02)
        
    pyautogui.mouseUp()

def run_paint_test():
    print("=== CYBORG ARTIST TEST (PAINT) ===")
    hand = CyborgHand()
    
    # 1. Connect to Paint
    print("\n[STEP 1] Looking for Paint...")
    # Matches "Untitled - Paint" or just "Paint"
    window = hand.connect_app(title_regex=".*Paint.*")
    
    if not window:
        print("FAIL: Please open MS Paint (mspaint)!")
        return

    # 2. Get Canvas Geometry (Proprioception)
    window.set_focus()
    rect = window.rectangle()
    print(f"\n[SENSE] Canvas detected at: {rect}")
    
    # Calculate relative center of the window (drawing area is usually central)
    # We'll aim for the middle of the app window
    cx = rect.mid_point().x
    cy = rect.mid_point().y
    
    # Tool Selection (Optional: Reset to pencil/brush if we could, but assuming default)
    # Just verify we are active
    time.sleep(1) 
    
    print("\n[STEP 2] Commencing Artistry...")
    
    # Head
    print(" - Drawing Head...")
    draw_circle(cx, cy, radius=100)
    
    # Left Eye
    print(" - Drawing Left Eye...")
    draw_circle(cx - 35, cy - 30, radius=10, steps=10)
    
    # Right Eye
    print(" - Drawing Right Eye...")
    draw_circle(cx + 35, cy - 30, radius=10, steps=10)
    
    # Smile (45 to 135 degrees is a frown, 225 to 315 is a smile? No, standard math:
    # 0 is right, 90 is down (screen coords), 180 is left, 270 is up.
    # Smile is bottom half: roughly 45 to 135 degrees.
    print(" - Drawing Smile...")
    draw_arc(cx, cy - 10, radius=60, start_angle=45, end_angle=135)
    
    print("\n[STEP 3] Masterpiece Complete.")

if __name__ == "__main__":
    run_paint_test()
