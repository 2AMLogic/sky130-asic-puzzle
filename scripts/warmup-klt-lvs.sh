#!/usr/bin/env bash
# Run `klt lvs` on the warm-up layout against its published gate-level netlists
# (issue #47). Third-party layout + published ground truth: the case no other
# canary can test, because their layouts come out of klt itself.
#
#   puzzle/warmup/04_final.gds --klt extract (--abstract-cells)--> build/warmup-klt-lvs.spice
#   build/warmup-klt-lvs.spice --klt lvs--> puzzle/warmup/01_netlist.v                 (signal-only)
#   build/warmup-klt-lvs.spice --klt lvs--> puzzle/warmup/02_netlist_with_power_rails.v (PG pins)
#
# Writes the klt lvs envelopes to evidence/warmup-klt-lvs-{01,02}.json (committed,
# with reference-side net/instance names elided). The pinned verdicts those
# envelopes are compared against live in evidence/warmup-klt-lvs-expected.json;
# the envelopes are rewritten on every run, so they cannot be their own
# expectation. `klt lvs --check` re-verifies the committed envelopes from the
# repo root again (exit 0 on both, 2026-11-20, klt 0.9.3.dev2572): Run 2's
# nested-clone path anchoring (klayout-tools#5631, since fixed upstream) no
# longer reproduces -- see evidence/warmup-klt-lvs.md, Run 2 and the
# pinned-expectation section. The extracted netlist stays in build/
# (gitignored): it is derived from a file that carries no license (CLAUDE.md §3).
# Never reads puzzle/puzzle.gds.
#
# Needs a sky130 PDK. Set PDK_ROOT to one, or have it under ~/.ciel. klt lvs has
# no --pdk CLI flag, but its request carries `reference.pdk`/`reference.pdk_root`
# (documented since before Run 1, and what klayout-tools#3748's fix points at in
# its error text), so the variant is named in the request rather than exported.
# $PDK here is only this script's own default, passed explicitly to the two
# commands that take it. A missing PDK is a hard error: this never silently skips.
#
# `klt extract --abstract-cells` is given the PDK's own sky130_fd_sc_hd.lef via
# --abstract-cell-lef: without it the std-cell black boxes carry no VNB pin, and
# the fix for klayout-tools#3749 (which merges the LEF's pins into a labelled
# cell's pin list) never engages. See evidence/warmup-klt-lvs.md, Run 2.
#
# Exit 0 means the runs completed AND both verdicts equal the pins in
# evidence/warmup-klt-lvs-expected.json (#158): 01 match, 02 the recorded
# tool-side mismatch of klayout-tools#5632. tools/lvs-verdict -- PDK-free,
# self-tested by tools/test-lvs-verdict -- compares both envelopes after both
# references have run, so one run reports both verdicts, and names any moved
# value with its direction. Any move fails, including 02 turning into a match:
# that is a stale pin to promote after the upstream fix, not a pass. A klt
# crash (rc > 3) stays a hard error, above.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOP="adder_demo"
WARMUP="puzzle/warmup"
BUILD="build"
LAYOUT_NETLIST="$BUILD/warmup-klt-lvs.spice"
PDK="${PDK:-sky130A}"

# Shared klt/PDK/LEF preamble (scripts/lib/klt-lvs-preamble.sh): sets
# PDK_JSON, LIBS_REF and CELL_LEF, exiting 2 with this prefix on any missing
# prerequisite. Sourced, so the variables land in this script's scope.
source scripts/lib/klt-lvs-preamble.sh 'warmup-klt-lvs'

if [ ! -f "$WARMUP/04_final.gds" ]; then
  ./scripts/fetch-puzzle.sh
fi

mkdir -p "$BUILD" evidence
klt --version

klt extract "$WARMUP/04_final.gds" --deck sky130 --pdk "$PDK" --top "$TOP" \
  --abstract-cells 'sky130_fd_sc_hd__*' --abstract-cell-lef "$CELL_LEF" \
  --def-pins "$WARMUP/03_post_place_and_route.def" \
  -o "$LAYOUT_NETLIST" --format json > "$BUILD/warmup-klt-lvs-extract.json"

for ref in 01:01_netlist 02:02_netlist_with_power_rails; do
  tag="${ref%%:*}"; name="${ref#*:}"
  out="evidence/warmup-klt-lvs-$tag.json"
  # Request on stdin so paths are relative to the repo root, the same base
  # `klt lvs --check` resolves them against when re-run from the repo root.
  rc=0
  klt lvs - --format json > "$out" <<JSON || rc=$?
{"layout": {"netlist": "$LAYOUT_NETLIST", "top": "$TOP"},
 "reference": {"netlist": "$WARMUP/$name.v", "top": "$TOP",
               "form": "gate-level-verilog", "library": "sky130_fd_sc_hd",
               "pdk": "$PDK"}}
JSON
  # exit 3 is a mismatch verdict, not a failure to run
  [ "$rc" -le 3 ] || { echo "warmup-klt-lvs: klt lvs crashed (rc=$rc) on $name" >&2; exit "$rc"; }
  python3 -I - "$out" "$name" <<'PY'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
# Reference-side identifiers come from an unlicensed upstream netlist
# (CLAUDE.md §3); evidence/warmup-regression.md elides them too. Verdict
# fields and the sha256 inputs `klt lvs --check` reads are left untouched.
d.pop("net_correspondence", None)
for m in d["mismatches"]:
    if isinstance(m.get("instance"), dict) and m["instance"].get("reference"):
        m["instance"]["reference"] = "<elided>"
with open(path, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")
pc = d["power_connectivity"]
print(f"{sys.argv[2]}: status={d['status']} power_connectivity={pc['status']} "
      f"body_verification={d['body_verification']['status']} mismatches={d['mismatch_count']}")
PY
done

# Verdict gate (#158): both envelopes exist now, so compare them against the
# pinned expectations before exiting -- a completed run that moved either
# verdict fails, with the moved value and its direction named.
exec "$ROOT/tools/lvs-verdict" evidence/warmup-klt-lvs-expected.json \
  01:evidence/warmup-klt-lvs-01.json 02:evidence/warmup-klt-lvs-02.json
