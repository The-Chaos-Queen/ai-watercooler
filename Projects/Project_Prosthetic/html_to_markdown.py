"""
html_to_markdown.py — Convert saved AI chat HTML files to clean Markdown.
Supports: Claude, Gemini, Kimi, Grok, DeepSeek, Mistral, LMArena.

Usage:
    python html_to_markdown.py chat.html                    # Convert single file
    python html_to_markdown.py folder/                       # Convert all .html files in folder
    python html_to_markdown.py chat.html -o output.md        # Specify output path
    python html_to_markdown.py folder/ --ingest              # Convert AND ingest into Qdrant
"""

import sys
import re
import email
from email import policy
import argparse
from pathlib import Path
from datetime import datetime

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)


# Platform detection and selectors (mirrors content.js logic)
PLATFORMS = {
    "claude": {
        "name": "Claude",
        "detect": ["claude.ai"],
        "user_selector": [".font-user-message", "[class*='font-user']"],
        "assistant_selector": [".font-claude-response", "[class*='font-claude']"],
        "content_selector": ".standard-markdown",
        "assistant_name": "Claude",
    },
    "gemini": {
        "name": "Gemini",
        "detect": ["gemini.google.com"],
        "user_selector": ["[class*='query-container']", "user-query"],
        "assistant_selector": ["[class*='response-container']", "model-response"],
        "content_selector": ".markdown",
        "assistant_name": "Gemini",
    },
    "kimi": {
        "name": "Kimi",
        "detect": ["kimi.moonshot.cn", "kimi.com"],
        "user_selector": [".chat-content-item-user"],
        "assistant_selector": [".chat-content-item-assistant"],
        "content_selector": None,
        "assistant_name": "Kimi",
    },
    "grok": {
        "name": "Grok",
        "detect": ["grok.com"],
        "user_selector": [".items-end .message-bubble"],
        "assistant_selector": [".items-start .message-bubble"],
        "content_selector": None,
        "assistant_name": "Grok",
    },
    "deepseek": {
        "name": "DeepSeek",
        "detect": ["chat.deepseek.com"],
        "user_selector": [".ds-message:nth-child(2)"],
        "assistant_selector": [".ds-message:nth-child(3)"],
        "content_selector": None,
        "assistant_name": "DeepSeek",
    },
    "mistral": {
        "name": "Mistral",
        "detect": ["chat.mistral.ai"],
        "user_selector": ['[data-message-author-role="user"]'],
        "assistant_selector": ['[data-message-author-role="assistant"]'],
        "content_selector": None,
        "assistant_name": "Mistral",
    },
    "lmarena": {
        "name": "LMArena",
        "detect": ["lmsys.org", "arena.ai", "battle"],
        "user_selector": [".bg-surface-raised", ".bg-interactive-cta-secondary-active"],
        "assistant_selector": [".bg-surface-primary", ".bg-surface-secondary"],
        "content_selector": ".prose",
        "assistant_name": "LMArena",
    },
}


def detect_platform(soup: BeautifulSoup) -> dict | None:
    """Detect which AI platform the HTML came from."""
    html_str = str(soup)[:5000].lower()

    for key, config in PLATFORMS.items():
        for marker in config["detect"]:
            if marker in html_str:
                return config

    # Fallback: try to detect by CSS classes in the body
    body = soup.find("body")
    if not body:
        return None

    body_str = str(body)[:10000]
    for key, config in PLATFORMS.items():
        for sel in config["user_selector"] + config["assistant_selector"]:
            # Strip CSS selector syntax for simple class check
            clean = sel.strip(".").split(":")[0].split("[")[0].split(" ")[0]
            if clean and clean in body_str:
                return config

    return None


