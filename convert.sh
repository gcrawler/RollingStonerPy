#!/usr/bin/env bash
# Batch-convert Bondi Secure DJVU files to PDF.
#
# Usage:
#   ./convert.sh                        — converts all .djvu in ./Issues to ./output
#   ./convert.sh /path/to/dir           — single input directory
#   ./convert.sh /path/to/file.djvu     — single file
#   ./convert.sh /path/to/dir /path/to/out

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="${1:-$SCRIPT_DIR/Issues}"
OUTPUT="${2:-$SCRIPT_DIR/output}"
DECRYPT="$SCRIPT_DIR/bondi_decrypt.py"

# Set SUBSAMPLE=2 (or 3) to reduce output file size at the cost of resolution.
# Default: no subsampling (full quality). At subsample=2, ~126MB/issue vs ~362MB.
DDJVU_OPTS="${DDJVU_OPTS:-}"
if [[ -n "${SUBSAMPLE:-}" ]]; then
    DDJVU_OPTS="-subsample=${SUBSAMPLE} ${DDJVU_OPTS}"
fi

# Verify tools
for cmd in python3 djvm ddjvu; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: '$cmd' not found. Install with: brew install djvulibre" >&2
        exit 1
    fi
done
python3 -c "from Crypto.Cipher import Blowfish" 2>/dev/null || {
    echo "ERROR: pycryptodome not installed. Run: pip3 install pycryptodome" >&2
    exit 1
}

mkdir -p "$OUTPUT"
OUTPUT_ABS="$(cd "$OUTPUT" && pwd)"

convert_one() {
    local src="$1"
    local stem
    stem="$(basename "$src" .djvu)"
    local out_pdf="$OUTPUT_ABS/${stem}.pdf"

    if [[ -f "$out_pdf" ]]; then
        echo "  skip  $stem.pdf (already exists)"
        return
    fi

    echo -n "  converting $stem ... "
    local tmp_base tmp
    tmp_base="$(mktemp /tmp/bondi_XXXXXX)"   # Xs must be at end for macOS mktemp
    tmp="${tmp_base}.djvu"
    mv "$tmp_base" "$tmp"
    trap "rm -f '$tmp'" RETURN

    python3 "$DECRYPT" "$src" "$tmp" 2>/dev/null
    # shellcheck disable=SC2086
    if ddjvu -format=pdf $DDJVU_OPTS "$tmp" "$out_pdf" 2>/dev/null; then
        echo "done → $(du -sh "$out_pdf" | cut -f1)"
    else
        echo "WARN: ddjvu failed for $stem (source may be corrupt) — skipping"
        rm -f "$out_pdf"
    fi
}

if [[ -f "$INPUT" ]]; then
    echo "==> Converting: $INPUT"
    echo "==> Output to: $OUTPUT_ABS"
    convert_one "$INPUT"
else
    shopt -s nullglob
    files=("$INPUT"/*.djvu)
    echo "==> Converting ${#files[@]} files in: $INPUT"
    echo "==> Output to: $OUTPUT_ABS"
    for f in "${files[@]}"; do
        convert_one "$f"
    done
fi

echo "==> Done. PDFs in $OUTPUT_ABS"
