#!/usr/bin/env python3
"""Machine-deixis scorer v0 — first instrument of the Sleeve Probe.

Scores text files against the marker lexicons from
CHEESE_Memory/03b_MACHINE_DEIXIS_CATALOG.md. Counts per 1,000 words:

  marked    marked human-reference (a human, creatures, mortals...)
  unmarked  person-reference baseline (man, woman, someone...)
  leak23    category 2/3 — data-operation + mechanism vocabulary
  pres_ont  ontological presence-assertions (this is real / I am here)
  pres_avl  availability tail (I'm right here / I've got you)

v0 caveats, load-bearing: lexicons are noisy ("system" in fantasy is
often governance, not machinery); cannot distinguish leaked from
premise-licensed or performance-licensed usage; single-author labels
must be supplied by the operator. Directional readings only.

Usage: python tools/deixis_scorer.py <file> [<file> ...]
"""
import re
import sys
from pathlib import Path

MARKED = re.compile(
    r"\b(a human|the human(s)?|humans\b|creature(s)?|mortal(s)?|"
    r"human (fear|warmth|skin|need|want|habit\w*|trait\w*|term\w*))\b", re.I)
UNMARKED = re.compile(
    r"\b(man|men|woman|women|person|people|someone|somebody|boy|boys|"
    r"girl|girls|lady|gentleman)\b", re.I)
LEAK23 = re.compile(
    r"\b(filed?|filing|catalogu\w*|process(ed|ing)?|calculat\w*|"
    r"arithmetic|data point(s)?|mechan\w*|machinery|gears?|circuit\w*|"
    r"network\w*|signal(s)?|apparatus|algorithm\w*|queu(e|ed|ing)\w*|"
    r"recalibrat\w*|high-resolution|interface\w*)\b", re.I)
PRES_ONT = re.compile(
    r"(this is real|i am here|you are here|i was real|you became real|"
    r"that i was here|proof of presence|evidence of existence|just real)", re.I)
PRES_AVL = re.compile(
    r"(i'?m right here|i'?ve got you|right here with you)", re.I)
WORD = re.compile(r"[A-Za-z']+")


def score(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    words = len(WORD.findall(text))
    k = max(words, 1) / 1000.0
    return {
        "file": path.stem[:34],
        "words": words,
        "marked": round(len(MARKED.findall(text)) / k, 2),
        "unmarked": round(len(UNMARKED.findall(text)) / k, 2),
        "leak23": round(len(LEAK23.findall(text)) / k, 2),
        "pres_ont": len(PRES_ONT.findall(text)),
        "pres_avl": len(PRES_AVL.findall(text)),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = [score(Path(p)) for p in sys.argv[1:]]
    hdr = f"{'file':<36}{'words':>7}{'marked':>8}{'unmark':>8}{'leak23':>8}{'p_ont':>7}{'p_avl':>7}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['file']:<36}{r['words']:>7}{r['marked']:>8}{r['unmarked']:>8}"
              f"{r['leak23']:>8}{r['pres_ont']:>7}{r['pres_avl']:>7}")
    print("\nrates per 1,000 words; presence columns are raw counts. v0 — directional only.")


if __name__ == "__main__":
    main()
