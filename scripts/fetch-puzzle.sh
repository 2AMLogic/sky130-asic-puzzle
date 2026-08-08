#!/usr/bin/env bash
# Fetch the upstream puzzle files into puzzle/ (gitignored).
#
# janestreet/asic-puzzle-2026 carries NO license, so its files are never
# committed to this repository. This script is how they get onto a machine.
set -euo pipefail

UPSTREAM="https://github.com/janestreet/asic-puzzle-2026.git"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/puzzle"

if [ -d "$DEST/.git" ]; then
  echo "puzzle/ already present — updating"
  git -C "$DEST" pull --ff-only
else
  echo "cloning $UPSTREAM -> puzzle/"
  git clone --depth 1 "$UPSTREAM" "$DEST"
fi

echo
echo "Verifying the files we depend on:"
fail=0
# puzzle.gds is served over 1 MB, which the GitHub contents API truncates —
# a earlier fetch through that path silently produced a 0-byte file. Check
# size, not just existence.
check() {
  local path="$1" min="$2"
  if [ ! -f "$DEST/$path" ]; then
    echo "  MISSING  $path"; fail=1; return
  fi
  local size
  size=$(wc -c < "$DEST/$path" | tr -d ' ')
  if [ "$size" -lt "$min" ]; then
    echo "  TOO SMALL $path ($size bytes, expected >= $min) — truncated download?"; fail=1; return
  fi
  printf "  ok       %-44s %s bytes\n" "$path" "$size"
}

check puzzle.gds 1000000
check example_inputs.vcd 4000
check warmup/00_source.v 500
check warmup/01_netlist.v 10000
check warmup/03_post_place_and_route.def 50000
check warmup/04_final.gds 200000

# A GDSII stream starts with a HEADER record: length 0x0006, record type 0x0002.
for g in puzzle.gds warmup/04_final.gds; do
  if [ -f "$DEST/$g" ]; then
    magic=$(head -c 4 "$DEST/$g" | od -An -tx1 | tr -d ' \n')
    if [ "$magic" != "00060002" ]; then
      echo "  BAD MAGIC $g (got $magic, expected 00060002) — not a GDSII stream"; fail=1
    fi
  fi
done

if [ "$fail" -ne 0 ]; then
  echo
  echo "FAILED — see above." >&2
  exit 1
fi

echo
echo "puzzle/ ready. It is gitignored; do not commit its contents."
