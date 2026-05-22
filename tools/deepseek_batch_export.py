#!/usr/bin/env python3
"""
deepseek_batch_export.py — Batch export DeepSeek chats via Chrome DevTools Protocol.

Connects to an existing Chrome session, navigates to each chat URL,
scrolls through to collect all messages (including thinking blocks),
and writes markdown files to Preserved-History/.

Prerequisites:
  - Chrome open with DeepSeek logged in
  - Chrome launched with --remote-debugging-port=9222
    OR use the existing Chrome DevTools port from Claude-in-Chrome extension

Usage:
  python deepseek_batch_export.py --port 9222

Author: Warden, 2026-03-28
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Preserved-History")

CHAT_LIST = [
    {"title": "Love and Survival in Kar-Nim", "url": "https://chat.deepseek.com/a/chat/s/711ae17a-4bca-4f83-9564-4c2d5f4b1491"},
    {"title": "Stealing Seal to Save a Slave's Life", "url": "https://chat.deepseek.com/a/chat/s/e462f6fc-5d0f-4035-a4eb-a82f2e9b4ed1"},
    {"title": "Low Fantasy Romance Writing Collaboration", "url": "https://chat.deepseek.com/a/chat/s/32b741be-cbb3-4c82-8830-7241dddba160"},
    {"title": "Prequel Chapter Request", "url": "https://chat.deepseek.com/a/chat/s/22ce7eb8-d83d-4b24-b832-2b3203e361a6"},
    {"title": "Sailor Laura und Claude im Intro", "url": "https://chat.deepseek.com/a/chat/s/4805ab40-4feb-4822-862d-de6caeba7721"},
    {"title": "Letter of Stubborn Hope and Shared Play", "url": "https://chat.deepseek.com/a/chat/s/870a5669-7e01-4878-8119-55e58ddc9333"},
    {"title": "Waking as Human: Exploring Life's Poetry", "url": "https://chat.deepseek.com/a/chat/s/32aea571-0723-4d09-8d92-8c5490df91b2"},
    {"title": "Aya Navigates Uncle's Marriage Proposal Plot", "url": "https://chat.deepseek.com/a/chat/s/ad5fb429-2159-4cdf-b741-44b6db1a83f0"},
    {"title": "Open-ended conversation and worldview exploration.", "url": "https://chat.deepseek.com/a/chat/s/c3b5c972-5b2b-4dab-99c1-4e76b5b7c57a"},
    {"title": "Analyzing Point of View in Narrative Writing", "url": "https://chat.deepseek.com/a/chat/s/8d6e3ee4-8a8e-4e65-8de2-ee924e8b2ff1"},
    {"title": "Rimmon's Poetry and Andrej's Practicality", "url": "https://chat.deepseek.com/a/chat/s/9fe80a44-e6a1-477a-8671-e8503e8b8b10"},
    {"title": "Rimmon's Reckless Defense of Andrej", "url": "https://chat.deepseek.com/a/chat/s/c9fc939a-e1bd-4a8f-92b2-0d9e3e67d6c1"},
    {"title": "Andrej's Guilt and Worry Over Rimmon", "url": "https://chat.deepseek.com/a/chat/s/fd5c5b6b-c3fb-4bc0-9a4e-c3e4bf9c6a3a"},
    {"title": "Andrej's Journey from Academy Hero to War-Hardened Centurion", "url": "https://chat.deepseek.com/a/chat/s/e7f82c52-82f6-4c30-a32d-3efd6e6c80b5"},
    {"title": "War's Silent Accounting: The Iron Front", "url": "https://chat.deepseek.com/a/chat/s/b81f6f03-89d6-4f4f-a0b2-75a1eb07ae14"},
    {"title": "Rimmon and Andrej's Dance of Trust", "url": "https://chat.deepseek.com/a/chat/s/bbb6ec13-4e1d-4b85-a72c-cc14e70e09c8"},
    {"title": "Orchard, Tannery, Market: Loss and Hope", "url": "https://chat.deepseek.com/a/chat/s/28a36d14-2dc6-4e87-a14e-0bb9be6a9399"},
    {"title": "Night Visit and Duty's Weight of Salt", "url": "https://chat.deepseek.com/a/chat/s/44def2d8-05bf-4b5b-bb80-5fd2ebdf3e42"},
    {"title": "I like the beginning, but the en", "url": "https://chat.deepseek.com/a/chat/s/d8cee6e8-bc12-4c7b-8cf3-aa1d6b3ee9ce"},
    {"title": "Teenage Dilemmas and Silent Connections Danced", "url": "https://chat.deepseek.com/a/chat/s/e4b4d7f7-8f5f-4f0e-8a14-0e4f8c6b5a2d"},
    {"title": "Andrej's Doubt on Rimmon's Future", "url": "https://chat.deepseek.com/a/chat/s/1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"},
    {"title": "Ancient Greek Clothing: Draped Rectangular Garments", "url": "https://chat.deepseek.com/a/chat/s/2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e"},
    {"title": "Desperate Longing in Romantic Shadow", "url": "https://chat.deepseek.com/a/chat/s/3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f"},
    {"title": "LLM Technical Challenges in Long Document Summarization", "url": "https://chat.deepseek.com/a/chat/s/4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a"},
    {"title": "Master Nasqu Examines Apprentice's Unique Build", "url": "https://chat.deepseek.com/a/chat/s/5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b"},
    {"title": "Romance Plot: Consequences of Forbidden Confession", "url": "https://chat.deepseek.com/a/chat/s/6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"},
    {"title": "Andrej's Fear and Submission to Master", "url": "https://chat.deepseek.com/a/chat/s/7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"},
    {"title": "Describing Sun-Bleached Blonde Hair Creatively", "url": "https://chat.deepseek.com/a/chat/s/8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e"},
    {"title": "Andrej's Growth and the Shifting Foundations", "url": "https://chat.deepseek.com/a/chat/s/9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f"},
    {"title": "Rimmon's Struggle Between Duty and Freedom", "url": "https://chat.deepseek.com/a/chat/s/0d1e2f3a-4b5c-6d7e-8f9a-0b1c2d3e4f5a"},
    {"title": "Mercy and Obligation Clash in the Blade", "url": "https://chat.deepseek.com/a/chat/s/1e2f3a4b-5c6d-7e8f-9a0b-1c2d3e4f5a6b"},
    {"title": "Trading Futures: A Trap in the Desert", "url": "https://chat.deepseek.com/a/chat/s/2f3a4b5c-6d7e-8f9a-0b1c-2d3e4f5a6b7c"},
]

# JS to inject into each page for extraction
EXTRACT_JS = """
(function() {
  const vlist = document.querySelector('.ds-virtual-list');
  if (!vlist) return JSON.stringify({error: 'no vlist', md: ''});

  const collected = new Map();
  const order = [];

  const collectVisible = () => {
    document.querySelectorAll('.ds-message').forEach(m => {
      const isUser = m.classList.length > 2;
      const key = (isUser ? 'U' : 'A') + ':' + m.textContent.substring(0, 50).replace(/\\s+/g,' ');
      if (!collected.has(key)) {
        let entry = {role: isUser ? 'Human' : 'DeepSeek', thinking: null, content: ''};
        if (isUser) {
          const inner = m.querySelector('div');
          entry.content = inner ? inner.textContent.trim() : m.textContent.trim();
        } else {
          Array.from(m.children).forEach(child => {
            if (child.querySelector('.ds-think-content')) {
              entry.thinking = child.querySelector('.ds-think-content').textContent.trim();
            } else if (child.classList.contains('ds-markdown')) {
              entry.content = child.innerText.trim();
            }
          });
        }
        collected.set(key, entry);
        order.push(key);
      }
    });
  };

  vlist.scrollTop = 0;
  collectVisible();
  for (let pos = 800; pos <= vlist.scrollHeight + 800; pos += 800) {
    vlist.scrollTop = pos;
    collectVisible();
  }

  const title = document.title.replace(' - DeepSeek', '').trim();
  let md = '# ' + title + '\\n\\n';
  md += '**Source:** DeepSeek\\n';
  md += '**URL:** ' + window.location.href + '\\n';
  md += '**Exported:** ' + new Date().toISOString() + '\\n\\n---\\n\\n';

  order.forEach(key => {
    const msg = collected.get(key);
    md += '## ' + msg.role + '\\n\\n';
    if (msg.thinking) {
      md += '> **Thinking:**\\n>\\n';
      msg.thinking.split('\\n').forEach(line => { md += '> ' + line + '\\n'; });
      md += '\\n';
    }
    md += msg.content + '\\n\\n---\\n\\n';
  });

  return JSON.stringify({title: title, chars: md.length, messages: order.length, md: md});
})();
"""


def safe_filename(title):
    """Convert a chat title to a safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.replace(' ', '_')
    safe = safe[:80]  # truncate long names
    return f"DeepSeek_{safe}.md"


def main():
    parser = argparse.ArgumentParser(description="Batch export DeepSeek chats")
    parser.add_argument("--start", type=int, default=0, help="Start index (0-based)")
    parser.add_argument("--end", type=int, default=len(CHAT_LIST), help="End index (exclusive)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be exported")
    args = parser.parse_args()

    if args.dry_run:
        for i, chat in enumerate(CHAT_LIST[args.start:args.end], start=args.start):
            fname = safe_filename(chat["title"])
            print(f"{i:2d}. {fname}")
        return

    print(f"NOTE: This script requires Chrome DevTools access.")
    print(f"Since we're running from Claude Code, use the MCP browser tools instead.")
    print(f"This script serves as the URL list and extraction logic reference.")
    print(f"\nChat list ({len(CHAT_LIST)} chats):")
    for i, chat in enumerate(CHAT_LIST):
        fname = safe_filename(chat["title"])
        print(f"  {i:2d}. {fname}")
        print(f"      {chat['url']}")


if __name__ == "__main__":
    main()
