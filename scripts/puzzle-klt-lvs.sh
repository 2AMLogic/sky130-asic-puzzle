#!/usr/bin/env bash
# Run `klt lvs` on the puzzle layout against the netlist this repository
# extracted from it (issue #76, scope item 3 of #47). Unlike the warm-up
# (scripts/warmup-klt-lvs.sh) there is no published ground truth here, so this
# is a self-consistency check — but at 1,618 instances over the full met1-met5
# routing stack it reaches `klt lvs` at a size and a reference shape the 79-cell
# warm-up cannot.
#
#   puzzle/puzzle.gds --klt extract (--abstract-cells)--> build/puzzle-klt-lvs.spice
#   build/puzzle-klt-lvs.spice --klt lvs--> evidence/puzzle-extracted.v  (signal-only)
#
# The reference is committed in this repository, so nothing is elided: both
# sides' names are already public here. The extracted layout netlist stays in
# build/ (gitignored) — it is derived from a file that carries no license
# (CLAUDE.md §3). Never reads puzzle/warmup/.
#
# Needs a sky130 PDK. Set PDK_ROOT to one, or have it under ~/.ciel. klt lvs has
# no --pdk CLI flag; the variant is named in the request (`reference.pdk`), the
# selector upstream's klayout-tools#3748 fix points at. $PDK here is only this
# script's own default, passed explicitly to the two commands that take it. A
# missing PDK, a missing std-cell LEF and a missing klt are each a hard error:
# this never silently skips.
#
# `klt extract --abstract-cells` is given the PDK's own sky130_fd_sc_hd.lef via
# --abstract-cell-lef so this script extracts identically to the warm-up one and
# the klayout-tools#3749 fix engages. No --def-pins: upstream ships no DEF for
# the puzzle, and the 13 top-level pins come from in-GDS labels already.
#
# STAGE ORDER. The isolating probe runs *before* the compare against the
# committed reference, deliberately. `klt lvs` cannot read
# evidence/puzzle-extracted.v at all today — its eight escaped-bracket scalar
# ports `\O[0] … \O[7] ` trip the gate-level-verilog reader's port-list check
# (klayout-tools#5693, a follow-up to closed #1371 and #4810) and it exits 1
# before any compare. That is a genuine hard error (klt's documented exit 1)
# and stops the script; running the probe first is what keeps that abort from
# also suppressing the one measurement that does get through. The probe is
# build/-only and nothing committed depends on it. There is no workaround for
# the reader defect in this script: the error is left to surface verbatim
# (CLAUDE.md §2).
#
# Exit 0 means both stages completed, NOT that the compare matched; the verdicts
# are printed and live in the envelopes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOP="puzzle"
LAYOUT_GDS="puzzle/puzzle.gds"
REFERENCE="evidence/puzzle-extracted.v"
BUILD="build"
LAYOUT_NETLIST="$BUILD/puzzle-klt-lvs.spice"
PROBE_REFERENCE="$BUILD/puzzle-klt-lvs-busport.v"
PDK="${PDK:-sky130A}"

command -v klt >/dev/null || { echo "puzzle-klt-lvs: klt not found on PATH" >&2; exit 2; }

if [ ! -f "$LAYOUT_GDS" ]; then
  ./scripts/fetch-puzzle.sh
fi

if ! PDK_JSON="$(klt pdk find --pdk "$PDK" --format json 2>/dev/null)"; then
  echo "puzzle-klt-lvs: no '$PDK' PDK found. Point PDK_ROOT at a sky130 install" >&2
  echo "(keep it inside your worktree; do not install into shared host paths)." >&2
  exit 2
fi

# The std-cell LEF --abstract-cell-lef needs, derived from the PDK this run
# actually resolved rather than hardcoded to ~/.ciel.
LIBS_REF="$(printf '%s' "$PDK_JSON" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["assets"]["libs_ref"])')"
CELL_LEF="$LIBS_REF/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
if [ ! -f "$CELL_LEF" ]; then
  echo "puzzle-klt-lvs: '$PDK' resolved to libs_ref '$LIBS_REF' but its" >&2
  echo "sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef is missing. --abstract-cells" >&2
  echo "cannot resolve the std cells' VNB/VPB pins without it, which silently" >&2
  echo "changes the verdict; install the libs.ref assets and re-run." >&2
  exit 2
fi

mkdir -p "$BUILD" evidence
klt --version

klt extract "$LAYOUT_GDS" --deck sky130 --pdk "$PDK" --top "$TOP" \
  --abstract-cells 'sky130_fd_sc_hd__*' --abstract-cell-lef "$CELL_LEF" \
  -o "$LAYOUT_NETLIST" --format json > "$BUILD/puzzle-klt-lvs-extract.json"

