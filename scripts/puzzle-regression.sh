#!/usr/bin/env bash
# The puzzle extraction regression (issue #68). Guards the larger third-party
# layout against a klt pin bump or a tools/extract change.
#
#   puzzle/puzzle.gds --tools/extract--------> build/puzzle-extract.v --compare--> evidence/puzzle-extracted.v
#                     --tools/klt-extract----> build/puzzle-klt.v     --compare--> evidence/puzzle-extracted.v
#
# Also asserts the floating-net invariant (exactly one non-port net with loads
# and no driver, in each netlist) and runs one mutation check (a dropped
# instance must be rejected). All outputs go to build/ (gitignored); nothing
# derived from puzzle.gds is committed (CLAUDE.md §3).
#
# Flags: --no-fetch (do not clone upstream; fail if puzzle/ is missing),
#        --require-klt (a missing klt is a failure, not a skip).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FETCH=1
REQUIRE_KLT=0
for arg in "$@"; do
  case "$arg" in
    --no-fetch) FETCH=0 ;;
    --require-klt) REQUIRE_KLT=1 ;;
    -h|--help) sed -n '2,15p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "puzzle-regression: unknown argument $arg" >&2; exit 2 ;;
  esac
done

LAYOUT="$ROOT/puzzle/puzzle.gds"
GOLDEN="$ROOT/evidence/puzzle-extracted.v"
BUILD="$ROOT/build"
hr() { printf '%s\n' "------------------------------------------------------------"; }

hr; echo "Puzzle extraction regression"; hr

if [ ! -s "$LAYOUT" ]; then
  if [ "$FETCH" -eq 1 ]; then
    "$ROOT/scripts/fetch-puzzle.sh"
  else
    echo "MISSING $LAYOUT — run ./scripts/fetch-puzzle.sh first" >&2
    exit 1
  fi
fi
mkdir -p "$BUILD"

if ! command -v klt >/dev/null 2>&1; then
  if [ "$REQUIRE_KLT" -eq 1 ]; then
    echo "FAILED — --require-klt was given but klt is not on PATH." >&2
    exit 1
  fi
  echo "NOTE — klt is not on PATH; the klt half will be skipped (not a pass)."
fi

echo; echo "1. tools/extract -> compare against evidence/puzzle-extracted.v"; hr
"$ROOT/tools/extract" "$LAYOUT" -o "$BUILD/puzzle-extract.v"
"$ROOT/tools/compare" "$BUILD/puzzle-extract.v" "$GOLDEN"
"$ROOT/tools/floating-nets" "$BUILD/puzzle-extract.v"

KLT_RESULT="SKIPPED (klt not on PATH)"
if command -v klt >/dev/null 2>&1; then
  echo; echo "2. klt extract --abstract-cells -> compare against evidence/puzzle-extracted.v"; hr
  echo "klt: $(klt --version)"
  "$ROOT/tools/klt-extract" "$LAYOUT" -o "$BUILD/puzzle-klt.v"
  "$ROOT/tools/compare" "$BUILD/puzzle-klt.v" "$GOLDEN"
  "$ROOT/tools/floating-nets" "$BUILD/puzzle-klt.v"
  KLT_RESULT="PASSED (equivalent to puzzle-extracted.v)"

  echo; echo "3. Mutation check: a dropped instance must be rejected"; hr
  python3 -I - "$BUILD/puzzle-klt.v" "$BUILD/puzzle-klt-mutated.v" "$ROOT/tools" <<'PY'
import sys
sys.path.insert(0, sys.argv[3])
import verilog_netlist as vn
nl = vn.load(sys.argv[1])
victim = next(i for i in nl.instances if not vn.is_fill(i.cell))
nl.instances.remove(victim)
open(sys.argv[2], "w").write(vn.write_verilog(nl))
PY
  if "$ROOT/tools/compare" "$BUILD/puzzle-klt-mutated.v" "$GOLDEN" >/dev/null 2>&1; then
    echo "FAILED — comparator accepted a netlist with an instance removed." >&2
    exit 1
  fi
  echo "mutation check: comparator rejects a damaged netlist (ok)"
fi

echo; hr
echo "klt cross-check: $KLT_RESULT"
echo "Puzzle regression complete."
