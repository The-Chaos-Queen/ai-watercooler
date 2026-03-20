"""
recall.py — Exocortex Memory Retrieval CLI
Command-line interface for the Qdrant memory system.

Usage:
    python recall.py "What is the Athena protocol?"
    python recall.py "tavern description" --limit 3
    python recall.py "old watercooler sqlite path" --type codex_session --type chat_history --limit 8
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
    parser.add_argument("--type", dest="types", action="append", default=[], help="Filter by source type. Repeatable.")
    parser.add_argument("--tag", dest="tags", action="append", default=[], help="Filter by tag. Repeatable.")
    parser.add_argument("--source-contains", type=str, default="", help="Case-insensitive substring filter for source metadata.")
    
    args = parser.parse_args()
    
    try:
        mem = MemoryEngine()
        results = mem.search(
            query=args.query,
            limit=args.limit,
            score_threshold=args.threshold,
            filter_types=args.types,
            tags_any=args.tags,
            source_contains=args.source_contains or None,
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
            source_path = r.get('source_path', '')
            score = r['score']
            source_type = r.get('source_type', 'unknown')
            trust_level = r.get('trust_level', '')
            project = r.get('project', '')
            thread_name = r.get('thread_name', '')
            tags = r.get('tags', [])

            meta_bits = [source_type]
            if trust_level:
                meta_bits.append(trust_level)
            if project:
                meta_bits.append(project)
            meta_label = " | ".join(meta_bits)

            print(f"**{i}. [{source}]** `{meta_label}` `(Score: {score:.2f})`")
            if thread_name:
                print(f"   Thread: `{thread_name}`")
            if source_path:
                print(f"   Path: `{source_path}`")
            if tags:
                print(f"   Tags: `{', '.join(tags)}`")
            print(f"> {content}\n")
            
    except Exception as e:
        print(f"Error during recall: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
