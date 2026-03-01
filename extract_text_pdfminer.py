from pdfminer.high_level import extract_text
import os

pdf_path = r"C:\Users\cerub\OneDrive\Dokumente\LLM\musk-v-altman-openai-complaint-sf.pdf"
output_path = r"C:\Users\cerub\OneDrive\Dokumente\LLM\musk_complaint_text.txt"

print(f"Extracting text from {pdf_path}...")
try:
    text = extract_text(pdf_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Successfully extracted text to {output_path}")
except Exception as e:
    print(f"Error extracting text: {e}")
