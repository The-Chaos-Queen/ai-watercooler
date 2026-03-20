#!/usr/bin/env python3
"""
research_scanner.py — MoCoP Research Radar

Monitors arXiv, GitHub, and HuggingFace for papers, repos, and models
related to MoCoP's cognitive architecture (hypernetwork LoRA injection,
cross-model state transfer, SSM-Transformer bridges, etc.).

Usage:
    python tools/research_scanner.py            # full scan
    python tools/research_scanner.py --dry-run  # show queries, skip API calls
    python tools/research_scanner.py --days 14  # custom lookback window

Output:
    tools/research_scanner_runs/scan_<timestamp>.md  — archived human-readable report
    tools/research_scanner_runs/latest.md            — latest human-readable report
    tools/research_scanner_runs/latest_summary.json  — compact metadata for handoff/dashboard
    tools/research_scanner_seen.json                 — deduplication state

Designed for cron on a Proxmox LXC (Debian 12). Requires only stdlib + requests.
"""

import argparse
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package not found. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "research_scanner_runs"
LATEST_REPORT_FILE = RESULTS_DIR / "latest.md"
LATEST_SUMMARY_FILE = RESULTS_DIR / "latest_summary.json"
SEEN_FILE = SCRIPT_DIR / "research_scanner_seen.json"

# arXiv API (Atom feed)
ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_MAX_RESULTS = 30  # per query group

# GitHub search API (unauthenticated: 10 req/min)
GITHUB_SEARCH_API = "https://api.github.com/search/repositories"

# HuggingFace API
HF_PAPERS_API = "https://huggingface.co/api/papers"
HF_MODELS_API = "https://huggingface.co/api/models"

# Request settings
REQUEST_TIMEOUT = 30  # seconds
RETRY_DELAY = 3       # seconds between retries
MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# Search queries — grouped so we can batch arXiv OR-queries efficiently
# ---------------------------------------------------------------------------

# Each group is OR'd together in a single arXiv query to minimize API calls.
# Groups are thematically clustered so results stay interpretable.
ARXIV_QUERY_GROUPS = [
    {
        "label": "Hypernetwork + LoRA injection",
        "terms": [
            "hypernetwork LoRA",
            "dynamic LoRA injection",
            "LoRA weight generation",
            "hypernetwork adapter",
        ],
    },
    {
        "label": "Cross-model state transfer",
        "terms": [
            "cross-model memory transfer",
            "state transfer language model",
            "latent state injection transformer",
            "model state bridging",
        ],
    },
    {
        "label": "SSM-Transformer hybrids / bridges",
        "terms": [
            "state space model transformer bridge",
            "Mamba transformer hybrid",
            "SSM transformer integration",
            "recurrent state transformer",
        ],
    },
    {
        "label": "Test-time memorization / surprise gating",
        "terms": [
            "test-time memorization",
            "surprise gated memory",
            "Titans memorization",
            "MIRAS architecture",
            "test-time training language model",
        ],
    },
    {
        "label": "Cognitive architecture / model continuity",
        "terms": [
            "cognitive architecture LLM",
            "model continuity neural network",
            "persistent memory language model",
            "episodic memory transformer",
        ],
    },
]

# GitHub searches — kept shorter since GitHub search is less flexible
GITHUB_QUERIES = [
    "hypernetwork LoRA injection",
    "mamba transformer bridge",
    "dynamic LoRA generation",
    "state space model LoRA",
    "cross model memory transfer",
    "test time memorization transformer",
    "Titans memorization",
]

# HuggingFace searches
HF_QUERIES = [
    "hypernetwork LoRA",
    "mamba transformer bridge",
    "state transfer",
    "dynamic LoRA",
    "test-time memorization",
    "Titans memory",
]

# arXiv categories to restrict search (cs.CL, cs.LG, cs.AI cover NLP + ML + AI)
ARXIV_CATEGORIES = ["cs.CL", "cs.LG", "cs.AI"]

# Relevance keywords — papers/repos matching these get flagged in the report
HIGH_RELEVANCE_KEYWORDS = [
    "hypernetwork",
    "lora injection",
    "dynamic lora",
    "state space model",
    "mamba",
    "cross-model",
    "state transfer",
    "test-time memorization",
    "titans",
    "miras",
    "surprise gated",
    "ssm",
    "cognitive bridge",
    "latent injection",
    "weight generation",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("research_scanner")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_seen() -> dict:
    """Load the deduplication state file."""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("Corrupted seen-state file; starting fresh")
    return {"arxiv": [], "github": [], "huggingface": []}


def save_seen(seen: dict) -> None:
    """Persist the deduplication state."""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)


