"""
recall.py — Exocortex Memory Retrieval CLI
Command-line interface for the Qdrant memory system.

Usage:
    python recall.py "What is the Athena protocol?"
    python recall.py "tavern description" --limit 3
"""

import sys
import argparse
from memory_engine import MemoryEngine

def main():
    # Force UTF-8 for Windows consoles
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="Recall memories from Exocortex.")
    parser.add_argument("query", type=str, help="The search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    parser.add_argument("--threshold", type=float, default=0.25, help="Similarity threshold (0-1)")
    
    args = parser.parse_args()
    
    try:
        mem = MemoryEngine()
        results = mem.search(
            query=args.query,
            limit=args.limit,
            score_threshold=args.threshold
        )
        
        print(f"\n🧠 **Recall Results for:** *'{args.query}'*\n")
        
        if not results:
            print("> *No matching memories found.*")
            return

        for i, r in enumerate(results, 1):
            content = r['content'].strip().replace('\n', ' ')
            # Truncate if too long for preview
            if len(content) > 300:
                content = content[:297] + "..."
                
            source = r.get('source', 'unknown')
            score = r['score']
            
            print(f"**{i}. [{source}]** `(Score: {score:.2f})`")
            print(f"> {content}\n")
            
    except Exception as e:
        print(f"Error during recall: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
