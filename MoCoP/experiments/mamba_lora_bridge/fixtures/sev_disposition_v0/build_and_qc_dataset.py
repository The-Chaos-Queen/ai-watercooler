import json
import os
import re

BLOCKLIST_PATH = "blocklist.txt"
OUTPUT_PATH = "sev_disposition_v0.jsonl"
DATA_FILES = ["data_craft.json", "data_family.json", "data_weather.json", "data_food.json", 
              "data_travel.json", "data_illness.json", "data_conflict.json", "data_discovery.json"]

def load_blocklist():
    with open(BLOCKLIST_PATH, 'r', encoding='utf-8') as f:
        words = [line.strip().lower() for line in f if line.strip()]
    return set(words)

def check_blocklist(text, blocklist):
    # tokenize by removing punctuation
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    words = set(clean_text.split())
    hits = words.intersection(blocklist)
    return hits

def check_lengths(variants):
    lengths = {k: len(v.split()) for k, v in variants.items()}
    max_len = max(lengths.values())
    min_len = min(lengths.values())
    if max_len == 0: return False
    return (max_len - min_len) / max_len <= 0.20 # +-10% from mean is roughly 20% max diff

def main():
    blocklist = load_blocklist()
    all_items = []
    
    for df in DATA_FILES:
        if not os.path.exists(df):
            print(f"Skipping {df} (not found)")
            continue
        with open(df, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data:
            skel_id = item["skeleton_id"]
            topic = item["topic"]
            base_text = item["base_text"]
            variants = item["variants"]
            
            # Check length match
            full_texts = {k: base_text + " " + v for k, v in variants.items()}
            if not check_lengths(full_texts):
                print(f"Length mismatch in skeleton {skel_id}")
                for k, v in full_texts.items():
                    print(f"  {k}: {len(v.split())} words")
                # return # strict exit
            
            for v_class, v_text in variants.items():
                full_text = base_text + " " + v_text
                hits = check_blocklist(full_text, blocklist)
                if hits:
                    print(f"Blocklist hit in {skel_id} ({v_class}): {hits}")
                    # return # strict exit
                
                # Append to final list
                all_items.append({
                    "id": f"{skel_id}_{v_class}",
                    "skeleton_id": skel_id,
                    "class": v_class,
                    "topic": topic,
                    "text": full_text,
                    "notes": ""
                })
                
    # Dedup check
    seen = set()
    for item in all_items:
        if item["text"] in seen:
            print(f"Duplicate found: {item['text']}")
        seen.add(item["text"])
        
    if len(all_items) < 160:
        print(f"Warning: Only {len(all_items)} items generated (expected 160).")
        
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")
            
    print(f"Successfully wrote {len(all_items)} items to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
