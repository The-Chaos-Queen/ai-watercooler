#!/usr/bin/env python3
"""
Birdwatcher - a cozy nature cam powered by Qwen-0.8B-VL via Ollama.
Snaps a webcam frame, sends it to the vision model, prints what's going on.

Usage:
    python birdwatcher.py                  # single snapshot
    python birdwatcher.py --loop 120       # snap every 120 seconds
    python birdwatcher.py --cam 1          # use second webcam
    python birdwatcher.py --save           # also save snapshots to disk
"""
import argparse
import base64
import time
import sys
import os
from datetime import datetime

import cv2
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5vl:0.5b"  # tiny, basically free

PROMPT = (
    "You are a cozy birdwatcher. Describe what you see in this webcam image "
    "in 1-2 short sentences. Focus on any birds, animals, or interesting "
    "nature activity. If nothing is happening, describe the vibe. "
    "Be warm and casual."
)

SNAP_DIR = os.path.join(os.path.dirname(__file__), "birdwatch_snaps")


def capture_frame(cam_index=0):
    """Grab a single frame from webcam, return as JPEG bytes."""
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"Could not open camera {cam_index}")
        sys.exit(1)
    # let the camera auto-expose for a moment
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Failed to capture frame")
        sys.exit(1)
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes(), frame


def describe(image_bytes):
    """Send image to Qwen via Ollama and get a description."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [b64],
            }
        ],
        "stream": False,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except requests.ConnectionError:
        return "(Ollama not running - start it with 'ollama serve')"
    except Exception as e:
        return f"(error: {e})"


def run_once(cam_index=0, save=False):
    """Snap, describe, print."""
    image_bytes, frame = capture_frame(cam_index)
    now = datetime.now().strftime("%H:%M:%S")

    if save:
        os.makedirs(SNAP_DIR, exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
        cv2.imwrite(os.path.join(SNAP_DIR, fname), frame)

    desc = describe(image_bytes)
    print(f"[{now}] {desc}")
    return desc


def main():
    parser = argparse.ArgumentParser(description="Cozy birdwatcher")
    parser.add_argument("--cam", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--loop", type=int, default=0, help="Seconds between snaps (0 = single shot)")
    parser.add_argument("--save", action="store_true", help="Save snapshots to disk")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Birdwatcher active - snapping every {args.loop}s (Ctrl+C to stop)")
        print()
        try:
            while True:
                run_once(args.cam, args.save)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nBirdwatcher signing off. The birds say bye!")
    else:
        run_once(args.cam, args.save)


if __name__ == "__main__":
    main()
