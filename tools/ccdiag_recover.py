import argparse
import json
from pathlib import Path

def recover(input_path, output_path, output_format):
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: {input_path} not found.")
        return

    messages = {}
    parent_to_children = {}

    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                uuid = data.get('uuid')
                if uuid:
                    messages[uuid] = data
                    parent_uuid = data.get('parentUuid')
                    if parent_uuid:
                        parent_to_children.setdefault(parent_uuid, []).append(uuid)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON on line {line_num}")

    if not messages:
        print("No valid messages with UUIDs found.")
        return

    print(f"Loaded {len(messages)} messages. Finding leaf nodes...")
    
    # Leaves are nodes that are never a parentUuid
    leaves = [uid for uid in messages if uid not in parent_to_children]

    print(f"Found {len(leaves)} branch leaves (forks). Tracing chains...")

    longest_chain = []
    
    for leaf in leaves:
        chain = []
        curr = leaf
        while curr and curr in messages:
            chain.append(messages[curr])
            curr = messages[curr].get('parentUuid')
        
        if len(chain) > len(longest_chain):
            longest_chain = chain

    # Reverse to get chronological order (root -> leaf)
    longest_chain.reverse()

    print(f"Longest continuous chain found: {len(longest_chain)} messages.")
    
    dropped = len(messages) - len(longest_chain)
    if dropped > 0:
        print(f"Pruned {dropped} orphaned or forked messages (dead ends).")

    if not output_path:
        print("No output file specified. Dry run complete.")
        return

    out_file = Path(output_path)
    if output_format == 'jsonl':
        with open(out_file, 'w', encoding='utf-8') as f:
            for msg in longest_chain:
                f.write(json.dumps(msg) + '\n')
    elif output_format == 'md':
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write("# Claude Code Session Recovery\n\n")
            f.write(f"Recovered {len(longest_chain)} messages.\n\n---\n\n")
            for msg in longest_chain:
                # Try to extract readable info
                msg_type = msg.get('type', 'unknown')
                msg_text = msg.get('text') or msg.get('message') or ""
                
                # Claude Code often stores the prompt/response in 'content' arrays
                if not msg_text and 'content' in msg:
                    if isinstance(msg['content'], str):
                        msg_text = msg['content']
                    elif isinstance(msg['content'], list):
                        texts = [c.get('text', '') for c in msg['content'] if c.get('type') == 'text']
                        msg_text = "\n".join(texts)
                
                f.write(f"### {msg_type.upper()} (UUID: {msg.get('uuid', 'N/A')})\n")
                if msg_text:
                    f.write(f"{msg_text}\n\n")
                else:
                    # Fallback to dump if no readable text is found
                    f.write(f"```json\n{json.dumps(msg, indent=2)}\n```\n\n")
                f.write("---\n\n")

    print(f"Successfully wrote recovered session to {out_file.resolve()}")

def main():
    parser = argparse.ArgumentParser(description="Recover corrupted Claude Code session JSONL files by extracting the longest parentUuid chain.")
    parser.add_argument("input", help="Path to the corrupted session.jsonl file")
    parser.add_argument("-o", "--output", help="Output file path (e.g., recovered.jsonl or recovery.md)")
    parser.add_argument("--format", choices=['jsonl', 'md'], default='jsonl', help="Output format: jsonl (default) or md (markdown readable)")
    
    args = parser.parse_args()
    recover(args.input, args.output, args.format)

if __name__ == "__main__":
    main()
