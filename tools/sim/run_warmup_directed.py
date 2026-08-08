#!/usr/bin/env python3
"""CLI: run the directed `A + B == 496` test against a shift/adder/comparator netlist.

    python3 -m tools.sim.run_warmup_directed \\
        --netlist puzzle/warmup/01_netlist.v \\
        --random 50

Prints model provenance (PDK variant/version/path — see tools/sim/pdk.py),
then one PASS/MISMATCH line per case, then a final PASS/FAIL summary. Exits
non-zero on any mismatch, a PDK resolution failure, or a compile/run failure
— never silently green.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sim.directed import default_cases, run_directed_test
from tools.sim.pdk import PdkResolutionError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", action="append", required=True, help="netlist Verilog file (repeatable)")
    parser.add_argument("--top", default="adder_demo", help="top module name (default: adder_demo)")
    parser.add_argument("--random", type=int, default=0, help="extra randomized (A,B) cases to add")
    parser.add_argument("--seed", type=int, default=496, help="seed for --random cases")
    parser.add_argument("--work-dir", default=".sim-work/directed", help="scratch directory for generated sources")
    args = parser.parse_args(argv)

    netlist_files = [Path(p) for p in args.netlist]
    for p in netlist_files:
        if not p.exists():
            print(f"error: netlist file not found: {p}", file=sys.stderr)
            return 2

    cases = default_cases(extra_random=args.random, seed=args.seed)

    try:
        result = run_directed_test(
            netlist_files,
            top=args.top,
            cases=cases,
            work_dir=Path(args.work_dir),
        )
    except PdkResolutionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(result.models.describe())
    print()

    if not result.sim.compiled:
        print("COMPILE FAILED", file=sys.stderr)
        print(result.sim.compile_stderr, file=sys.stderr)
        return 1
    if not result.sim.ran:
        print("SIMULATION DID NOT RUN", file=sys.stderr)
        print(result.sim.run_stderr, file=sys.stderr)
        return 1

    for o in result.outcomes:
        status = "OK" if o.matched else "MISMATCH"
        print(f"{status:9} {o.label:16} a={o.a:3} b={o.b:3} expected_s={int(o.expected_s)} got_s={o.got_s}")

    print()
    print(f"RESULT {'PASS' if result.ok else 'FAIL'} ({len(result.outcomes)} cases)")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
