import argparse
import os

try:
    import pymupdf4llm
except ImportError:
    print("Error: pymupdf4llm is not installed. Please run 'pip install pymupdf4llm'")
    exit(1)

def main():
    parser = argparse.ArgumentParser(description="Extract PDF to Markdown with Images via PyMuPDF4LLM")
    parser.add_argument("input_pdf", help="Path to the PDF file")
    parser.add_argument("--out", "-o", default=None, help="Output directory for markdown and images")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_pdf)
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = args.out if args.out else os.path.join(os.path.dirname(input_path), base_name + "_extracted")
    
    os.makedirs(out_dir, exist_ok=True)
    image_dir = os.path.join(out_dir, "images")
    os.makedirs(image_dir, exist_ok=True)

    print(f"[*] Extracting Markdown and saving images to {out_dir} ...")
    
    md_text = pymupdf4llm.to_markdown(
        input_path, 
        image_path=image_dir, 
        write_images=True
    )
    
    output_md_file = os.path.join(out_dir, f"{base_name}.md")
    with open(output_md_file, "w", encoding="utf-8") as f:
        f.write(md_text)
        
    print(f"[+] Done! Markdown written to {output_md_file}")

if __name__ == "__main__":
    main()
