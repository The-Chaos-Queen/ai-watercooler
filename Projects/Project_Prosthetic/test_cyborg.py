from hand_v2 import CyborgHand
import time

def run_cyborg_test():
    print("=== CYBORG HAND TEST (CALCULATOR) ===")
    
    # Initialize Hand
    hand = CyborgHand()
    
    # 1. Connect (Tactile Sense)
    print("\n[STEP 1] Connecting to Calculator...")
    app_window = hand.connect_app(title_regex="Calculator")
    
    if not app_window:
        print("FAIL: Please open Windows Calculator first!")
        return

    # 2. Perform Actions (Motor Functions)
    print("\n[STEP 2] Executing Sequence: 7 + 7 =")
    time.sleep(1)
    
    # Note: Modern calc buttons have names like "Seven", "Plus", "Equals"
    sequences = [
        ("Seven", "Button"),
        ("Plus", "Button"),
        ("Seven", "Button"),
        ("Equals", "Button")
    ]
    
    for name, ctype in sequences:
        hand.click_element(app_window, element_name=name, control_type=ctype)
        time.sleep(0.5)

    print("\n[STEP 3] Test Complete.")

if __name__ == "__main__":
    run_cyborg_test()