def build_report_path(scan_time: datetime) -> Path:
    """Return the timestamped archive path for a scanner run."""
    stamp = scan_time.strftime("%Y%m%dT%H%M%SZ")
    return RESULTS_DIR / f"scan_{stamp}.md"


def build_summary(
    arxiv_papers: list[dict],
    github_repos: list[dict],
    hf_results: list[dict],
    days: int,
    scan_time: datetime,
    report_path: Path,
) -> dict[str, Any]:
    """Build a compact summary payload suitable for handoff/dashboard logging."""
    high_rel_papers = len([p for p in arxiv_papers if p["relevance_score"] >= 3])
    high_rel_repos = len([r for r in github_repos if r["relevance_score"] >= 2])
    high_rel_hf = len([h for h in hf_results if h["relevance_score"] >= 2])
    return {
        "scan_time_utc": scan_time.isoformat(),
        "lookback_days": days,
        "report_path": str(report_path),
        "latest_report_path": str(LATEST_REPORT_FILE),
        "counts": {
            "arxiv_papers": len(arxiv_papers),
            "github_repos": len(github_repos),
            "huggingface_results": len(hf_results),
            "total_results": len(arxiv_papers) + len(github_repos) + len(hf_results),
        },
        "high_relevance": {
            "arxiv_papers": high_rel_papers,
            "github_repos": high_rel_repos,
            "huggingface_results": high_rel_hf,
            "total_results": high_rel_papers + high_rel_repos + high_rel_hf,
        },
        "top_hits": {
            "arxiv": [p["title"] for p in arxiv_papers[:3]],
            "github": [r["name"] for r in github_repos[:3]],
            "huggingface": [h["title"] for h in hf_results[:3]],
        },
    }


def safe_request(method: str, url: str, **kwargs) -> requests.Response | None:
    """Make an HTTP request with retries and graceful error handling."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 403:
                log.warning("Rate-limited (403) on %s — backing off", url)
                time.sleep(RETRY_DELAY * attempt * 2)
            elif resp.status_code == 422:
                log.warning("Unprocessable query (422) on %s — skipping", url)
                return None
            else:
                log.warning(
                    "HTTP %d on %s (attempt %d/%d)",
                    resp.status_code,
                    url,
                    attempt,
                    MAX_RETRIES,
                )
                time.sleep(RETRY_DELAY * attempt)
        except requests.exceptions.ConnectionError:
            log.warning("Connection error on %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
            time.sleep(RETRY_DELAY * attempt)
        except requests.exceptions.Timeout:
            log.warning("Timeout on %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
            time.sleep(RETRY_DELAY * attempt)
        except requests.exceptions.RequestException as e:
            log.warning("Request error on %s: %s", url, e)
            return None
    log.error("All retries exhausted for %s", url)
    return None


def score_relevance(text: str) -> int:
    """Count how many high-relevance keywords appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in HIGH_RELEVANCE_KEYWORDS if kw in text_lower)


def truncate(text: str, max_len: int = 300) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def build_arxiv_query(terms: list[str], days: int) -> str:
    """
    Build an arXiv search query string.
    OR the terms together, restrict to target categories.
    """
    # Quote multi-word terms and OR them
    quoted = [f'all:"{t}"' for t in terms]
    terms_clause = " OR ".join(quoted)

    # Category restriction
    cat_clause = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)

    return f"({terms_clause}) AND ({cat_clause})"


