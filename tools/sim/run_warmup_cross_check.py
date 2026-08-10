#!/usr/bin/env python3
"""CLI: cross-check a candidate warm-up netlist against the reference netlist.

This is issue #5's second acceptance criterion: the harness run on
`evidence/warmup-extracted.v` must agree with `warmup/01_netlist.v`
cycle-for-cycle on `S`, over a shared randomized stimulus of at least 1,000
cycles — the *functional* counterpart to the structural comparator
(`tools/compare`), and an independent check: nothing here reuses or derives
from what the structural comparator already validated.

Method: record a single randomized shift-load stimulus by simulating the
*reference* netlist (`--reference`, normally `warmup/01_netlist.v`), then
replay that exact recorded input trace — the same `(A, B)` bit sequence, at
the same timestamps — against the *candidate* netlist (`--candidate`,
normally the extractor's output) via `tools.sim.replay`, and diff `S` at
every sampled timestamp. Any divergence is reported with its first
differing timestamp, not a bare pass/fail.

    python3 -m tools.sim.run_warmup_cross_check \\
        --reference puzzle/warmup/01_netlist.v \\
        --candidate evidence/warmup-extracted.v \\
        --cases 150 --seed 496
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sim.directed import DEFAULT_PORTS, default_cases
from tools.sim.pdk import PdkResolutionError
from tools.sim.replay import run_vcd_replay
from tools.sim.warmup_recorder import REPLAY_PORT_MAP, record_shift_load_vcd
from tools.vcd.reader import read_vcd

# Each shift-load case advances the clock ~10 half-periods (2 reset edges +
# 8 shift edges) -> ~5 clock cycles/case, plus a non-clocked settle tail.
# 150 cases comfortably clears the 1,000-cycle acceptance-criterion floor;
# pass --cases to override.
DEFAULT_CASES = 150


def _count_clock_cycles(recorded_vcd_path: Path) -> int:
    """Count rising edges of `clk` in the recorded trace.

    Deliberately not derived from `compared_through / period_ns`: the raw
    VCD timestamp unit is whatever precision the compiled design resolves
    to (the finest `` `timescale `` among all compiled sources, including
    the PDK model files) — dividing a raw timestamp by a hardcoded
    nanosecond period silently assumes that unit is nanoseconds, which it
    usually is not (Icarus commonly resolves to picoseconds once the PDK
    models are linked in). Counting actual `clk` transitions sidesteps the
    unit question entirely.
    """
    doc = read_vcd(recorded_vcd_path)
    history = doc.signal_history("clk")
    return sum(1 for _t, v in history if v == "1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", required=True, help="reference netlist (e.g. warmup/01_netlist.v)")
    parser.add_argument("--candidate", required=True, help="candidate netlist to check (e.g. an extracted netlist)")
    parser.add_argument("--top", default="adder_demo", help="top module name (default: adder_demo)")
    parser.add_argument("--cases", type=int, default=DEFAULT_CASES, help="randomized (A,B) cases to drive")
    parser.add_argument("--seed", type=int, default=496, help="seed for the randomized cases")
    parser.add_argument("--work-dir", default=".sim-work/warmup-cross-check", help="scratch directory")
    args = parser.parse_args(argv)

    reference = Path(args.reference)
    candidate = Path(args.candidate)
    for label, p in (("--reference", reference), ("--candidate", candidate)):
        if not p.exists():
            print(f"error: {label} file not found: {p}", file=sys.stderr)
            return 2

    work_dir = Path(args.work_dir)
    cases = default_cases(extra_random=args.cases, seed=args.seed)

    print(f"Reference netlist: {reference}")
    print(f"Candidate netlist: {candidate}")
    print(f"Cases: {len(cases)} ({args.cases} randomized + 10 fixed directed, seed={args.seed})")

    try:
        recorded_vcd = (work_dir / "recorded.vcd").resolve()
        record_shift_load_vcd(
            reference, cases, recorded_vcd, work_dir / "record", top=args.top, ports=DEFAULT_PORTS
        )
    except (PdkResolutionError, RuntimeError) as e:
        print(f"error recording reference stimulus: {e}", file=sys.stderr)
        return 1

    print(f"Recorded stimulus: {recorded_vcd}")

    try:
        result = run_vcd_replay(
            [candidate],
            recorded_vcd,
            top=args.top,
            port_map=REPLAY_PORT_MAP,
            input_names=["clk", "rst_n", "en", "A", "B"],
            output_names=["S"],
            work_dir=work_dir / "replay",
        )
    except PdkResolutionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print()
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

    cycles = _count_clock_cycles(recorded_vcd)
    print(f"Compared through t={result.compared_through} ({result.recorded.timescale if result.recorded else '?'} units)")
    print(f"Clock cycles covered: {cycles} (counted rising edges of clk in the recorded stimulus)")

    if result.ok:
        print("\nRESULT PASS — candidate agrees with reference on S over the entire shared stimulus")
        return 0

    d = result.first_divergence
    if d is not None:
        print(f"\nRESULT FAIL — first divergence at t={d.time} signal={d.signal}")
        print(f"  reference (expected): {d.expected}")
        print(f"  candidate (actual):   {d.actual}")
    else:
        print("\nRESULT FAIL — simulation did not produce a comparable trace")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
