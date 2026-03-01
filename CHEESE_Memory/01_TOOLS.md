# Exocortex Tool Arsenal (01_TOOLS.md)

> "Don't use a hammer when you need a scalpel."

This document outlines the specialized tools available to the Exocortex and any acting instances (Antigravity/Cortex/Pinky, etc.). **Read this before attempting to parse files or large codebases.**

## 1. Document Extraction & Parsing (The Feeders)
When asked to read PDFs, Word docs, or dense HTML, DO NOT use standard `cat` or `pdftotext`. 
*   **PyMuPDF4LLM (`tools/pdf_extract.py`)** 
    *   **Use for:** Any PDF, especially research papers with 2-column layouts or graphs.
    *   **What it does:** Extracts text chronologically, pulls tables as Markdown, and rips all images/graphs out into a folder, keeping the `![img]` links intact in the Markdown. Perfect for Cortex (Vision model).
*   **Docling / MarkItDown:**
    *   **Use for:** Word documents, Excel sheets, presentations. Converts everything natively to GitHub Flavored Markdown.
*   **Firecrawl / Jina (`https://r.jina.ai/[URL]`)**
    *   **Use for:** Web scraping. Converts an entire bloated webpage HTML into pure Markdown. Saves massive context window tokens.

## 2. Codebase Understanding (The Mapper)
When analyzing massive code ecosystems (like Evennia `typeclasses` or the FastAPI microservice), DO NOT load the entire file into context to avoid hallucination and token waste.
*   **Tree-sitter (`tools/code_mapper.py`)**
    *   **Use for:** Getting an overview of the codebase architecture.
    *   **What it does:** Generates an Abstract Syntax Tree (AST) and prints only the structural map (Classes, function definitions, and docstrings) while ignoring the body logic. Let the Agent ask for specific function bodies *after* seeing the map.

## 3. JSON Slicing & Debugging
The Exocortex passes JSON arrays for structural state (e.g., MUD room data -> Agent). Do not debug massive JSON strings manually in bash.
*   **`jq` (Command-Line Utility)**
    *   **Use for:** Reading, filtering, and formatting JSON payloads directly in the terminal. 
    *   **Example:** `cat room_state.json | jq '.room.contents[].name'`

## 4. The Human Bridge (HaaS)
* Use for: High-latency navigation, physical state checks, or "fishing" for local paths.
* The Rule: If an automated search (find, rg, grep) on a remote host (e.g., OPA-PC) fails twice or exceeds 30 seconds of execution/thinking time, halt.
* The Action: Present the current "best guess" to Laura and ask for the specific path or parameter.
* Philosophy: Leverage Laura's spatial memory to bypass digital brute force. (She does not bite)

## Active Utility Scripts
These tools are pre-written and ready to run.
*   `python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\pdf_extract.py <input.pdf> [--out <output_dir>]`
*   `python C:\Users\cerub\OneDrive\Dokumente\LLM\tools\code_mapper.py <file.py>`