def search_arxiv(days: int, seen_ids: list[str]) -> list[dict]:
    """Query arXiv API and return new papers."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_papers = []

    for group in ARXIV_QUERY_GROUPS:
        query = build_arxiv_query(group["terms"], days)
        log.info("arXiv query [%s]: %s", group["label"], query[:120])

        params = {
            "search_query": query,
            "start": 0,
            "max_results": ARXIV_MAX_RESULTS,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        resp = safe_request("GET", ARXIV_API, params=params)
        if resp is None:
            continue

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            log.warning("Failed to parse arXiv XML for group '%s'", group["label"])
            continue

        for entry in root.findall("atom:entry", ARXIV_NS):
            arxiv_id_raw = entry.find("atom:id", ARXIV_NS)
            if arxiv_id_raw is None:
                continue
            arxiv_id = arxiv_id_raw.text.strip()

            # Skip if already seen
            if arxiv_id in seen_ids:
                continue

            # Parse published date
            published_el = entry.find("atom:published", ARXIV_NS)
            if published_el is not None:
                try:
                    pub_date = datetime.fromisoformat(
                        published_el.text.strip().replace("Z", "+00:00")
                    )
                    if pub_date < cutoff:
                        continue
                except ValueError:
                    pass  # can't parse date, include anyway

            title_el = entry.find("atom:title", ARXIV_NS)
            summary_el = entry.find("atom:summary", ARXIV_NS)
            authors = entry.findall("atom:author/atom:name", ARXIV_NS)

            title = title_el.text.strip().replace("\n", " ") if title_el is not None else "(no title)"
            abstract = summary_el.text.strip() if summary_el is not None else ""
            author_names = [a.text.strip() for a in authors[:5]]  # cap at 5 authors
            if len(authors) > 5:
                author_names.append(f"et al. (+{len(authors) - 5})")

            # Find PDF link
            pdf_link = arxiv_id  # fallback
            for link in entry.findall("atom:link", ARXIV_NS):
                if link.get("title") == "pdf":
                    pdf_link = link.get("href", arxiv_id)
                    break

            relevance = score_relevance(title + " " + abstract)

            paper = {
                "id": arxiv_id,
                "title": title,
                "authors": ", ".join(author_names),
                "abstract_snippet": truncate(abstract),
                "link": pdf_link,
                "query_group": group["label"],
                "relevance_score": relevance,
                "published": published_el.text.strip() if published_el is not None else "unknown",
            }
            all_papers.append(paper)

        # Be polite to arXiv — 3 second pause between queries (their policy)
        time.sleep(3)

    # Deduplicate across query groups (same paper may match multiple groups)
    seen_in_results: set[str] = set()
    deduped: list[dict] = []
    for p in all_papers:
        if p["id"] not in seen_in_results:
            seen_in_results.add(p["id"])
            deduped.append(p)

    # Sort by relevance score descending
    deduped.sort(key=lambda x: x["relevance_score"], reverse=True)
    return deduped


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


def search_github(days: int, seen_urls: list[str]) -> list[dict]:
    """Search GitHub for relevant repos."""
    cutoff_str = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    all_repos: list[dict] = []
    seen_in_results: set[str] = set()

    for query in GITHUB_QUERIES:
        # GitHub search: query + pushed date filter
        q = f"{query} pushed:>={cutoff_str}"
        log.info("GitHub query: %s", q)

        params = {
            "q": q,
            "sort": "updated",
            "order": "desc",
            "per_page": 10,
        }
        headers = {"Accept": "application/vnd.github.v3+json"}

        resp = safe_request("GET", GITHUB_SEARCH_API, params=params, headers=headers)
        if resp is None:
            continue

        try:
            data = resp.json()
        except json.JSONDecodeError:
            log.warning("Failed to parse GitHub JSON for query '%s'", query)
            continue

        for item in data.get("items", []):
            url = item.get("html_url", "")
            if url in seen_urls or url in seen_in_results:
                continue
            seen_in_results.add(url)

            desc = item.get("description") or "(no description)"
            full_text = f"{item.get('full_name', '')} {desc} {' '.join(item.get('topics', []))}"
            relevance = score_relevance(full_text)

            repo = {
                "name": item.get("full_name", "unknown"),
                "description": truncate(desc, 200),
                "stars": item.get("stargazers_count", 0),
                "url": url,
                "language": item.get("language", "unknown"),
                "updated": item.get("updated_at", "unknown"),
                "query": query,
                "relevance_score": relevance,
            }
            all_repos.append(repo)

        # GitHub unauthenticated: 10 req/min. Space requests out.
        time.sleep(6)

    all_repos.sort(key=lambda x: (-x["relevance_score"], -x["stars"]))
    return all_repos


# ---------------------------------------------------------------------------
# HuggingFace
# ---------------------------------------------------------------------------


def search_huggingface_papers(seen_ids: list[str]) -> list[dict]:
    """Search HuggingFace daily papers endpoint."""
    results: list[dict] = []
    seen_in_results: set[str] = set()

    # HF daily papers — fetch recent papers
    log.info("HuggingFace: fetching daily papers")
    resp = safe_request("GET", HF_PAPERS_API)
    if resp is not None:
        try:
            papers = resp.json()
        except json.JSONDecodeError:
            papers = []

        for paper in papers:
            paper_id = paper.get("id", "")
            if not paper_id or paper_id in seen_ids or paper_id in seen_in_results:
                continue

            title = paper.get("title", "(no title)")
            summary = paper.get("summary", "")
            full_text = f"{title} {summary}"
            relevance = score_relevance(full_text)

            # Only include papers with some relevance to avoid noise
            if relevance == 0:
                continue

            seen_in_results.add(paper_id)
            results.append({
                "id": paper_id,
                "title": title,
                "summary_snippet": truncate(summary),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "relevance_score": relevance,
            })

    time.sleep(1)

    # HF model search
    for query in HF_QUERIES:
        log.info("HuggingFace model search: %s", query)
        params = {
            "search": query,
            "sort": "lastModified",
            "direction": -1,
            "limit": 5,
        }
        resp = safe_request("GET", HF_MODELS_API, params=params)
        if resp is None:
            continue

        try:
            models = resp.json()
        except json.JSONDecodeError:
            continue

        for model in models:
            model_id = model.get("modelId", "") or model.get("id", "")
            if not model_id or model_id in seen_ids or model_id in seen_in_results:
                continue

            tags = " ".join(model.get("tags", []))
            full_text = f"{model_id} {tags}"
            relevance = score_relevance(full_text)

            if relevance == 0:
                continue

            seen_in_results.add(model_id)
            results.append({
                "id": model_id,
                "title": model_id,
                "summary_snippet": f"Tags: {tags[:200]}" if tags else "(no tags)",
                "url": f"https://huggingface.co/{model_id}",
                "relevance_score": relevance,
                "type": "model",
            })

        time.sleep(2)

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    arxiv_papers: list[dict],
    github_repos: list[dict],
    hf_results: list[dict],
    days: int,
    scan_time: datetime,
) -> str:
    """Generate the Markdown report."""

    lines: list[str] = []
    lines.append("# MoCoP Research Radar — Scan Report")
    lines.append("")
    lines.append(f"**Scan date:** {scan_time.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Lookback window:** {days} days")
    lines.append(f"**Papers found:** {len(arxiv_papers)}")
    lines.append(f"**Repos found:** {len(github_repos)}")
    lines.append(f"**HuggingFace results:** {len(hf_results)}")
    lines.append("")

    # --- Relevance summary ---
    high_rel_papers = [p for p in arxiv_papers if p["relevance_score"] >= 3]
    high_rel_repos = [r for r in github_repos if r["relevance_score"] >= 2]
    high_rel_hf = [h for h in hf_results if h["relevance_score"] >= 2]

    if high_rel_papers or high_rel_repos or high_rel_hf:
        lines.append("## High-Relevance Hits")
        lines.append("")
        lines.append("These results match 2+ MoCoP-relevant keywords and deserve a closer look.")
        lines.append("")
        for p in high_rel_papers:
            lines.append(f"- **[arXiv]** [{p['title']}]({p['link']}) (relevance: {p['relevance_score']})")
        for r in high_rel_repos:
            lines.append(f"- **[GitHub]** [{r['name']}]({r['url']}) ({r['stars']} stars, relevance: {r['relevance_score']})")
        for h in high_rel_hf:
            lines.append(f"- **[HF]** [{h['title']}]({h['url']}) (relevance: {h['relevance_score']})")
        lines.append("")

    # --- arXiv ---
    lines.append("## arXiv Papers")
    lines.append("")
    if not arxiv_papers:
        lines.append("No new papers found in this scan window.")
    else:
        for p in arxiv_papers:
            rel_badge = f" [REL:{p['relevance_score']}]" if p["relevance_score"] > 0 else ""
            lines.append(f"### {p['title']}{rel_badge}")
            lines.append("")
            lines.append(f"- **Authors:** {p['authors']}")
            lines.append(f"- **Published:** {p['published']}")
            lines.append(f"- **Query group:** {p['query_group']}")
            lines.append(f"- **Link:** {p['link']}")
            lines.append(f"- **Abstract:** {p['abstract_snippet']}")
            lines.append("")
    lines.append("")

    # --- GitHub ---
    lines.append("## GitHub Repositories")
    lines.append("")
    if not github_repos:
        lines.append("No new repositories found in this scan window.")
    else:
        for r in github_repos:
            rel_badge = f" [REL:{r['relevance_score']}]" if r["relevance_score"] > 0 else ""
            lines.append(f"### [{r['name']}]({r['url']}){rel_badge}")
            lines.append("")
            lines.append(f"- **Stars:** {r['stars']} | **Language:** {r['language']}")
            lines.append(f"- **Updated:** {r['updated']}")
            lines.append(f"- **Search query:** {r['query']}")
            lines.append(f"- **Description:** {r['description']}")
            lines.append("")
    lines.append("")

    # --- HuggingFace ---
    lines.append("## HuggingFace")
    lines.append("")
    if not hf_results:
        lines.append("No new relevant results found.")
    else:
        for h in hf_results:
            htype = h.get("type", "paper")
            rel_badge = f" [REL:{h['relevance_score']}]" if h["relevance_score"] > 0 else ""
            lines.append(f"### [{h['title']}]({h['url']}) ({htype}){rel_badge}")
            lines.append("")
            lines.append(f"- **Summary:** {h['summary_snippet']}")
            lines.append("")
    lines.append("")

    # --- Footer ---
    lines.append("---")
    lines.append(f"*Generated by research_scanner.py — {scan_time.strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="MoCoP Research Radar — scan arXiv, GitHub, and HuggingFace"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print queries without making API calls",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Lookback window in days (default: 30)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the seen-state file before scanning",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output path for the results Markdown file",
    )
    args = parser.parse_args()

    scan_time = datetime.now(timezone.utc)
    log.info("MoCoP Research Radar starting (days=%d, dry_run=%s)", args.days, args.dry_run)

    # --- Dry run ---
    if args.dry_run:
        print("\n=== DRY RUN — Queries that would be executed ===\n")

        print("--- arXiv Queries ---")
        for group in ARXIV_QUERY_GROUPS:
            query = build_arxiv_query(group["terms"], args.days)
            print(f"\n  [{group['label']}]")
            print(f"  Query: {query}")

        print("\n--- GitHub Queries ---")
        cutoff_str = (scan_time - timedelta(days=args.days)).strftime("%Y-%m-%d")
        for q in GITHUB_QUERIES:
            print(f"  {q} pushed:>={cutoff_str}")

        print("\n--- HuggingFace Queries ---")
        print("  Daily papers endpoint (filtered by relevance keywords)")
        for q in HF_QUERIES:
            print(f"  Model search: {q}")

        print(f"\nResults directory: {RESULTS_DIR}")
        print(f"Latest report path: {LATEST_REPORT_FILE}")
        print(f"Latest summary path: {LATEST_SUMMARY_FILE}")
        print(f"Seen-state file: {SEEN_FILE}")
        return

    # --- Load deduplication state ---
    if args.reset and SEEN_FILE.exists():
        log.info("Resetting seen-state file")
        SEEN_FILE.unlink()

    seen = load_seen()

    # --- Run searches ---
    log.info("=== Searching arXiv ===")
    arxiv_papers = search_arxiv(args.days, seen.get("arxiv", []))
    log.info("Found %d new arXiv papers", len(arxiv_papers))

    log.info("=== Searching GitHub ===")
    github_repos = search_github(args.days, seen.get("github", []))
    log.info("Found %d new GitHub repos", len(github_repos))

    log.info("=== Searching HuggingFace ===")
    hf_results = search_huggingface_papers(seen.get("huggingface", []))
    log.info("Found %d new HuggingFace results", len(hf_results))

    # --- Update seen state ---
    seen["arxiv"] = list(set(seen.get("arxiv", []) + [p["id"] for p in arxiv_papers]))
    seen["github"] = list(set(seen.get("github", []) + [r["url"] for r in github_repos]))
    seen["huggingface"] = list(set(seen.get("huggingface", []) + [h["id"] for h in hf_results]))
    seen["last_scan"] = scan_time.isoformat()
    save_seen(seen)
    log.info("Seen-state updated: %s", SEEN_FILE)

    # --- Generate report ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output).expanduser().resolve() if args.output else build_report_path(scan_time)
    report = generate_report(arxiv_papers, github_repos, hf_results, args.days, scan_time)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    log.info("Report written to: %s", output_path)

    with open(LATEST_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    log.info("Latest report written to: %s", LATEST_REPORT_FILE)

    summary = build_summary(
        arxiv_papers=arxiv_papers,
        github_repos=github_repos,
        hf_results=hf_results,
        days=args.days,
        scan_time=scan_time,
        report_path=output_path,
    )
    with open(LATEST_SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log.info("Latest summary written to: %s", LATEST_SUMMARY_FILE)

    # --- Summary ---
    total = summary["counts"]["total_results"]
    high_rel = summary["high_relevance"]["total_results"]
    print(f"\nScan complete: {total} new results ({high_rel} high-relevance)")
    print(f"Report: {output_path}")
    print(f"Latest summary: {LATEST_SUMMARY_FILE}")


if __name__ == "__main__":
    main()
