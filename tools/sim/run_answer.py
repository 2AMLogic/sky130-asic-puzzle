"""CLI: stage 8 — simulate the output generator with the solved inputs.

    python3 -m tools.sim.run_answer --netlist evidence/puzzle-extracted.v \\
        --active-cycles 121 --observe-cycles 30

Reuses stage 7's pipeline (`tools/sim/solve.py`) end to end rather than
retyping the solved 121-bit sequence recorded in `evidence/puzzle-solve.md`
§5 into a second place: the same bounded-model-checking call that proved it
unique is re-run here (it takes under a second — see `evidence/puzzle-solve.md`
§4), so there is exactly one source of truth for the answer's input, and this
script's own run is independent evidence that the sequence still reproduces
against the current netlist.

The one thing stage 7 did not need and stage 8 does: the simulation window
is extended past the goal cycle (`--observe-cycles`, appended after
`--solve-tail-cycles`) so the output generator has room to keep emitting
after `success` asserts, and the watched outputs include `O[0]`..`O[7]`
alongside `success`. The per-cycle bits are decoded into bytes under both
candidate bit orders (`tools/sim/answer.py`) — neither is assumed — and the
longest printable run is reported as the message.

Exit status: 0 on a decoded message, 1 when stage 7's re-solve is UNSAT
(should not happen if `evidence/puzzle-solve.md` still holds), 2 on a usage,
verification, or environment failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sim.answer import decode_output_cycles, select_order
from tools.sim.solve import (
    enumerate_solutions,
    load_design,
    verify_by_simulation,
    windowed_scenario,
)
from tools.sim.testbench import SequenceExpectation

EXIT_OK = 0
EXIT_UNSAT = 1
EXIT_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.sim.run_answer")
    ap.add_argument("--netlist", required=True, type=Path)
    ap.add_argument("--clock-port", default="clk")
    ap.add_argument("--reset-port", default="rst_n")
    ap.add_argument("--enable-port", default="enable")
    ap.add_argument("--goal", default="success", help="output port that gates the message")
    ap.add_argument("--free", action="append", default=None,
                    help="input port the solver may choose (repeatable)")
    ap.add_argument("--output", action="append", default=None,
                    help="one watched output bit port, escaped-identifier form "
                         "(repeatable); default \\O[0]..\\O[7]")
    ap.add_argument("--reset-cycles", type=int, default=3)
    ap.add_argument("--idle-cycles", type=int, default=1)
    ap.add_argument("--active-cycles", type=int, default=121)
    ap.add_argument("--solve-tail-cycles", type=int, default=5,
                    help="tail cycles used to re-derive the stage-7 answer "
                         "(must match evidence/puzzle-solve.md for the same goal cycle)")
    ap.add_argument("--observe-cycles", type=int, default=30,
                    help="extra idle cycles appended after the solved window, "
                         "to give the message room to finish")
    ap.add_argument("--solver", default="cadical195")
    ap.add_argument("--clock-period-ns", type=int, default=10)
    ap.add_argument("--work-dir", type=Path, default=Path(".sim-work/answer"))
    ap.add_argument("--table-cache", type=Path, default=None)
    args = ap.parse_args(argv)

    if not args.netlist.exists():
        print(f"no such netlist: {args.netlist}", file=sys.stderr)
        return EXIT_ERROR
    try:
        import pysat  # noqa: F401
    except ImportError:
        print("python-sat is not installed — `pip install python-sat`", file=sys.stderr)
        return EXIT_ERROR

    design = load_design(
        args.netlist,
        work_dir=args.work_dir,
        table_cache=args.table_cache,
        clock_port=args.clock_port,
    )
    print(design.pdk.describe())
    print()
    print(f"Netlist: {args.netlist} (top `{design.netlist.top}`)")
    print(f"Cell truth tables: {len(design.tables)} cell types, measured from the models above")

    free_ports = args.free or [
        p for p in design.model.inputs
        if p not in (args.clock_port, args.reset_port, args.enable_port)
    ]
    output_ports = args.output or [f"\\O[{b}]" for b in range(8)]

    print()
    print("== re-deriving the stage-7 solved input sequence (same machinery, not retyped) ==")
    scenario = windowed_scenario(
        design.model,
        reset_cycles=args.reset_cycles,
        idle_cycles=args.idle_cycles,
        active_cycles=args.active_cycles,
        tail_cycles=args.solve_tail_cycles,
        free_ports=free_ports,
        enable_port=args.enable_port,
        reset_port=args.reset_port,
        goal_output=args.goal,
    )
    report = enumerate_solutions(
        design.model, scenario, free_ports=free_ports, max_solutions=1, solver_name=args.solver,
    )
    if report.unsat:
        print(f"RESULT UNSAT at bound {report.bound} — no solved sequence to replay; "
              "this contradicts evidence/puzzle-solve.md and should be investigated, not worked around")
        return EXIT_UNSAT
    solution = report.solutions[0]
    print(f"CNF: {report.stats['vars']} variables, {report.stats['clauses_total']} clauses")
    print(f"Solver: {report.solver}   solve time: {report.seconds_total:.2f}s")
    print(f"Goal: {args.goal} == 1 at cycle {scenario.goal_cycle}")
    for port in free_ports:
        cycles = scenario.free_cycles(port)
        bits = "".join(str(b) for b in solution.bits(port, cycles))
        print(f"  {port}[{cycles[0]}..{cycles[-1]}] = {bits}")

    obs_start = args.reset_cycles + args.idle_cycles + args.active_cycles
    total_cycles = scenario.cycles + args.observe_cycles
    drive: dict[str, list[int]] = {}
    for port in design.model.inputs:
        if port == args.clock_port:
            continue
        values = [solution.inputs[t].get(port, 0) for t in range(scenario.cycles)]
        # Extend with the same idle state windowed_scenario uses outside the
        # active window — reset stays deasserted, everything else stays 0 —
        # so the tail feeds the design nothing new; it only gives the output
        # generator time to keep running.
        idle = 1 if port == args.reset_port else 0
        values += [idle] * args.observe_cycles
        drive[port] = values

    watch = [args.goal, *output_ports]
    print()
    print(f"== simulating {total_cycles} cycles ({args.observe_cycles} appended past the solved "
          f"{scenario.cycles}-cycle window) and watching {args.goal} + {', '.join(output_ports)} ==")
    result = verify_by_simulation(
        design,
        drive=drive,
        watch=watch,
        expect=[SequenceExpectation(cycle=scenario.goal_cycle, signal=args.goal, value=1)],
        work_dir=args.work_dir,
        clock_period_ns=args.clock_period_ns,
    )
    if not result.sim.compiled:
        print("compile FAILED")
        print(result.sim.compile_stderr)
        return EXIT_ERROR
    print(f"Testbench: {result.testbench}")
    print(f"Sources:   {result.command_note}")
    for line in result.sim.run_stdout.splitlines():
        if line.startswith(("RESULT ", "EXPECT FAIL")):
            print(line)
    if not result.ok:
        print(f"VERIFICATION FAILED — {args.goal} did not assert as expected at cycle {scenario.goal_cycle} "
              "in this replay")
        return EXIT_ERROR
    print(f"VERIFIED — {args.goal} asserts at cycle {scenario.goal_cycle} in a gate-level "
          "simulation of the netlist")

    bare_ports = [p.lstrip("\\").strip() for p in output_ports]
    cycles = list(range(obs_start, total_cycles))
    decoded = decode_output_cycles(result.samples, bare_ports, cycles)
    chosen = select_order(decoded)

    print()
    print(f"== decoding {', '.join(output_ports)} over cycles {obs_start}..{total_cycles - 1} "
          "(both candidate bit orders checked) ==")
    for name, res in decoded.items():
        marker = "  <- selected (longest printable run)" if name == chosen.order.name else ""
        print(f"  {name} ({'O[0]=MSB' if res.order.index0_is_msb else 'O[0]=LSB'}): "
              f"{res.printable_count}/{len(res.bytes_all)} printable bytes, "
              f"longest printable run {res.message_end - res.message_start} bytes{marker}")
        print(f"    {res.rendered()}")

    print()
    if chosen.message_end == chosen.message_start:
        print("No printable run found in either bit order — no message decoded.")
        return EXIT_ERROR

    print(f"Selected bit order: {chosen.order.name} "
          f"({'O[0] = MSB' if chosen.order.index0_is_msb else 'O[0] = LSB'})")
    print(f"Message cycles: {chosen.message_cycles[0]}..{chosen.message_cycles[-1]} "
          f"({len(chosen.message_bytes)} bytes)")
    print(f"Message: {chosen.message!r}")

    tail_len = min(5, args.observe_cycles)
    tail_bytes = chosen.bytes_all[-tail_len:] if tail_len else []
    if tail_len and len(set(tail_bytes)) > 1:
        print(f"WARNING: the last {tail_len} observed bytes are not all equal "
              f"({tail_bytes}) — --observe-cycles may be too short to have captured "
              "the whole message; consider increasing it.")

    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
