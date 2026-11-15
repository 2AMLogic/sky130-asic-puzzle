# shellcheck shell=bash
# Shared klt/PDK/LEF resolution preamble for the klt-lvs harness scripts
# (issue #123). Source it, never execute it:
#
#   source scripts/lib/klt-lvs-preamble.sh 'warmup-klt-lvs'
#
# The argument is the calling script's message prefix. Requires $PDK (the
# caller's default: sky130A) and runs under the caller's `set -euo pipefail`.
# On success it sets PDK_JSON, LIBS_REF and CELL_LEF in the caller's scope —
# sourced, not run in a subshell, precisely so they reach it. On a missing
# klt, an unresolvable PDK or a missing std-cell LEF it prints the
# caller-prefixed hard error and exits 2, which — sourced — exits the
# caller: a missing prerequisite never silently skips (these scripts compare
# against ground truth, and a skipped check would look like a pass).
#
# Lives under scripts/lib/ rather than scripts/ so scripts/lint.sh's
# `-maxdepth 1` enumeration does not demand the +x bit a sourced file
# deliberately does not carry (issue #123, Champion note 1).

command -v klt >/dev/null || { echo "$1: klt not found on PATH" >&2; exit 2; }

if ! PDK_JSON="$(klt pdk find --pdk "$PDK" --format json 2>/dev/null)"; then
  echo "$1: no '$PDK' PDK found. Point PDK_ROOT at a sky130 install" >&2
  echo "(keep it inside your worktree; do not install into shared host paths)." >&2
  exit 2
fi

# The std-cell LEF --abstract-cell-lef needs, derived from the PDK this run
# actually resolved rather than hardcoded to ~/.ciel.
LIBS_REF="$(printf '%s' "$PDK_JSON" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["assets"]["libs_ref"])')"
CELL_LEF="$LIBS_REF/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
if [ ! -f "$CELL_LEF" ]; then
  echo "$1: '$PDK' resolved to libs_ref '$LIBS_REF' but its" >&2
  echo "sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef is missing. --abstract-cells" >&2
  echo "cannot resolve the std cells' VNB/VPB pins without it, which silently" >&2
  echo "changes the verdict; install the libs.ref assets and re-run." >&2
  exit 2
fi
