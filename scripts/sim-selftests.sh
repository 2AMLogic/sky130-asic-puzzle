#!/usr/bin/env bash
# The tools/sim self-test gate (issue #108): one entry point CI calls.
#
# CI ran exactly one tools/sim module before this script existed —
# selftest_cli (issue #102, kept where it is, ahead of the fetch, on
# purpose) — while the five library self-tests and the directed warm-up run
# never executed anywhere automated. This script runs them, reporting one
# ok/skip/FAIL line per module in scripts/lint.sh's note() format, so a skip
# is visible and a failure is fatal.
#
# What runs, and what each needs:
#
#   tools.sim.selftest_pdk      — always (no external dependency at all)
#   tools.sim.selftest_icarus   — iverilog (issue #178: the wrapper's
#                               compiled/ran semantics, exercised with tiny
#                               PDK-free testbenches — clean, compile-error,
#                               fatal-after-pass — plus the fatal shape
#                               through the real verify_by_simulation gate)
#   tools.sim.selftest_answer   — iverilog
#   tools.sim.selftest_portmap  — iverilog + resolvable sky130 models
#   tools.sim.selftest_celltable — resolvable sky130 models (the golden
#                               69-cell check; issue #122). No iverilog, no
#                               fetched netlist. The fixture and negative
#                               control need nothing, but the module is
#                               gated here on HAVE_MODELS so the gate line
#                               reflects the golden check this exists for.
#   tools.sim.selftest_replay   — iverilog + models + puzzle/warmup/01_netlist.v
#   tools.sim.run_warmup_directed --netlist puzzle/warmup/01_netlist.v --random 10
#                               — the shift-load protocol's SEMANTIC gate
#                                 (expected_s from A + B == 496). The same
#                                 prerequisites as selftest_replay. This one
#                                 is why the script exists alongside
#                                 selftest_replay: the replay self-test
#                                 records and replays against the same
#                                 netlist, so a recorder-protocol mutation
#                                 moves both sides together and still passes;
#                                 the directed run's expected_s does not move.
#   tools.sim.selftest_solve    — iverilog + resolvable sky130 models +
#                                 puzzle/warmup/01_netlist.v + python-sat
#                                 (pinned in CI): the solver stack's
#                                 known-answer check against the warm-up,
#                                 gated in by issue #118. Skipped, naming
#                                 whichever prerequisite is missing, so the
#                                 coverage gap stays legible in the log
#                                 instead of silently absent.
#
# A missing iverilog, models or python-sat is a reported skip and exit 0 by
# default; --require-pdk turns that into a hard failure naming what was
# missing (mirroring warmup-regression.sh's --require-klt), so CI can never
# go green on a silently skipped gate. A missing netlist is always a
# reported skip — run this after scripts/fetch-puzzle.sh in CI. Scratch
# output lands in .sim-work/ (gitignored), so the tree stays clean.
#
# Flags: --require-pdk (a missing iverilog, models or python-sat is a
# failure, not a skip).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REQUIRE_PDK=0
for arg in "$@"; do
  case "$arg" in
    --require-pdk) REQUIRE_PDK=1 ;;
    -h|--help) sed -n '2,/^[^#]/{ /^[^#]/d; p; }' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "sim-selftests: unknown argument $arg" >&2; exit 2 ;;
  esac
done

NETLIST="puzzle/warmup/01_netlist.v"

fail=0
note() { printf '  %-8s %s\n' "$1" "$2"; }

run_py() {
  # run_py <display-name> <python.module> [args...] — run one module; its own
  # output goes to the log verbatim, then one note line records the verdict.
  local name="$1" module="$2"
  shift 2
  echo "running: python3 -m $module $*"
  if python3 -m "$module" "$@"; then
    note "ok" "$name"
  else
    note "FAIL" "$name (output above)"; fail=1
  fi
}

hr() { printf '%s\n' "------------------------------------------------------------"; }

hr
echo "tools/sim self-tests (issue #108)"
hr

# Probe prerequisites once, up front, so each module's skip line can name
# what is missing instead of each module tracebacking on its own.
HAVE_IV=0
if command -v iverilog >/dev/null 2>&1; then HAVE_IV=1; fi
HAVE_MODELS=0
if python3 -c 'from tools.sim.pdk import resolve_sky130_models; resolve_sky130_models()' >/dev/null 2>&1; then
  HAVE_MODELS=1
fi
HAVE_NETLIST=0
if [ -f "$NETLIST" ]; then HAVE_NETLIST=1; fi
HAVE_PYSAT=0
if python3 -c 'import pysat' >/dev/null 2>&1; then HAVE_PYSAT=1; fi
echo "prerequisites: iverilog=$HAVE_IV sky130_models=$HAVE_MODELS warmup_netlist=$HAVE_NETLIST python_sat=$HAVE_PYSAT"

