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
# committed reference, deliberately. `klt lvs` could not read
# evidence/puzzle-extracted.v until klayout-tools#5693 was fixed (closed by
# #7452, merge `6ca7e00` — first in the dev line, no released klt carries it
# yet): its eight escaped-bracket scalar ports `\O[0] … \O[7] ` tripped the
# gate-level-verilog reader's port-list check and it exited 1 before any
# compare (Run 1, and re-demonstrated on the old build in Run 2). The probe's
# own stage fails soft: a probe-side hard error (klt's documented exit 1 or
# worse) is reported on stderr with its rc and stage 2 is still attempted, so
# the probe can never suppress the deliverable compare. The probe is build/-
# only and nothing committed depends on it. There is no workaround for a
# reader defect in this script: the error is left to surface verbatim
# (CLAUDE.md §2).
#
# Exit 0 means both stages completed AND the stage 2 verdict equals the pins
# in evidence/puzzle-klt-lvs-expected.json (#165): tools/lvs-verdict --
# PDK-free, self-tested by tools/test-lvs-verdict -- compares the fresh
# envelope after the reference has run and names any moved value with its
# direction. The pinned mismatch is tool-side (klayout-tools#7561:
# --abstract-cells joins routed pads of one pin even when one side is an
# anonymous net, which on this layout shorts four driven nets into VGND);
# a run that instead reports match means the upstream fix has landed --
# promote the pin, never loosen the gate. A klt lvs crash (rc > 3) and a
# stage 2 that produces no report (a reader error, pre-#7452 klt) stay hard
# errors: the script propagates the exit code and leaves any previously
# installed envelope in evidence/ untouched.
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

# Shared klt/PDK/LEF preamble (scripts/lib/klt-lvs-preamble.sh): sets
# PDK_JSON, LIBS_REF and CELL_LEF, exiting 2 with this prefix on any missing
# prerequisite. Sourced, so the variables land in this script's scope.
source scripts/lib/klt-lvs-preamble.sh 'puzzle-klt-lvs'

if [ ! -f "$LAYOUT_GDS" ]; then
  ./scripts/fetch-puzzle.sh
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
run_lvs "$PROBE_REFERENCE" "$BUILD/puzzle-klt-lvs-probe.json" "probe(bus-port)" \
  || echo "puzzle-klt-lvs: probe failed (rc=$?) — continuing to stage 2" >&2

# ---- Stage 2: the committed reference, unmodified -------------------------
#
# This is the deliverable compare. A klt without the klayout-tools#5693 fix
# exits 1 here at reference conversion; the error is left to surface, stops
# the script and leaves any previously installed envelope untouched.
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

# Verdict gate (#165): the fresh envelope exists now, so compare it against
# the pinned expectations before exiting -- a completed run that moved the
# verdict fails, with the moved value and its direction named.
exec "$ROOT/tools/lvs-verdict" evidence/puzzle-klt-lvs-expected.json \
  01:evidence/puzzle-klt-lvs-01.json
