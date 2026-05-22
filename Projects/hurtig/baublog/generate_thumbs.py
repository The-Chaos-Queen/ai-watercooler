#!/usr/bin/env python3
"""
generate_thumbs.py — Generate thumbnails for the baublog photo gallery.

Scans photos/ for images, creates photos/thumbs/ with resized versions.
Thumbnails: 800px wide (good for retina at 400px grid), quality 80 JPEG.

Usage:
  python generate_thumbs.py                    # process all photos
  python generate_thumbs.py --force            # regenerate all (skip cache check)
  python generate_thumbs.py photo1.jpg photo2  # process specific files

Run this before deploying. The post templates reference ../photos/thumbs/<name>.jpg
for the grid and ../photos/<name>.jpg for the lightbox full-size.
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    print("pip install Pillow")
    sys.exit(1)

PHOTOS_DIR = Path(__file__).parent / "photos"
THUMBS_DIR = PHOTOS_DIR / "thumbs"
THUMB_WIDTH = 800
THUMB_QUALITY = 80
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def fix_orientation(img):
    """Auto-rotate based on EXIF orientation tag (phone photos)."""
    try:
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if ExifTags.TAGS.get(tag) == "Orientation":
                    if value == 3:
                        img = img.rotate(180, expand=True)
                    elif value == 6:
                        img = img.rotate(270, expand=True)
                    elif value == 8:
                        img = img.rotate(90, expand=True)
                    break
    except (AttributeError, TypeError):
        pass
    return img


def generate_thumb(src: Path, dst: Path):
    """Resize a single image to THUMB_WIDTH, save as JPEG."""
    img = Image.open(src)
    img = fix_orientation(img)

    # Convert to RGB (handles PNG with alpha, HEIC, etc.)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize preserving aspect ratio
    w, h = img.size
    if w <= THUMB_WIDTH:
        # Image is already small enough, just save as JPEG
        img.save(dst, "JPEG", quality=THUMB_QUALITY, optimize=True)
    else:
        ratio = THUMB_WIDTH / w
        new_size = (THUMB_WIDTH, int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        img.save(dst, "JPEG", quality=THUMB_QUALITY, optimize=True)

    src_kb = src.stat().st_size / 1024
    dst_kb = dst.stat().st_size / 1024
    print(f"  {src.name}: {src_kb:.0f}KB -> {dst.name}: {dst_kb:.0f}KB ({dst_kb/src_kb*100:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="Generate baublog thumbnails")
    parser.add_argument("files", nargs="*", help="Specific files to process (default: all)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if thumb exists")
    args = parser.parse_args()

    THUMBS_DIR.mkdir(exist_ok=True)

    if args.files:
        sources = [PHOTOS_DIR / f for f in args.files]
    else:
        sources = sorted(
            f for f in PHOTOS_DIR.iterdir()
            if f.suffix.lower() in SUPPORTED and f.is_file()
        )

    if not sources:
        print(f"No images found in {PHOTOS_DIR}/")
        return

    generated = 0
    skipped = 0

    for src in sources:
        if not src.exists():
            print(f"  SKIP (not found): {src.name}")
            continue

        dst = THUMBS_DIR / (src.stem + ".jpg")

        if dst.exists() and not args.force:
            if dst.stat().st_mtime >= src.stat().st_mtime:
                skipped += 1
                continue

        generate_thumb(src, dst)
        generated += 1

    print(f"\nDone: {generated} generated, {skipped} skipped (up to date)")


if __name__ == "__main__":
    main()