python3 -I - "$BUILD/puzzle-klt-lvs-extract.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
cells = d["abstracted_cells"]
pins = sorted(n["name"] for n in d["nets"] if n.get("pin"))
print(f"extract: status={d['status']} nets={d['net_count']} pins={d['pin_count']} "
      f"abstracted_instances={sum(c['instance_count'] for c in cells)} "
      f"cell_types={len(cells)} devices={d['device_count']}")
print(f"  pins: {chr(32).join(pins)}")
PY

# `klt lvs` requests go in on stdin so every path is relative to the repo root,
# the same base `klt lvs --check` resolves them against when re-run from here.
run_lvs() {  # run_lvs <reference-path> <envelope-path> <label>
  local ref="$1" out="$2" label="$3" rc=0
  klt lvs - --format json > "$out" <<JSON || rc=$?
{"layout": {"netlist": "$LAYOUT_NETLIST", "top": "$TOP"},
 "reference": {"netlist": "$ref", "top": "$TOP",
               "form": "gate-level-verilog", "library": "sky130_fd_sc_hd",
               "pdk": "$PDK"}}
JSON
  # `klt lvs --help` documents the contract: 0 is a verdict, 3 is a mismatch
  # verdict, and 1 is a clean error that writes an {"error": ...} envelope
  # instead of a report. So those two codes -- not the warm-up script's looser
  # `rc <= 3`, which predates this script ever meeting a clean error -- are
  # exactly the cases where a verdict exists to summarise.
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "puzzle-klt-lvs: klt lvs produced no report (rc=$rc) on $label -- see its error above" >&2
    return "$rc"
  fi
  python3 -I - "$out" "$label" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
pc, bv = d["power_connectivity"], d["body_verification"]
print(f"{sys.argv[2]}: status={d['status']} power_connectivity={pc['status']} "
      f"body_verification={bv['status']} mismatches={d['mismatch_count']}")
PY
}

# ---- Stage 1: the isolating probe (build/-only, never committed) ----------
#
# Same layout, same request, same library and PDK; the *only* difference from
# stage 2 is the reference's eight `\O[N] ` escaped-bracket scalar ports becoming
# one `output [7:0] O;` bus — the port form the reader does accept. So whatever
# stage 2's reader error is, it is attributable to the port names alone, and the
# rest of the compare over 1,618 instances is measured here.
echo
echo "Stage 1: isolating probe — bracket-free bus port form (build/ only)"
python3 -I - "$REFERENCE" "$PROBE_REFERENCE" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
# Port list: the eight `    \O[N] ,` entries collapse to a single `    O,`.
text = re.sub(r"[ \t]*\\O\[0\] ,\n", "    O,\n", text, count=1)
text = re.sub(r"[ \t]*\\O\[[1-7]\] ,\n", "", text)
# Direction declarations: eight scalars collapse to one bus declaration.
text = re.sub(r"[ \t]*output \\O\[0\] ;\n", " output [7:0] O;\n", text, count=1)
text = re.sub(r"[ \t]*output \\O\[[1-7]\] ;\n", "", text)
# Body: `.X(\O[N] )` becomes a bit-select on the bus, `.X(O[N])`.
text = re.sub(r"\\O\[([0-7])\] ", r"O[\1]", text)
assert "\\O[" not in text, "an escaped-bracket O port survived the transform"
assert text.count("output [7:0] O;") == 1, "bus declaration was not emitted exactly once"
open(dst, "w").write(text)
print(f"  wrote {dst}: eight '\\O[N] ' scalar ports -> one 'output [7:0] O;' bus")
PY
run_lvs "$PROBE_REFERENCE" "$BUILD/puzzle-klt-lvs-probe.json" "probe(bus-port)"

# ---- Stage 2: the committed reference, unmodified -------------------------
#
# This is the deliverable compare. Today it exits 1 at reference conversion
# (klayout-tools#5693); the error is left to surface and stops the script.
echo
echo "Stage 2: evidence/puzzle-extracted.v as committed"
# Written under build/ first so a run that produces no report leaves no
# zero-byte placeholder in the committed evidence/ tree.
STAGED="$BUILD/puzzle-klt-lvs-01.json"
rc=0
run_lvs "$REFERENCE" "$STAGED" "puzzle-extracted.v" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "puzzle-klt-lvs: no report produced for $REFERENCE; nothing installed to evidence/" >&2
  exit "$rc"
fi
cp "$STAGED" evidence/puzzle-klt-lvs-01.json
echo "  envelope: evidence/puzzle-klt-lvs-01.json ($(wc -c < evidence/puzzle-klt-lvs-01.json) bytes)"
