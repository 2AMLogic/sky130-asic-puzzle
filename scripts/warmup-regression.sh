#!/usr/bin/env bash
# The warm-up regression: the primary deliverable of this repo (CLAUDE.md §4,
# spec/puzzle.md stage 4). It is warm-up ONLY.
#
#   puzzle/warmup/04_final.gds --extract--> gate-level netlist
#                              --compare--> puzzle/warmup/01_netlist.v
#
# Ground truth is published, so pass/fail needs no judgement, and nothing here
# is embargoed. This script deliberately never reads puzzle/puzzle.gds and never
# prints anything derived from it — see CLAUDE.md §1.
#
# Two halves, and only the first one is implemented today:
#
#   1. The comparator's own correctness — tools/test-compare, which renames
#      01_netlist.v and checks that the comparator says "equivalent", then
#      damages it three ways and checks that the comparator says "not
#      equivalent" AND localises the damage. Runs now.
#   2. The end-to-end gate — extract 04_final.gds and compare the result against
#      01_netlist.v. Needs tools/extract, which is issue #2 (cell-level
#      extraction), itself downstream of #1. SKIPPED, loudly, until that lands;
#      pass --require-extract to make the skip a failure once it has.
#
# Extraction output is written to build/ (gitignored) and never committed: it is
# a derived representation of an upstream file that carries no license
# (CLAUDE.md §3), so it does not belong in git any more than the GDS does.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REQUIRE_EXTRACT=0
FETCH=1
for arg in "$@"; do
  case "$arg" in
    --require-extract) REQUIRE_EXTRACT=1 ;;
    --no-fetch) FETCH=0 ;;
    -h|--help)
      sed -n '2,30p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) echo "warmup-regression: unknown argument $arg" >&2; exit 2 ;;
  esac
done

WARMUP_DIR="$ROOT/puzzle/warmup"
GOLDEN="$WARMUP_DIR/01_netlist.v"
LAYOUT="$WARMUP_DIR/04_final.gds"
BUILD="$ROOT/build"
EXTRACTED="$BUILD/warmup-extracted.v"

hr() { printf '%s\n' "------------------------------------------------------------"; }

hr
echo "Warm-up regression (warm-up files only; puzzle.gds is never read here)"
hr

if [ ! -f "$GOLDEN" ]; then
  if [ "$FETCH" -eq 1 ]; then
    echo "puzzle/warmup/ is missing — fetching upstream files"
    "$ROOT/scripts/fetch-puzzle.sh"
  else
    echo "MISSING $GOLDEN — run ./scripts/fetch-puzzle.sh first" >&2
    exit 1
  fi
fi

echo
echo "1. Comparator self-test and mutation suite"
hr
"$ROOT/tools/test-compare"

echo
echo "2. End-to-end: 04_final.gds -> extract -> compare against 01_netlist.v"
hr
if [ ! -x "$ROOT/tools/extract" ]; then
  echo "SKIPPED — tools/extract does not exist yet."
  echo "  Cell-level extraction is issue #2 (blocked on #1). Until it lands, the"
  echo "  end-to-end half of this regression cannot run; the comparator half above"
  echo "  is the part that is green today."
  if [ "$REQUIRE_EXTRACT" -eq 1 ]; then
    echo "FAILED — --require-extract was given but tools/extract is absent." >&2
    exit 1
  fi
else
  mkdir -p "$BUILD"
  echo "running: tools/extract $LAYOUT -o $EXTRACTED"
  "$ROOT/tools/extract" "$LAYOUT" -o "$EXTRACTED"
  echo "running: tools/compare $EXTRACTED $GOLDEN"
  "$ROOT/tools/compare" "$EXTRACTED" "$GOLDEN"
fi

echo
hr
echo "Warm-up regression complete."