# 1. PDK resolver self-test — mocks every source, so it always runs.
run_py "tools.sim.selftest_pdk" tools.sim.selftest_pdk

# 2. Icarus wrapper semantics self-test — clean / compile-error /
#    fatal-after-pass against tiny hand-written testbenches, and the same
#    fatal shape through verify_by_simulation. Needs iverilog only.
if [ "$HAVE_IV" -eq 1 ]; then
  run_py "tools.sim.selftest_icarus" tools.sim.selftest_icarus
else
  note "skip" "tools.sim.selftest_icarus — iverilog not found"
fi

# 3. Known-answer decode self-test — synthetic DUT, needs iverilog only.
if [ "$HAVE_IV" -eq 1 ]; then
  run_py "tools.sim.selftest_answer" tools.sim.selftest_answer
else
  note "skip" "tools.sim.selftest_answer — iverilog not found"
fi

# 4. Multi-bit port-map self-test — needs iverilog + models (run_vcd_replay
#    links the model files unconditionally, even for the synthetic DUT).
if [ "$HAVE_IV" -eq 1 ] && [ "$HAVE_MODELS" -eq 1 ]; then
  run_py "tools.sim.selftest_portmap" tools.sim.selftest_portmap
else
  note "skip" "tools.sim.selftest_portmap — needs iverilog + resolvable sky130 models"
fi

# 5. Celltable port-direction self-test — the golden 69-cell check resolves
#    the sky130 models with resolve_sky130_models() (issue #122), so it runs
#    wherever a PDK is installed, not only on the baseline's recording host.
#    Needs models only — no iverilog, no fetched netlist.
if [ "$HAVE_MODELS" -eq 1 ]; then
  run_py "tools.sim.selftest_celltable" tools.sim.selftest_celltable
else
  note "skip" "tools.sim.selftest_celltable — needs resolvable sky130 models (the golden 69-cell check)"
fi

# 6. Replay self-test + the directed run — both read the warm-up netlist.
#    The directed run is the protocol's semantic gate: its cases carry
#    expected_s derived from A + B == 496, which a recorder mutation cannot
#    move (see the header comment for why selftest_replay alone cannot).
if [ "$HAVE_IV" -eq 1 ] && [ "$HAVE_MODELS" -eq 1 ] && [ "$HAVE_NETLIST" -eq 1 ]; then
  run_py "tools.sim.selftest_replay" tools.sim.selftest_replay
  run_py "tools.sim.run_warmup_directed --random 10 (shift-load protocol, 20 cases)" \
    tools.sim.run_warmup_directed --netlist "$NETLIST" --random 10
else
  note "skip" "tools.sim.selftest_replay — needs iverilog + models + $NETLIST (run ./scripts/fetch-puzzle.sh)"
  note "skip" "tools.sim.run_warmup_directed — needs iverilog + models + $NETLIST (run ./scripts/fetch-puzzle.sh)"
fi

# 7. Solver self-test — the solver stack's known-answer check against the
#    warm-up, gated in by issue #118. It needs everything the replay pair
#    needs plus python-sat. The probe is load-bearing, not cosmetic:
#    selftest_solve guards pysat itself and exits 1 when it is missing,
#    and run_py records any non-zero exit as FAIL — so an unguarded run
#    would turn a green suite on a python-sat-less host into a hard failure.
solve_missing=""
if [ "$HAVE_IV" -eq 0 ]; then solve_missing="iverilog"; fi
if [ "$HAVE_MODELS" -eq 0 ]; then solve_missing="${solve_missing:+$solve_missing, }resolvable sky130 models"; fi
if [ "$HAVE_NETLIST" -eq 0 ]; then solve_missing="${solve_missing:+$solve_missing, }$NETLIST"; fi
if [ "$HAVE_PYSAT" -eq 0 ]; then solve_missing="${solve_missing:+$solve_missing, }python-sat"; fi
if [ -z "$solve_missing" ]; then
  run_py "tools.sim.selftest_solve" tools.sim.selftest_solve
else
  note "skip" "tools.sim.selftest_solve — missing: $solve_missing"
fi

# --require-pdk (CI): a missing iverilog, models or python-sat must fail the
# run, not skip it — a gate that cannot run must never look like one that
# passed.
missing=""
if [ "$HAVE_IV" -eq 0 ]; then missing="iverilog"; fi
if [ "$HAVE_MODELS" -eq 0 ]; then missing="${missing:+$missing, }resolvable sky130 models"; fi
if [ "$HAVE_PYSAT" -eq 0 ]; then missing="${missing:+$missing, }python-sat"; fi
if [ "$REQUIRE_PDK" -eq 1 ] && [ -n "$missing" ]; then
  echo "FAILED — --require-pdk was given, but missing: $missing." >&2
  exit 1
fi

hr
if [ "$fail" -ne 0 ]; then
  echo "SIM SELF-TESTS FAILED" >&2
  exit 1
fi
echo "tools/sim self-tests passed."
