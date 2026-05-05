"""
backup_snapshot.py — Creates a ZIP snapshot of Dokumente (excluding training runs)
and uploads it to Google Drive.

Runs weekly via Windows Scheduled Task.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SOURCE = Path(r"C:\Users\cerub\OneDrive\Dokumente")
ZIP_DIR = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\tmp")
LOG = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\tools\backup_logs\snapshot.log")
GDRIVE_DEST = "gdrive:backups/Dokumente/snapshots/"

EXCLUDE_PATTERNS = [
    r"\.git\\",
    r"\.venv\\",
    r"__pycache__",
    r"node_modules",
    r"\.mypy_cache",
    r"run_a1\\",
    r"run_a3\\",
    r"run_pilot_01\\",
    r"run_actbias\\",
    r"run_pca_clamped\\",
    r"run_constant_bias\\",
    r"run_bypass_raw\\",
    r"run_64s\\",
    r"step1_",
    r"run_reincarnation\\",
    r"chrome_profile\\",
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    date = datetime.now().strftime("%Y-%m-%d")
    zip_name = f"Dokumente_{date}.zip"
    zip_path = ZIP_DIR / zip_name

    ZIP_DIR.mkdir(parents=True, exist_ok=True)

    log(f"Starting snapshot: {zip_name}")

    # Collect files, excluding heavy stuff
    import re
    exclude_re = [re.compile(p) for p in EXCLUDE_PATTERNS]
    files = []
    for root, dirs, filenames in os.walk(SOURCE):
        rel_root = os.path.relpath(root, SOURCE)
        if any(p.search(rel_root) for p in exclude_re):
            continue
        for fn in filenames:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, SOURCE)
            if any(p.search(rel) for p in exclude_re):
                continue
            files.append((full, rel))

    log(f"Found {len(files)} files to zip")

    # Create ZIP
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in files:
            try:
                zf.write(full, rel)
            except (PermissionError, OSError) as e:
                pass  # skip locked files

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    log(f"ZIP created: {zip_name} ({size_mb:.1f} MB)")

    # Upload to Google Drive
    log(f"Uploading to {GDRIVE_DEST}...")
    result = subprocess.run(
        ["rclone", "copy", str(zip_path), GDRIVE_DEST],
        capture_output=True, text=True, timeout=3600,
    )
    if result.returncode == 0:
        log(f"Upload complete: {zip_name}")
        # Clean up local ZIP
        zip_path.unlink()
        log("Local ZIP cleaned up")
    else:
        log(f"Upload FAILED: {result.stderr[:200]}")

    log("Snapshot done.")


if __name__ == "__main__":
    main()
