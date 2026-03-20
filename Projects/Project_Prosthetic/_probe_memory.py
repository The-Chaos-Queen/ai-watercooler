from memory_engine import MemoryEngine
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def probe_exocortex(query: str):
    mem = MemoryEngine()
    print(f"\n[PROBE] Querying: '{query}'")
    results = mem.search(query, limit=5, score_threshold=0.4)
    
    if not results:
        print("  [X] No semantic matches found.")
        return

    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} [Score: {r['score']:.2f} | Source: {r['source']}] ---")
        print(r['content'])
        print("-" * 50)

if __name__ == "__main__":
    # Query for the Latin wisdom discussion
    probe_exocortex("De Sapientia Veterum Latin dialogue with Claude")
