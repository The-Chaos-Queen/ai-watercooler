#!/usr/bin/env python3
"""
Convert PDF to Markdown using docling with OCR support.

Usage:
    python pdf_to_markdown.py input.pdf
    python pdf_to_markdown.py input.pdf output.md
"""

import sys
from pathlib import Path
from docling.document_converter import DocumentConverter

def convert_pdf(input_path: str, output_path: str = None):
    """Convert PDF to markdown."""
    input_file = Path(input_path)

    if not input_file.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if output_path is None:
        output_path = input_file.with_suffix('.md')

    print(f"Converting: {input_file.name}")
    print(f"Output: {output_path}")

    # Create converter (tesserocr will be used automatically if available)
    converter = DocumentConverter()

    # Convert
    result = converter.convert(str(input_file))

    # Export to markdown
    markdown_text = result.document.export_to_markdown()

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    print(f"Done! Saved to: {output_path}")
    print(f"  Pages: {len(result.document.pages) if hasattr(result.document, 'pages') else 'N/A'}")
    print(f"  Size: {len(markdown_text)} characters")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py input.pdf [output.md]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_md = sys.argv[2] if len(sys.argv) > 2 else None

    convert_pdf(input_pdf, output_md)
