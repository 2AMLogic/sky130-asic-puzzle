#!/usr/bin/env bash
# Run `klt lvs` on the warm-up layout against its published gate-level netlists
# (issue #47). Third-party layout + published ground truth: the case no other
# canary can test, because their layouts come out of klt itself.
#
#   puzzle/warmup/04_final.gds --klt extract (--abstract-cells)--> build/warmup-klt-lvs.spice
#   build/warmup-klt-lvs.spice --klt lvs--> puzzle/warmup/01_netlist.v                 (signal-only)
#   build/warmup-klt-lvs.spice --klt lvs--> puzzle/warmup/02_netlist_with_power_rails.v (PG pins)
#
# Writes the klt lvs envelopes to evidence/warmup-klt-lvs-{01,02}.json (committed;
# re-verify with `klt lvs --check`), with reference-side net/instance names elided. The extracted netlist stays in build/
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
# Exit 0 means the runs completed and envelopes were written, NOT that the compare
# matched; the verdicts are printed and live in the envelopes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOP="adder_demo"
WARMUP="puzzle/warmup"
BUILD="build"
LAYOUT_NETLIST="$BUILD/warmup-klt-lvs.spice"
PDK="${PDK:-sky130A}"

command -v klt >/dev/null || { echo "warmup-klt-lvs: klt not found on PATH" >&2; exit 2; }

if [ ! -f "$WARMUP/04_final.gds" ]; then
  ./scripts/fetch-puzzle.sh
fi

if ! PDK_JSON="$(klt pdk find --pdk "$PDK" --format json 2>/dev/null)"; then
  echo "warmup-klt-lvs: no '$PDK' PDK found. Point PDK_ROOT at a sky130 install" >&2
  echo "(keep it inside your worktree; do not install into shared host paths)." >&2
  exit 2
fi

# The std-cell LEF --abstract-cell-lef needs, derived from the PDK this run
# actually resolved rather than hardcoded to ~/.ciel.
LIBS_REF="$(printf '%s' "$PDK_JSON" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["assets"]["libs_ref"])')"
CELL_LEF="$LIBS_REF/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
if [ ! -f "$CELL_LEF" ]; then
  echo "warmup-klt-lvs: '$PDK' resolved to libs_ref '$LIBS_REF' but its" >&2
  echo "sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef is missing. --abstract-cells" >&2
  echo "cannot resolve the std cells' VNB/VPB pins without it, which silently" >&2
  echo "changes the verdict; install the libs.ref assets and re-run." >&2
  exit 2
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
