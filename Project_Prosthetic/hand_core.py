import pyautogui
import time
import keyboard
import sys
import threading

class ProstheticHand:
    def __init__(self):
        # 1. HARDWARE SAFETY: PyAutoGUI Fail-Safe
        # Slamming mouse to (0,0) aborts everything
        pyautogui.FAILSAFE = True
        
        # 2. SPEED LIMITER
        # Add a delay after every PyAutoGUI call
        pyautogui.PAUSE = 0.5 

        self.abort_flag = False
        self._start_kill_switch_listener()
        
        print("=== PROSTHETIC HAND INITIALIZED ===")
        print("SAFETY PROTOCOLS ACTIVE:")
        print("1. MOUSE SLAM: Top-Left Corner (0,0)")
        print("2. KEYBOARD KILL: Hold 'ESC'")

    def _start_kill_switch_listener(self):
        """Background thread to listen for ESC key."""
        def check_kill_switch():
            while not self.abort_flag:
                if keyboard.is_pressed('esc'):
                    print("\n!!! KILL SWITCH TRIGGERED (ESC) !!!")
                    self.emergency_stop()
                time.sleep(0.1)
        
        t = threading.Thread(target=check_kill_switch, daemon=True)
        t.start()

    def emergency_stop(self):
        """Immediate cessation of all motor functions."""
        self.abort_flag = True
        # Force exit
        print("Creating emergency dump...")
        sys.exit(1)

    def move_to(self, x, y, duration=1.0):
        """Safe movement wrapper."""
        if self.abort_flag: return
        
        try:
            print(f"Moving to ({x}, {y})...")
            pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
        except pyautogui.FailSafeException:
            print("\n!!! FAIL-SAFE TRIGGERED (Mouse Slam) !!!")
            self.emergency_stop()

    def wiggle_test(self):
        """Phase 1 Calibration Routine."""
        print("Starting Wiggle Test in 3 seconds...")
        print("KEEP HAND NEAR MOUSE.")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        # Get start position
        start_x, start_y = pyautogui.position()
        print(f"Origin: {start_x}, {start_y}")

        offset = 100
        
        # Square Pattern
        moves = [
            (start_x + offset, start_y),       # Right
            (start_x + offset, start_y + offset), # Down
            (start_x, start_y + offset),       # Left
            (start_x, start_y)                 # Up (Home)
        ]

        for target_x, target_y in moves:
            if self.abort_flag: break
            self.move_to(target_x, target_y)

        print("Wiggle Test Complete. No casualties.")

if __name__ == "__main__":
    hand = ProstheticHand()
    hand.wiggle_test()