def element_to_markdown(element) -> str:
    """Convert an HTML element to Markdown, handling common patterns."""
    if element is None:
        return ""

    parts = []

    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                parts.append(text)
            continue

        tag = child.name
        if not tag:
            continue

        # Code blocks
        if tag == "pre" or (hasattr(child, "get") and "code-block" in child.get("class", [])):
            code = child.get_text()
            # Try to detect language from class
            lang = ""
            code_el = child.find("code")
            if code_el and code_el.get("class"):
                for cls in code_el["class"]:
                    if cls.startswith("language-"):
                        lang = cls.replace("language-", "")
            parts.append(f"\n```{lang}\n{code.strip()}\n```\n")
            continue

        # Thinking blocks (Claude <details> or similar)
        if tag == "details":
            thinking_content = element_to_markdown(child)
            summary_el = child.find("summary")
            label = summary_el.get_text().strip() if summary_el else "Thinking"
            parts.append(f"\n<details>\n<summary>{label}</summary>\n\n{thinking_content.strip()}\n\n</details>\n\n")
            continue

        # Recurse for content
        content = element_to_markdown(child)

        if tag == "p":
            parts.append(f"\n{content}\n")
        elif tag == "br":
            parts.append("\n")
        elif tag in ("strong", "b"):
            parts.append(f"**{content.strip()}**")
        elif tag in ("em", "i"):
            parts.append(f"*{content.strip()}*")
        elif tag == "code":
            parts.append(f"`{child.get_text()}`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            # Offset by 2 since h1/h2 are used for role headers
            parts.append(f"\n{'#' * (level + 1)} {content.strip()}\n")
        elif tag == "ul":
            for li in child.find_all("li", recursive=False):
                li_content = element_to_markdown(li).strip()
                parts.append(f"- {li_content}\n")
            parts.append("")
        elif tag == "ol":
            for idx, li in enumerate(child.find_all("li", recursive=False), 1):
                li_content = element_to_markdown(li).strip()
                parts.append(f"{idx}. {li_content}\n")
            parts.append("")
        elif tag == "a":
            href = child.get("href", "")
            parts.append(f"[{content.strip()}]({href})")
        elif tag == "blockquote":
            for line in content.strip().split("\n"):
                parts.append(f"> {line}\n")
        elif tag in ("div", "span", "section", "article"):
            parts.append(content)
        else:
            parts.append(content)

    return "".join(parts)


def find_elements(soup, selectors):
    """Try multiple CSS selectors and return the first set that finds results."""
    for sel in selectors:
        try:
            found = soup.select(sel)
            if found:
                return found
        except Exception:
            continue
    return []


def extract_thinking_text(el, prose_el):
    """Extract thinking/reasoning text from an LMArena message element.
    
    The thinking content is the text between the model header and the .prose response.
    We extract the full text, remove the prose text and model headers, and what remains
    is the thinking trace.
    """
    import re

    full_text = el.get_text(separator="\n")
    prose_text = prose_el.get_text(separator="\n") if prose_el else ""

    # If we don't have a prose element, only treat this as thinking if it has a thinking indicator
    if not prose_el:
        if not any(kw in full_text.lower() for kw in ["thought for", "thinking...", "reasoning"]):
            return "", ""
        thinking_raw = full_text
    else:
        # Remove the prose (response) text from full text to isolate thinking
        idx = full_text.find(prose_text[:100])
        if idx > -1:
            thinking_raw = full_text[:idx]
        else:
            thinking_raw = ""

    # Clean out model headers like "Anthropic claude-opus-4-5..." and "Thought for X seconds"
    lines = thinking_raw.split("\n")
    clean_lines = []
    thought_duration = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip model identification lines
        if any(kw in stripped.lower() for kw in ["anthropic", "claude-opus", "claude-sonnet", "generating...", "direct", "message from"]):
            continue
        # Capture "Thought for X seconds" as metadata
        if re.match(r"Thought for \d+", stripped, re.I):
            thought_duration = stripped
            continue
        clean_lines.append(stripped)

    thinking_text = "\n".join(clean_lines).strip()
    return thinking_text, thought_duration


def extract_assistant_label(el, default="Assistant"):
    """Try to find a more specific label for an LMArena assistant message."""
    text = el.get_text()
    
    import re
    # Check for "Model A", "Model B", "Assistant A", "Assistant B"
    for label in ["Model A", "Model B", "Assistant A", "Assistant B"]:
        if label.lower() in text.lower()[:200]:
            return label
            
    # Check for "Message from [Name]"
    m = re.search(r"Message from ([\w\.-]+)", text, re.I)
    if m:
        return m.group(1)
        
    return default


def convert_html_to_markdown(html_content: str) -> str:
    """Convert an AI chat HTML file to clean Markdown."""
    soup = BeautifulSoup(html_content, "html.parser")

    platform = detect_platform(soup)
    platform_name = platform["name"] if platform else "Unknown"

    if not platform:
        # Fallback: generic extraction
        print(f"  [WARN] Could not detect platform. Using generic extraction.")
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            return f"# Chat Export (Unknown Platform)\n\n{text}"
        return "# Chat Export\n\n> Error: Could not extract content."

    print(f"  [INFO] Detected platform: {platform_name}")

    # Use a combined selector to get ALL messages in document order.
    # This preserves the natural DOM ordering instead of sorting.
    user_sels = platform["user_selector"]
    asst_sels = platform["assistant_selector"]
    combined_sel = ", ".join(user_sels + asst_sels)

    try:
        raw_nodes = soup.select(combined_sel)
    except Exception:
        raw_nodes = []

    print(f"  [INFO] Raw nodes found: {len(raw_nodes)}")
    # Deduplicate: if node A contains node B, keep only A.
    # We do this by checking if any ancestor of a node is also in our set of raw nodes.
    # We use id() for fast lookup in a set.
    raw_nodes_ids = {id(n) for n in raw_nodes if n.name not in ("html", "body", "main", "section", "header", "footer")}
    nodes = []
    for n in raw_nodes:
        if n.name in ("html", "body", "main", "section", "header", "footer"):
            continue
        is_nested = False
        current = n.parent
        while current:
            if id(current) in raw_nodes_ids:
                is_nested = True
                break
            current = current.parent
        if not is_nested:
            nodes.append(n)

    print(f"  [INFO] Fast dedup finished. Top-level nodes: {len(nodes)}")

    # LMArena Battle Reversing:
    # LMArena often uses flex-col-reverse to display newest messages at top in HTML
    # and keeps messages in reverse document order.
    if nodes and platform_name == "LMArena":
        is_reverse = False
        # Search deeper for flex-col-reverse
        for n in nodes[:5]:
            curr = n.parent
            depth = 0
            while curr and depth < 15:
                if "flex-col-reverse" in curr.get("class", []):
                    is_reverse = True
                    break
                curr = curr.parent
                depth += 1
            if is_reverse: break
            
        # Fallback: if the first node is Assistant and the last is User, 
        # it's usually reversed in battle mode
        if not is_reverse and len(nodes) > 1:
            first_text = nodes[0].get_text().lower()
            last_text = nodes[-1].get_text().lower()
            if "better" not in first_text and ("model a" in first_text or "assistant a" in first_text):
                is_reverse = True
        
        if is_reverse:
            print("  [INFO] Detected reverse order, reversing nodes for target chronology")
            nodes.reverse()

    print(f"  [INFO] Found {len(nodes)} message elements (after dedup)")
    
    # Classify each node as user or assistant
    print("  [INFO] Classifying nodes...")
    is_lmarena = platform_name == "LMArena"
    all_messages = []

    for i, el in enumerate(nodes):
        if i % 10 == 0:
            print(f"    - Classifying check {i}/{len(nodes)}", end="\r", flush=True)
            
        # Determine role
        role = None
        el_classes = el.get("class", [])
        if isinstance(el_classes, str):
            el_classes = el_classes.split()
            
        # Check if the element itself matches any user selector
        for sel in user_sels:
            clean_sel = sel.strip(".")
            # match by class or by selector
            if clean_sel in el_classes:
                role = "User"
                break
            try:
                if hasattr(el, 'matches') and el.matches(sel):
                    role = "User"
                    break
            except Exception:
                continue
                
        if not role:
            role = platform["assistant_name"]
            
        # For LMArena assistant messages, try to find a more specific label
        if is_lmarena and role != "User":
             # Only look for label if it's the "real" message block
             role = extract_assistant_label(el, default=role)

        # For LMArena: check if this is an actual message or UI chrome
        prose_el = el.select_one(platform["content_selector"]) if platform["content_selector"] else None
        full_text = el.get_text().strip()

        if is_lmarena:
            # Skip UI chrome: assistant elements with no prose and very short text
            if role != "User":
                if not prose_el and len(full_text) < 50:
                    # Skip empty/chrome assistant containers
                    continue
                if len(full_text) < 30 and not prose_el:
                    # Skip model headers/navigation labels
                    continue
            else:
                # For User: only skip if it's genuinely empty
                if not full_text:
                    continue

        all_messages.append((role, el, prose_el))
    
    print(f"\n  [INFO] Classification finished. Messages: {len(all_messages)}")

    if not all_messages:
        return f"# {platform_name} Chat Export\n\n> No messages found."

    # Build markdown
    output = f"# {platform_name} Chat Export\n\n"
    prev_content = None
    thinking_count = 0
    pending_model_name = None

    for i, (role, el, prose_el) in enumerate(all_messages):
        print(f"    [PROGRESS] Processing message {i+1}/{len(all_messages)} ({role})", end="\r", flush=True)
        
        # Extract response content
        content_el = prose_el if prose_el else el
        md_content = element_to_markdown(content_el).strip()
        
        # LMArena Battle Special Handling:
        # If this is a tiny block and contains a model name/label, treat it as a header for next message
        if is_lmarena and role != "User" and not prose_el and len(md_content) < 100:
            if "### Message from" in md_content or "Model A" in md_content or "Model B" in md_content or "Assistant A" in md_content:
                # Extract the name
                import re
                m = re.search(r"Message from ([\w\.-]+)", md_content, re.I)
                if m:
                    pending_model_name = m.group(1)
                elif "Model A" in md_content or "Assistant A" in md_content:
                    pending_model_name = "Model A"
                elif "Model B" in md_content or "Assistant B" in md_content:
                    pending_model_name = "Model B"
                continue # Skip the label block itself

        # Use pending model name if available
        current_role = role
        if pending_model_name and role != "User":
            current_role = pending_model_name
            pending_model_name = None

        # Filter out UI noise for LMArena
        if is_lmarena:
            # Skip voting buttons
            if "better" in md_content.lower() and ("A is better" in md_content or "B is better" in md_content):
                continue
            # Skip "See other response" blocks
            if md_content.startswith("See other response"):
                # But check if there's more content after it
                lines = md_content.split("\n")
                if len(lines) <= 2:
                    continue
                md_content = "\n".join(lines[1:]).strip()

        # Extract thinking blocks for assistant messages
        thinking_md = ""
        if is_lmarena and current_role != "User":
            # In battles, the thinking might be in el but outside prose_el
            thinking_text, thought_duration = extract_thinking_text(el, prose_el)
            if thinking_text:
                thinking_count += 1
                header = f"*{thought_duration}*\n\n" if thought_duration else ""
                thinking_md = f"<details>\n<summary>💭 Thinking</summary>\n\n{header}{thinking_text}\n\n</details>\n\n"

        # Skip empty or duplicate sequential messages
        if not md_content or md_content == prev_content:
            continue

        output += f"## {current_role}\n\n"
        if thinking_md:
            output += thinking_md
        output += f"{md_content}\n\n---\n\n"
        prev_content = md_content

    if thinking_count > 0:
        print(f"\n  [INFO] Extracted {thinking_count} thinking blocks")

    return output


def extract_html_from_mht(mht_path: Path) -> str:
    """Extract the HTML part from an MHT/MHTML archive."""
    raw = mht_path.read_bytes()
    msg = email.message_from_bytes(raw, policy=policy.default)

    # Walk MIME parts, find the text/html one
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        # Fallback: first text part
        for part in msg.walk():
            ct = part.get_content_type()
            if ct.startswith("text/"):
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    return ""


def robust_read(path: Path) -> str:
    """Read file with multiple encoding fallbacks to avoid replacement characters."""
    encodings = ["utf-8", "utf-16", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            content = path.read_text(encoding=enc)
            # Basic sanity check: if it's all replacement chars, it's the wrong encoding
            if content.count("\ufffd") > len(content) * 0.1:
                continue
            return content
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def convert_file(input_path: Path, output_path: Path = None) -> Path:
    """Convert a single HTML or MHT file to Markdown."""
    print(f"\n[CONVERT] {input_path.name}")

    if input_path.suffix.lower() in (".mht", ".mhtml"):
        print("  [INFO] MHT archive detected, extracting HTML...")
        html_content = extract_html_from_mht(input_path)
    else:
        html_content = robust_read(input_path)

    markdown = convert_html_to_markdown(html_content)

    if output_path is None:
        output_path = input_path.with_suffix(".md")

    output_path.write_text(markdown, encoding="utf-8")
    print(f"  [DONE] Saved to {output_path.name} ({len(markdown)} chars)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convert AI chat HTML to Markdown")
    parser.add_argument("input", help="HTML file or directory of HTML files")
    parser.add_argument("-o", "--output", help="Output file path (for single file)")
    parser.add_argument("--ingest", action="store_true", help="Also ingest into Qdrant after conversion")
    args = parser.parse_args()

    input_path = Path(args.input)
    converted_files = []

    if input_path.is_file():
        out = Path(args.output) if args.output else None
        converted_files.append(convert_file(input_path, out))
    elif input_path.is_dir():
        html_files = sorted(input_path.glob("*.html")) + sorted(input_path.glob("*.htm")) + sorted(input_path.glob("*.mht")) + sorted(input_path.glob("*.mhtml"))
        print(f"Found {len(html_files)} HTML/MHT files in {input_path.name}/")
        for f in html_files:
            converted_files.append(convert_file(f))
    else:
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    # Optional: ingest into Qdrant
    if args.ingest and converted_files:
        print("\n[INGEST] Sending to Qdrant...")
        try:
            from ingest_sessions import ingest_file
            from memory_engine import MemoryEngine
            mem = MemoryEngine()
            total = 0
            for f in converted_files:
                total += ingest_file(mem, f)
            print(f"[INGEST] Done. {total} chunks stored.")
        except Exception as e:
            print(f"[INGEST] Error: {e}")

    print(f"\n{'='*40}")
    print(f"Converted {len(converted_files)} files.")


if __name__ == "__main__":
    main()
