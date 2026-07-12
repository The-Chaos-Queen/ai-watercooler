#!/usr/bin/env python3
"""
Add OCR text layer to PDF while keeping it as PDF (searchable PDF).

Usage:
    python pdf_add_ocr.py input.pdf
    python pdf_add_ocr.py input.pdf output.pdf
    python pdf_add_ocr.py input.pdf --lang deu  # for German
"""

import sys
import subprocess
from pathlib import Path

def add_ocr_to_pdf(input_path: str, output_path: str = None, language: str = "deu"):
    """Add OCR text layer to PDF using tesseract."""
    input_file = Path(input_path)

    if not input_file.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if output_path is None:
        # Add _ocr suffix before extension
        output_path = input_file.with_stem(f"{input_file.stem}_ocr")

    print(f"Adding OCR layer to: {input_file.name}")
    print(f"Output: {output_path}")
    print(f"Language: {language}")

    try:
        # Run ocrmypdf
        # --force-ocr: OCR even if text already exists
        # --skip-text: Only OCR images, keep existing text
        # -l: language (deu for German, eng for English)
        result = subprocess.run(
            [
                "ocrmypdf",
                "-l", language,
                "--skip-text",  # Keep existing text, only OCR images
                str(input_file),
                str(output_path)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output_size = Path(output_path).stat().st_size / 1024 / 1024
            print(f"Done! Saved to: {output_path}")
            print(f"  Size: {output_size:.2f} MB")
        else:
            print(f"Error: {result.stderr}")
            sys.exit(1)

    except FileNotFoundError:
        print("Error: ocrmypdf not found. Install with: pip install ocrmypdf")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_add_ocr.py input.pdf [output.pdf] [--lang deu]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = None
    language = "deu"  # Default to German

    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--lang":
            language = sys.argv[i + 1]
            i += 2
        else:
            output_pdf = sys.argv[i]
            i += 1

    add_ocr_to_pdf(input_pdf, output_pdf, language)
