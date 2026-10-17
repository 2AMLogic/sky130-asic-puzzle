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
# no --pdk flag (see evidence/upstream.md), so the variant is exported as $PDK.
# A missing PDK is a hard error: this never silently skips.
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
export PDK="${PDK:-sky130A}"

command -v klt >/dev/null || { echo "warmup-klt-lvs: klt not found on PATH" >&2; exit 2; }

if [ ! -f "$WARMUP/04_final.gds" ]; then
  ./scripts/fetch-puzzle.sh
fi

if ! klt pdk find --pdk "$PDK" >/dev/null 2>&1; then
  echo "warmup-klt-lvs: no '$PDK' PDK found. Point PDK_ROOT at a sky130 install" >&2
  echo "(keep it inside your worktree; do not install into shared host paths)." >&2
  exit 2
fi

mkdir -p "$BUILD" evidence
klt --version

klt extract "$WARMUP/04_final.gds" --deck sky130 --pdk "$PDK" --top "$TOP" \
  --abstract-cells 'sky130_fd_sc_hd__*' --def-pins "$WARMUP/03_post_place_and_route.def" \
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
               "form": "gate-level-verilog", "library": "sky130_fd_sc_hd"}}
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
