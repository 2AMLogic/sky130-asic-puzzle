#!/usr/bin/env python3
"""CLI: replay a recorded VCD's inputs against a netlist and diff the outputs.

This is stage 6 of `spec/puzzle.md` — the gate on stages 7 and 8. It needs an
extracted netlist to be pointed at `puzzle/example_inputs.vcd`, which does
not exist yet (blocked on #2; see `evidence/puzzle-replay.md`). It has been
self-tested against the warm-up in the meantime (`tools/sim/selftest_replay.py`).

Once an extracted puzzle netlist exists, the intended invocation is:

    python3 -m tools.sim.run_vcd_replay \\
        --netlist evidence/puzzle-extracted.v \\
        --vcd puzzle/example_inputs.vcd \\
        --top puzzle \\
        --inputs clk,rst_n,enable,I \\
        --outputs O,success \\
        --port-map "clk=clk,rst_n=rst_n,enable=enable,I=I,success=success,O=\\O[0]:\\O[1]:\\O[2]:\\O[3]:\\O[4]:\\O[5]:\\O[6]:\\O[7]"

`--port-map` defaults to the identity map (recorded VCD signal name == DUT
port name) when omitted; pass explicit `recorded=dut` pairs if the extracted
netlist's top-level ports were renamed. For a recorded signal wider than 1
bit whose DUT has no vector port for it — the common case for a netlist
extracted straight from GDS pin labels, which declares one scalar port per
bit (e.g. `\\O[0]` .. `\\O[7]`) rather than a `[7:0]` vector — give a
colon-separated list of `width` DUT port names instead of one name, ordered
bit 0 (LSB) first: `O=\\O[0]:\\O[1]:...:\\O[7]`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sim.pdk import PdkResolutionError
from tools.sim.replay import run_vcd_replay


def _parse_port_map(raw: str | None, names: list[str]) -> dict[str, str | list[str]]:
    if not raw:
        return {n: n for n in names}
    mapping: dict[str, str | list[str]] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        k, _, v = pair.partition("=")
        if not v:
            mapping[k] = k
        elif ":" in v:
            mapping[k] = v.split(":")
        else:
            mapping[k] = v
    for n in names:
        mapping.setdefault(n, n)
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--netlist", action="append", required=True, help="netlist Verilog file (repeatable)")
    parser.add_argument("--vcd", required=True, help="recorded VCD to replay")
    parser.add_argument("--top", required=True, help="DUT top module name")
    parser.add_argument("--inputs", required=True, help="comma-separated recorded input signal names")
    parser.add_argument("--outputs", required=True, help="comma-separated recorded output signal names")
    parser.add_argument(
        "--port-map",
        default=None,
        help="comma-separated recorded=dut pairs; default identity. A dut value may be a "
        "colon-separated list of per-bit port names (bit 0 first) for a multi-bit signal "
        "with no vector port, e.g. O=\\O[0]:\\O[1]:...:\\O[7]",
    )
    parser.add_argument("--margin", type=int, default=1000, help="extra sim time after the last recorded event")
    parser.add_argument("--work-dir", default=".sim-work/replay", help="scratch directory for generated sources")
    args = parser.parse_args(argv)

    netlist_files = [Path(p) for p in args.netlist]
    for p in netlist_files:
        if not p.exists():
            print(f"error: netlist file not found: {p}", file=sys.stderr)
            return 2

    vcd_path = Path(args.vcd)
    if not vcd_path.exists():
        print(f"error: VCD file not found: {vcd_path}", file=sys.stderr)
        return 2

    input_names = [s.strip() for s in args.inputs.split(",") if s.strip()]
    output_names = [s.strip() for s in args.outputs.split(",") if s.strip()]
    port_map = _parse_port_map(args.port_map, input_names + output_names)

    try:
        result = run_vcd_replay(
            netlist_files,
            vcd_path,
            top=args.top,
            port_map=port_map,
            input_names=input_names,
            output_names=output_names,
            work_dir=Path(args.work_dir),
            margin=args.margin,
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

    print(f"Compared through t={result.compared_through} ({result.recorded.timescale if result.recorded else '?'} units)")
    if result.simulated_vcd_path:
        print(f"Simulated trace: {result.simulated_vcd_path}")

    if result.ok:
        print("\nRESULT PASS — no divergence over the entire recorded trace")
        return 0

    d = result.first_divergence
    if d is not None:
        print(f"\nRESULT FAIL — first divergence at t={d.time} signal={d.signal}")
        print(f"  expected: {d.expected}")
        print(f"  actual:   {d.actual}")
    else:
        print("\nRESULT FAIL — simulation did not produce a comparable trace")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
