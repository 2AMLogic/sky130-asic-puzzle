"""Bounded model checking over a `SeqModel`, via CNF + a SAT solver.

`spec/puzzle.md` stage 7 names the approach: "92-bit state; bounded model
checking / SAT".  This is that encoding.

The circuit is unrolled `cycles` times.  Every net at every cycle becomes a
Boolean literal; every gate contributes the clauses of its *measured* truth
table (`tools/sim/celltable.py`), so the constraint system and the fast
simulator in `tools/sim/seqmodel.py` are reading the same cell semantics.
Flip-flops are the only thing that crosses a cycle boundary:

    s[t+1] = async_asserted(t) ? async_value : D(t)

Constants are folded as the unroll proceeds — with `rst_n` and `enable`
pinned by the scenario, whole cones collapse before a clause is ever
emitted, which is what keeps a 100+ cycle unroll of a 700-gate design
small enough to be solved in seconds rather than minutes.

The result is a plain CNF handed to `python-sat` (CaDiCaL by default).  A
solution is a per-cycle input assignment; it is *not* trusted here — the
caller is expected to replay it through Icarus against the real netlist
(`tools/sim/solve.py` does).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from tools.sim.seqmodel import SeqModel

# A literal is a non-zero int (DIMACS convention).  Variable 1 is reserved
# and forced true, so a "constant" literal is just ±TRUE_LIT.
TRUE_LIT = 1
FALSE_LIT = -1


class BmcError(RuntimeError):
    pass


@dataclass
class Cnf:
    n_vars: int = 1  # var 1 == TRUE
    clauses: list[list[int]] = field(default_factory=lambda: [[TRUE_LIT]])

    def new_var(self) -> int:
        self.n_vars += 1
        return self.n_vars

    def add(self, clause: list[int]) -> None:
        self.clauses.append(clause)


def _is_const(lit: int) -> bool:
    return lit in (TRUE_LIT, FALSE_LIT)


def _apply_table(cnf: Cnf, table, in_lits: list[int]) -> list[int | None]:
    """Emit clauses for one gate, returning a literal per output pin.

    Inputs that are already constant are substituted away first; if that
    makes an output constant, no variable and no clause is created for it.
    """
    free_idx = [i for i, lit in enumerate(in_lits) if not _is_const(lit)]
    fixed_mask = 0
    for i, lit in enumerate(in_lits):
        if lit == TRUE_LIT:
            fixed_mask |= 1 << i

    n_free = len(free_idx)
    n_out = len(table.outputs)
    # Residual table over the free inputs only.
    residual: list[str] = []
    for pat in range(1 << n_free):
        full = fixed_mask
        for b, i in enumerate(free_idx):
            if pat >> b & 1:
                full |= 1 << i
        residual.append(table.rows[full])

    out_lits: list[int | None] = []
    for j in range(n_out):
        col = [row[j] for row in residual]
        if all(c == "0" for c in col):
            out_lits.append(FALSE_LIT)
            continue
        if all(c == "1" for c in col):
            out_lits.append(TRUE_LIT)
            continue
        if n_free == 1:
            # Buffer or inverter of a single free input: no new variable.
            src = in_lits[free_idx[0]]
            out_lits.append(src if col[1] == "1" else -src)
            continue
        y = cnf.new_var()
        for pat, value in enumerate(col):
            antecedent = [
                -in_lits[free_idx[b]] if pat >> b & 1 else in_lits[free_idx[b]]
                for b in range(n_free)
            ]
            cnf.add(antecedent + [y if value == "1" else -y])
        out_lits.append(y)
    return out_lits


def _mux(cnf: Cnf, sel: int, if_true: int, if_false: int) -> int:
    if sel == TRUE_LIT:
        return if_true
    if sel == FALSE_LIT:
        return if_false
    if if_true == if_false:
        return if_true
    y = cnf.new_var()
    cnf.add([-sel, -if_true, y])
    cnf.add([-sel, if_true, -y])
    cnf.add([sel, -if_false, y])
    cnf.add([sel, if_false, -y])
    return y


@dataclass
class Unrolling:
    cnf: Cnf
    model: SeqModel
    # input_lits[t][port], state_lits[t][ff_index], out_lits[t][port]
    input_lits: list[dict[str, int]]
    state_lits: list[list[int]]
    output_lits: list[dict[str, int]]
    stats: dict[str, int]


def unroll(
    model: SeqModel,
    *,
    cycles: int,
    input_schedule: list[dict[str, int | None]],
    initial: list[int | None] | None = None,
    undriven_value: int | None = 0,
) -> Unrolling:
    """Unroll `model` for `cycles` clock edges.

    `input_schedule[t][port]` is `0`/`1` to pin that input at cycle `t`, or
    `None` to leave it free for the solver.  `initial[i]` does the same for
    flip-flop `i`'s power-up value (`None` = free, which is the honest model
    for a flop with no set/reset pin).
    """
    if len(input_schedule) != cycles:
        raise BmcError(f"input schedule has {len(input_schedule)} entries, expected {cycles}")
    cnf = Cnf()

    if initial is None:
        initial = [ff.initial_value for ff in model.ffs]
    state: list[int] = []
    for ff, want in zip(model.ffs, initial, strict=True):
        if want is None:
            state.append(cnf.new_var())
        else:
            state.append(TRUE_LIT if want else FALSE_LIT)

    undriven_lit: dict[str, int] = {}
    for net in model.undriven_nets:
        if undriven_value is None:
            undriven_lit[net] = cnf.new_var()
        else:
            undriven_lit[net] = TRUE_LIT if undriven_value else FALSE_LIT

    input_lits: list[dict[str, int]] = []
    state_lits: list[list[int]] = [list(state)]
    output_lits: list[dict[str, int]] = []

    for t in range(cycles):
        values: dict[str, int] = dict(undriven_lit)
        values["1'b0"] = FALSE_LIT
        values["1'b1"] = TRUE_LIT
        row: dict[str, int] = {}
        for port in model.inputs:
            want = input_schedule[t].get(port)
            if want is None:
                lit = cnf.new_var()
            else:
                lit = TRUE_LIT if want else FALSE_LIT
            row[port] = lit
            values[port] = lit
        input_lits.append(row)
        for ff, lit in zip(model.ffs, state, strict=True):
            values[ff.q_net] = lit

        for gate in model.gates:
            outs = _apply_table(cnf, gate.table, [values[n] for n in gate.in_nets])
            for net, lit in zip(gate.out_nets, outs, strict=True):
                if net is not None and lit is not None:
                    values[net] = lit

        output_lits.append({name: values[name] for name in model.outputs})

        nxt: list[int] = []
        for ff in model.ffs:
            d = values[ff.d_net]
            if ff.async_pin is None:
                nxt.append(d)
                continue
            arst = values[ff.async_net]
            forced = TRUE_LIT if ff.async_value else FALSE_LIT
            # asserted low: sel = arst -> normal D, else forced value
            nxt.append(_mux(cnf, arst, d, forced))
        state = nxt
        state_lits.append(list(state))

    return Unrolling(
        cnf=cnf,
        model=model,
        input_lits=input_lits,
        state_lits=state_lits,
        output_lits=output_lits,
        stats={"vars": cnf.n_vars, "clauses": len(cnf.clauses), "cycles": cycles},
    )


@dataclass
class SolveOutcome:
    sat: bool
    seconds: float
    solver: str
    stats: dict[str, int]
    inputs: list[dict[str, int]] | None = None
    model_bits: dict[int, bool] | None = None


def solve_cnf(
    unrolling: Unrolling,
    *,
    assumptions: list[int] | None = None,
    extra_clauses: list[list[int]] | None = None,
    solver_name: str = "cadical195",
) -> SolveOutcome:
    from pysat.solvers import Solver  # imported lazily: optional dependency

    clauses = list(unrolling.cnf.clauses)
    if extra_clauses:
        clauses.extend(extra_clauses)
    started = time.monotonic()
    with Solver(name=solver_name, bootstrap_with=clauses) as sat:
        ok = sat.solve(assumptions=assumptions or [])
        elapsed = time.monotonic() - started
        stats = {**unrolling.stats, "clauses_total": len(clauses)}
        if not ok:
            return SolveOutcome(sat=False, seconds=elapsed, solver=solver_name, stats=stats)
        assignment = sat.get_model()

    bits = {abs(v): v > 0 for v in assignment}

    def value(lit: int) -> int:
        if lit == TRUE_LIT:
            return 1
        if lit == FALSE_LIT:
            return 0
        return int(bits[abs(lit)] if lit > 0 else not bits[abs(lit)])

    inputs = [{port: value(lit) for port, lit in row.items()} for row in unrolling.input_lits]
    return SolveOutcome(
        sat=True,
        seconds=elapsed,
        solver=solver_name,
        stats=stats,
        inputs=inputs,
        model_bits=bits,
    )
