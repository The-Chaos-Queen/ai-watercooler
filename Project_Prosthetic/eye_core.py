"""
eye_core.py — The Prosthetic Eye
Hybrid perception: VLM for semantics, OpenCV for precision.
"""
import base64
import io
import json
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
import requests
from PIL import Image

class Certainty(Enum):
    PRECISE = auto()      # OpenCV template match > threshold
    APPROXIMATE = auto()  # VLM gave region/description
    EXPLORATORY = auto()  # Grid search fallback
    FAILED = auto()       # No target found

@dataclass
class VisualTarget:
    x: int
    y: int
    certainty: Certainty
    confidence: float
    source: str
    description: str

class VisualLibrary:
    """Persistent storage of learned UI element signatures."""
    def __init__(self, db_path: str = "visual_memory.db"):
        self.db_path = db_path
        self._init_db()
        self._template_cache = {}

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS elements (
                    id INTEGER PRIMARY KEY,
                    semantic_name TEXT UNIQUE,
                    template_path TEXT,
                    roi_x INTEGER, roi_y INTEGER, roi_w INTEGER, roi_h INTEGER,
                    last_used TIMESTAMP
                )
            """)

    def recall(self, semantic_name: str) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT template_path, roi_x, roi_y, roi_w, roi_h FROM elements WHERE semantic_name = ?",
                (semantic_name,)
            ).fetchone()
        
        if not row: return None
        template_path, x, y, w, h = row
        
        if semantic_name not in self._template_cache:
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None: return None
            self._template_cache[semantic_name] = template
            
        return self._template_cache[semantic_name], (x, y, w, h)

    def memorize(self, semantic_name: str, screenshot: Image.Image, bbox: Tuple[int, int, int, int]):
        """Saves a visual template to disk and database."""
        x, y, w, h = bbox
        
        # Crop the template from the screenshot
        template = screenshot.crop((x, y, x+w, y+h))
        
        # Ensure templates directory exists
        base_dir = Path(__file__).parent / "visual_memory" / "templates"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Save image file
        safe_name = "".join([c for c in semantic_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(" ", "_").lower()
        template_filename = f"{safe_name}.png"
        template_path = base_dir / template_filename
        template.save(template_path)
        
        # Update Database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO elements 
                (semantic_name, template_path, roi_x, roi_y, roi_w, roi_h, last_used)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (semantic_name, str(template_path), x, y, w, h))
        
        # Update Cache
        if semantic_name in self._template_cache:
            del self._template_cache[semantic_name]
            
        print(f"[MEMORY] Learned: '{semantic_name}' -> {template_filename}")

    def recall(self, semantic_name: str) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """Retrieves a template from memory."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT template_path, roi_x, roi_y, roi_w, roi_h FROM elements WHERE semantic_name = ?",
                (semantic_name,)
            ).fetchone()
        
        if not row: 
            return None
            
        template_path_str, x, y, w, h = row
        
        # Cache Hit Check
        if semantic_name in self._template_cache:
            return self._template_cache[semantic_name], (x, y, w, h)
            
        # Load from disk
        template_path = Path(template_path_str)
        if not template_path.exists():
            print(f"[MEMORY] Error: Template file missing for '{semantic_name}'")
            return None
            
        # CV2 uses BGR, but we load grayscale for matching
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            return None
            
        self._template_cache[semantic_name] = template
        print(f"[MEMORY] Recalled: '{semantic_name}'")
        return template, (x, y, w, h)

class ProstheticEye:
    def __init__(self, vlm_endpoint="http://localhost:1234/v1/chat/completions", model="qwen2-vl-2b-instruct"): # Default to Qwen
        self.endpoint = vlm_endpoint
        self.model = model  # Ensure this matches what user loaded!
        self.library = VisualLibrary()
        self.match_threshold = 0.8

    def _encode_image(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def _query_vlm(self, image: Image.Image, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a UI automation assistant. You strictly output JSON. No thinking, no explanations."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self._encode_image(image)}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=120)
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"VLM Error: {e}")
            return ""

    def locate(self, description: str, screenshot: Image.Image) -> VisualTarget:
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray_screen = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)

        # 1. Muscle Memory
        memory = self.library.recall(description)
        if memory:
            template, roi = memory
            res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= self.match_threshold:
                h, w = template.shape
                cx, cy = max_loc[0] + w//2, max_loc[1] + h//2
                return VisualTarget(cx, cy, Certainty.PRECISE, max_val, "memory", description)

        # 2. VLM Semantic Query
        print(f"Querying VLM for '{description}'...")
        prompt = f"Identify the screen coordinates of the UI element described as '{description}'. Return ONLY a JSON object with keys: x (center), y (center), confidence (0-1)."
        response = self._query_vlm(screenshot, prompt)
        print(f"DEBUG RAW VLM RESPONSE: {response}")

        # Robust Parsing
        import re
        try:
            # Find the FIRST json object in the string
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
                data = json.loads(clean_json)
                return VisualTarget(int(data['x']), int(data['y']), Certainty.APPROXIMATE, float(data.get('confidence', 0.5)), "vlm", description)
            else:
                print(f"No JSON found in response: {response[:100]}...")
                return VisualTarget(0, 0, Certainty.FAILED, 0.0, "vlm_parse_error", description)
        except Exception as e:
            print(f"Parser Error: {e}")
            return VisualTarget(0, 0, Certainty.FAILED, 0.0, "vlm_error", description)

