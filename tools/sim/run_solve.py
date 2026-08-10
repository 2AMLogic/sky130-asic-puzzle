"""CLI: structural analysis, then bounded model checking, then simulation.

    python3 -m tools.sim.run_solve --netlist evidence/puzzle-extracted.v \\
        --active-cycles 121 --free I --goal success --max-solutions 2 --verify

Prints, in order and all from one run so an evidence record can quote it
verbatim: PDK model provenance, the structural report (does the state
decompose?), the CNF size and solve time at the stated bound, the solved
input sequence, whether a second solve proved it unique, and the Icarus
result for replaying that sequence against the real netlist.

Exit status: 0 when everything asked for succeeded, 1 when the instance was
UNSAT at the given bound (a legitimate, complete answer — with the bound
stated), 2 on a usage or environment error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.sim.solve import (
    enumerate_solutions,
    load_design,
    verify_by_simulation,
    windowed_scenario,
)
from tools.sim.structure import analyze, format_report
from tools.sim.testbench import SequenceExpectation

EXIT_OK = 0
EXIT_UNSAT = 1
EXIT_ERROR = 2


def _short_names(model) -> dict[str, str]:
    """Stable short labels for flops, ordered by placement in the layout.

    `tools/extract` names instances after their placement coordinates, so
    sorting on those gives a reading order that matches the layout rather
    than an arbitrary netlist order.
    """

    def key(name: str):
        parts = name.split("_")
        try:
            return (int(parts[-1]), int(parts[-2]))
        except ValueError:
            return (0, 0)

    ordered = sorted((ff.name for ff in model.ffs), key=key)
    return {n: f"F{i:02d}" for i, n in enumerate(ordered)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.sim.run_solve")
    ap.add_argument("--netlist", required=True, type=Path)
    ap.add_argument("--clock-port", default="clk")
    ap.add_argument("--reset-port", default="rst_n")
    ap.add_argument("--enable-port", default="enable")
    ap.add_argument("--goal", default="success", help="output port to drive high")
    ap.add_argument("--goal-value", type=int, default=1, choices=(0, 1))
    ap.add_argument("--free", action="append", default=None,
                    help="input port the solver may choose (repeatable)")
    ap.add_argument("--reset-cycles", type=int, default=3)
    ap.add_argument("--idle-cycles", type=int, default=1)
    ap.add_argument("--active-cycles", type=int, default=121)
    ap.add_argument("--tail-cycles", type=int, default=5)
    ap.add_argument("--max-solutions", type=int, default=1,
                    help="stop after this many; >1 also tests uniqueness")
    ap.add_argument("--solver", default="cadical195")
    ap.add_argument("--structure", action="store_true", help="print the structural report")
    ap.add_argument("--verify", action="store_true", help="replay the answer through Icarus")
    ap.add_argument("--grid-width", type=int, default=0,
                    help="also render the solved bits as a grid this many columns wide")
    ap.add_argument("--clock-period-ns", type=int, default=10)
    ap.add_argument("--work-dir", type=Path, default=Path(".sim-work/solve"))
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
    print()

    if args.structure:
        print("== structural analysis ==")
        print(format_report(analyze(design.model), short_names=_short_names(design.model)))

    free_ports = args.free or [
        p for p in design.model.inputs
        if p not in (args.clock_port, args.reset_port, args.enable_port)
    ]
    scenario = windowed_scenario(
        design.model,
        reset_cycles=args.reset_cycles,
        idle_cycles=args.idle_cycles,
        active_cycles=args.active_cycles,
        tail_cycles=args.tail_cycles,
        free_ports=free_ports,
        enable_port=args.enable_port,
        reset_port=args.reset_port,
        goal_output=args.goal,
        goal_value=args.goal_value,
    )
    print("== bounded model checking ==")
    print(f"Bound: {scenario.cycles} clock cycles "
          f"({args.reset_cycles} reset, {args.idle_cycles} idle, "
          f"{args.active_cycles} active, {args.tail_cycles} tail)")
    print(f"Free inputs: {', '.join(free_ports)} during the active window "
          f"({args.active_cycles} cycles each), pinned to 0 outside it")
    print(f"Goal: {args.goal} == {args.goal_value} at cycle {scenario.goal_cycle}")

    report = enumerate_solutions(
        design.model,
        scenario,
        free_ports=free_ports,
        max_solutions=args.max_solutions,
        solver_name=args.solver,
    )
    print(f"CNF: {report.stats['vars']} variables, {report.stats['clauses_total']} clauses")
    print(f"Solver: {report.solver}   total solve time: {report.seconds_total:.2f}s")

    if report.unsat:
        print(f"RESULT UNSAT at bound {report.bound} — no input sequence in this window "
              f"drives {args.goal} to {args.goal_value}")
        return EXIT_UNSAT

    print(f"Solutions found: {len(report.solutions)}")
    for i, solution in enumerate(report.solutions):
        for port in free_ports:
            cycles = scenario.free_cycles(port)
            bits = "".join(str(b) for b in solution.bits(port, cycles))
            print(f"  solution {i}: {port}[{cycles[0]}..{cycles[-1]}] = {bits}")
    if len(report.solutions) < args.max_solutions and report.exhausted:
        print(f"UNIQUE — a further solve with the {len(report.solutions)} solution(s) above "
              "blocked returned UNSAT, so no other input sequence works at this bound")
    elif report.exhausted:
        print("Solution space exhausted at this bound")
    else:
        print("More solutions may exist (stopped at --max-solutions)")

    if args.grid_width > 0:
        for i, solution in enumerate(report.solutions):
            for port in free_ports:
                bits = solution.bits(port, scenario.free_cycles(port))
                print(f"\n  solution {i}, {port} as a {args.grid_width}-column grid:")
                for row_start in range(0, len(bits), args.grid_width):
                    row = bits[row_start:row_start + args.grid_width]
                    print("    " + "".join("#" if b else "." for b in row))

    rc = EXIT_OK
    if args.verify:
        print()
        print("== verification by simulation (Icarus, against the real netlist) ==")
        solution = report.solutions[0]
        drive = {
            port: [solution.inputs[t].get(port, 0) for t in range(scenario.cycles)]
            for port in design.model.inputs
            if port != args.clock_port
        }
        result = verify_by_simulation(
            design,
            drive=drive,
            watch=[args.goal],
            expect=[SequenceExpectation(
                cycle=scenario.goal_cycle, signal=args.goal, value=args.goal_value
            )],
            work_dir=args.work_dir,
            clock_period_ns=args.clock_period_ns,
        )
        if not result.sim.compiled:
            print("compile FAILED")
            print(result.sim.compile_stderr)
            return EXIT_ERROR
        asserted = [int(r["cycle"]) for r in result.samples if r.get(args.goal) == "1"]
        print(f"Testbench: {result.testbench}")
        print(f"Sources:   {result.command_note}")
        print(f"Cycles where {args.goal} == 1: "
              f"{asserted if len(asserted) <= 12 else str(asserted[:12]) + ' ...'}")
        for line in result.sim.run_stdout.splitlines():
            if line.startswith(("RESULT ", "EXPECT FAIL")):
                print(line)
        if not result.ok:
            print("VERIFICATION FAILED — the solver's answer does not reproduce in simulation")
            rc = EXIT_ERROR
        else:
            print("VERIFIED — the solved sequence drives "
                  f"{args.goal} to {args.goal_value} in a gate-level simulation of the netlist")
    return rc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
