#!/bin/bash
# bulk_convert.sh — read a newline-separated list of Research/*.pdf filenames from $1
# and convert each to Research/converted_md/<basename>.md via tools/pdf_extract.py.
#
# Discards the auto-generated _extracted/ tree (images + redundant md) once the
# flat .md is moved into converted_md/. Skips any PDF that already has a converted
# .md so reruns are idempotent.

set -u
LIST="${1:?usage: bulk_convert.sh <list_file>}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
RESEARCH="${REPO}/Research"
OUT="${RESEARCH}/converted_md"
PY="${PY:-C:/Users/cerub/anaconda3/python.exe}"

mkdir -p "$OUT"

ok=0; skip=0; fail=0
while IFS= read -r pdf; do
    [ -z "$pdf" ] && continue
    base="${pdf%.pdf}"
    target="${OUT}/${base}.md"
    if [ -f "$target" ]; then
        skip=$((skip+1))
        continue
    fi
    src="${RESEARCH}/${pdf}"
    if [ ! -f "$src" ]; then
        echo "MISSING: $pdf"
        fail=$((fail+1))
        continue
    fi
    tmp="${OUT}/${base}_extracted"
    if "$PY" "${REPO}/tools/pdf_extract.py" "$src" --out "$tmp" >/dev/null 2>&1; then
        if [ -f "${tmp}/${base}.md" ]; then
            mv "${tmp}/${base}.md" "$target"
            rm -rf "$tmp"
            ok=$((ok+1))
            echo "OK: $pdf"
        else
            echo "NO_MD: $pdf"
            rm -rf "$tmp"
            fail=$((fail+1))
        fi
    else
        echo "EXTRACT_FAIL: $pdf"
        rm -rf "$tmp"
        fail=$((fail+1))
    fi
done < "$LIST"

echo "---summary---"
echo "ok=$ok skip=$skip fail=$fail"
