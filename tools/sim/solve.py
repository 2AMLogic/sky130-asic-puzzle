"""Solve a gate-level netlist for an output, then prove it by simulation.

This is stage 7 of `spec/puzzle.md` as a reusable pipeline, in four steps
that are deliberately separable:

  1. **Model** the netlist (`tools/sim/seqmodel.py`) using cell truth tables
     measured from the PDK (`tools/sim/celltable.py`).
  2. **Ask** the structural question first (`tools/sim/structure.py`) —
     whether the flops decompose into independent clusters, which decides
     whether a solver is even the right tool.
  3. **Solve** by bounded model checking (`tools/sim/bmc.py`): unroll to a
     stated bound, constrain the input schedule, assert the target output.
  4. **Verify** the answer by replaying it through Icarus against the real
     netlist.  Step 4 is not optional and not a formality — a solver result
     is a claim about the *encoding*, and only a simulation is a claim about
     the *netlist* (CLAUDE.md §5).

`enumerate_solutions` also supports the uniqueness question: block a found
assignment of the free inputs and re-solve.  An `UNSAT` on the second pass
is a proof that the first answer is the only one within the bound.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from tools.sim import bmc
from tools.sim.celltable import CellTable, derive_cell_tables, load_tables, save_tables
from tools.sim.icarus import SimResult, compile_and_run
from tools.sim.pdk import ResolvedModels, resolve_sky130_models
from tools.sim.seqmodel import FF_CELLS, SeqModel, build_model, simulate
from tools.sim.testbench import SequenceExpectation, build_sequence_testbench
from tools.verilog_netlist import Netlist, base_cell, is_fill, load

CYCLE_RE = re.compile(r"^CYCLE (\d+) (.*)$")


@dataclass
class LoadedDesign:
    netlist: Netlist
    model: SeqModel
    tables: dict[str, CellTable]
    pdk: ResolvedModels
    source: Path


def load_design(
    netlist_path: Path,
    *,
    work_dir: Path,
    table_cache: Path | None = None,
    clock_port: str = "clk",
) -> LoadedDesign:
    nl = load(str(netlist_path))
    pdk = resolve_sky130_models()
    needed: dict[str, set[str]] = defaultdict(set)
    for inst in nl.instances:
        if is_fill(inst.cell) or base_cell(inst.cell) in FF_CELLS:
            continue
        needed[inst.cell] |= set(inst.connections)
    tables: dict[str, CellTable] | None = None
    if table_cache is not None and table_cache.exists():
        cached = load_tables(table_cache)
        if set(needed) <= set(cached):
            tables = {c: cached[c] for c in needed}
    if tables is None:
        tables = derive_cell_tables(dict(needed), pdk, work_dir=work_dir / "celltable")
        if table_cache is not None:
            save_tables(tables, table_cache, pdk)
    model = build_model(nl, tables, clock_port=clock_port)
    return LoadedDesign(netlist=nl, model=model, tables=tables, pdk=pdk, source=netlist_path)


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------


@dataclass
class Scenario:
    """A bounded input schedule plus the property to satisfy."""

    schedule: list[dict[str, int | None]]
    goal_output: str
    goal_cycle: int
    goal_value: int = 1

    @property
    def cycles(self) -> int:
        return len(self.schedule)

    def free_cycles(self, port: str) -> list[int]:
        return [t for t, row in enumerate(self.schedule) if row.get(port) is None]


def windowed_scenario(
    model: SeqModel,
    *,
    reset_cycles: int,
    idle_cycles: int,
    active_cycles: int,
    tail_cycles: int,
    free_ports: list[str],
    enable_port: str | None,
    reset_port: str,
    goal_output: str,
    goal_value: int = 1,
    clock_port: str = "clk",
) -> Scenario:
    """The shape every design in this repo uses: reset, then an enabled window.

    Outside the active window the free ports are pinned to 0, so the answer
    is a statement about the window and nothing else.
    """
    total = reset_cycles + idle_cycles + active_cycles + tail_cycles
    schedule: list[dict[str, int | None]] = []
    for t in range(total):
        active = reset_cycles + idle_cycles <= t < reset_cycles + idle_cycles + active_cycles
        row: dict[str, int | None] = {clock_port: 1}
        row[reset_port] = 0 if t < reset_cycles else 1
        if enable_port:
            row[enable_port] = 1 if active else 0
        for port in model.inputs:
            if port in (clock_port, reset_port, enable_port):
                continue
            row[port] = None if (active and port in free_ports) else 0
        schedule.append(row)
    return Scenario(
        schedule=schedule,
        goal_output=goal_output,
        goal_cycle=total - 1,
        goal_value=goal_value,
    )


# --------------------------------------------------------------------------
# solving
# --------------------------------------------------------------------------


@dataclass
class Solution:
    inputs: list[dict[str, int]]
    seconds: float

    def bits(self, port: str, cycles: list[int]) -> list[int]:
        return [self.inputs[t][port] for t in cycles]


@dataclass
class SolveReport:
    solutions: list[Solution] = field(default_factory=list)
    exhausted: bool = False  # a follow-up solve returned UNSAT
    unsat: bool = False  # the very first solve returned UNSAT
    stats: dict[str, int] = field(default_factory=dict)
    solver: str = ""
    seconds_total: float = 0.0
    bound: int = 0


def enumerate_solutions(
    model: SeqModel,
    scenario: Scenario,
    *,
    free_ports: list[str],
    max_solutions: int = 1,
    solver_name: str = "cadical195",
    undriven_value: int | None = 0,
    initial: list[int | None] | None = None,
) -> SolveReport:
    """Solve, then optionally block and re-solve to test uniqueness."""
    unrolling = bmc.unroll(
        model,
        cycles=scenario.cycles,
        input_schedule=scenario.schedule,
        initial=initial,
        undriven_value=undriven_value,
    )
    goal_lit = unrolling.output_lits[scenario.goal_cycle][scenario.goal_output]
    assumption = goal_lit if scenario.goal_value else -goal_lit

    free_lits: list[int] = []
    for port in free_ports:
        for t in scenario.free_cycles(port):
            free_lits.append(unrolling.input_lits[t][port])

    report = SolveReport(stats=dict(unrolling.stats), solver=solver_name, bound=scenario.cycles)
    blocking: list[list[int]] = []
    for _ in range(max_solutions):
        outcome = bmc.solve_cnf(
            unrolling,
            assumptions=[assumption],
            extra_clauses=blocking,
            solver_name=solver_name,
        )
        report.seconds_total += outcome.seconds
        report.stats = dict(outcome.stats)
        if not outcome.sat:
            if not report.solutions:
                report.unsat = True
            report.exhausted = True
            break
        report.solutions.append(Solution(inputs=outcome.inputs or [], seconds=outcome.seconds))
        assigned = []
        for port in free_ports:
            for t in scenario.free_cycles(port):
                lit = unrolling.input_lits[t][port]
                assigned.append(-lit if outcome.inputs[t][port] else lit)
        if not assigned:
            report.exhausted = True
            break
        blocking.append(assigned)
    else:
        # Loop ran to completion without an UNSAT: try one more solve purely to
        # learn whether the space is exhausted, without recording a solution.
        outcome = bmc.solve_cnf(
            unrolling,
            assumptions=[assumption],
            extra_clauses=blocking,
            solver_name=solver_name,
        )
        report.seconds_total += outcome.seconds
        report.exhausted = not outcome.sat
    _ = free_lits
    return report


def concrete_trace(
    model: SeqModel, scenario: Scenario, solution: Solution, *, undriven_value: int = 0
):
    """Replay a solution through the fast cycle model (a pre-Icarus sanity check)."""
    seq = [
        {port: solution.inputs[t].get(port, 0) for port in model.inputs}
        for t in range(scenario.cycles)
    ]
    return simulate(model, seq, undriven_value=undriven_value)


# --------------------------------------------------------------------------
# verification by simulation — the step that makes the answer evidence
# --------------------------------------------------------------------------


@dataclass
class VerifyResult:
    ok: bool
    samples: list[dict[str, str]]
    sim: SimResult
    testbench: Path
    sources: list[Path]
    command_note: str


def verify_by_simulation(
    design: LoadedDesign,
    *,
    drive: dict[str, list[int]],
    watch: list[str],
    expect: list[SequenceExpectation],
    work_dir: Path,
    clock_period_ns: int = 10,
    timeout_s: float = 600.0,
) -> VerifyResult:
    """Replay a per-cycle stimulus through Icarus against the real netlist."""
    tb_text = build_sequence_testbench(
        top=design.netlist.top,
        clock_port=design.model.clock_net,
        drive=drive,
        watch=watch,
        expect=expect,
        clock_period_ns=clock_period_ns,
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    tb_path = work_dir / "sequence_tb.v"
    tb_path.write_text(tb_text, encoding="utf-8")
    sources = [tb_path, design.source, *design.pdk.model_files()]
    sim = compile_and_run(sources, top="tb", work_dir=work_dir, timeout_s=timeout_s)

    samples: list[dict[str, str]] = []
    for line in sim.run_stdout.splitlines():
        m = CYCLE_RE.match(line)
        if not m:
            continue
        row = {"cycle": m.group(1)}
        for token in m.group(2).split():
            key, _, value = token.partition("=")
            row[key] = value
        samples.append(row)
    ok = sim.compiled and sim.ran and "RESULT PASS" in sim.run_stdout
    return VerifyResult(
        ok=ok,
        samples=samples,
        sim=sim,
        testbench=tb_path,
        sources=sources,
        command_note=" ".join(str(s) for s in sources),
    )
