#!/usr/bin/env python3
"""Convert saved .mht / .html chat pages to readable plaintext.

Made for the html-to-convert/ folder (saved LMArena battles, claude.ai pages
etc.). Stdlib only. Handles MIME multipart (.mht) with quoted-printable or
base64 parts, picks the text/html payload, strips tags/scripts/styles,
collapses whitespace, and writes <input>_text.txt next to the source.

Usage:
  python tools/mht_to_text.py "html-to-convert/Arena ... (17).mht"
  python tools/mht_to_text.py html-to-convert            # whole folder
"""
import email
import email.policy
import html as html_lib
import io
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "template"}
BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5",
              "h6", "section", "article", "blockquote", "pre"}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = io.StringIO()
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            self.out.write("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self.out.write("\n")

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.out.write(data)


def html_part_from_mht(path: Path) -> str:
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    best = None
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True) or b""
            if best is None or len(payload) > len(best):
                best = payload
    if best is None:
        raise ValueError(f"no text/html part found in {path.name}")
    for enc in ("utf-8", "windows-1252", "latin-1"):
        try:
            return best.decode(enc)
        except UnicodeDecodeError:
            continue
    return best.decode("utf-8", errors="replace")


def to_text(html_doc: str) -> str:
    parser = TextExtractor()
    parser.feed(html_doc)
    text = html_lib.unescape(parser.out.getvalue())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip() + "\n"


def convert(path: Path) -> Path:
    if path.suffix.lower() in (".mht", ".mhtml"):
        doc = html_part_from_mht(path)
    else:
        doc = path.read_text(encoding="utf-8", errors="replace")
    out_path = path.with_name(path.stem + "_text.txt")
    out_path.write_text(to_text(doc), encoding="utf-8")
    return out_path


def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows cp1252 console safety
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    target = Path(sys.argv[1])
    files = ([p for p in target.iterdir()
              if p.suffix.lower() in (".mht", ".mhtml", ".html", ".htm")]
             if target.is_dir() else [target])
    for f in files:
        try:
            out = convert(f)
            print(f"ok   {f.name} -> {out.name}")
        except Exception as e:
            print(f"FAIL {f.name}: {e}")


if __name__ == "__main__":
    main()
