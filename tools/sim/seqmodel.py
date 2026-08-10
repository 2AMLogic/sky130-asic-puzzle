"""A cycle-level Boolean model of a gate-level netlist.

`tools/sim/icarus.py` simulates a netlist the honest way — event-driven, in
Icarus, against the PDK's behavioural models.  That is the oracle, and every
claim in `evidence/` is ultimately backed by it.  But an oracle you can only
*run forward* cannot answer "which inputs make `success` go high" over a
92-flop state space; for that the same circuit has to be turned into
something a solver can reason about.

This module is that turn.  It reduces a `tools.verilog_netlist.Netlist` to:

  - a list of flip-flops (`FlipFlop`), each with its D/Q/clock nets and its
    asynchronous set/reset, and
  - the combinational gates between them in topological order (`Gate`),
    each carrying the truth table measured from the PDK models by
    `tools/sim/celltable.py`.

Two consumers walk that same structure: `simulate()` here (concrete
evaluation, used to explore and to cross-check against Icarus) and
`tools/sim/bmc.py` (CNF unrolling).  Sharing the structure is deliberate —
if the solver and the fast simulator disagreed about what the circuit is,
neither result would mean anything.

The reduction is only valid under assumptions this module *checks* rather
than assumes: a single clock, reaching every flip-flop through
non-inverting buffers only, and no combinational cycles.  `build_model()`
raises `ModelError` naming the offending net if any of them fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.sim.celltable import CellTable
from tools.verilog_netlist import Netlist, base_cell, is_fill

# Output pins across the sky130_fd_sc_hd cells this repo's netlists use.  The
# set is checked against the measured cell tables in `build_model`, so a cell
# with an output pin missing from here fails loudly instead of being read as
# an input.
FF_CELLS = {"dfrtp_2", "dfstp_2", "dfxtp_2"}

# Non-inverting cells permitted on a clock path.
CLOCK_BUFFERS = ("clkbuf", "buf", "clkdlybuf", "dlygate", "dlymetal")

CONSTANT_NETS = {"1'b0": 0, "1'b1": 1}


class ModelError(RuntimeError):
    pass


@dataclass(frozen=True)
class FlipFlop:
    name: str
    cell: str
    d_net: str
    q_net: str
    clk_net: str
    async_pin: str | None
    async_net: str | None
    async_value: int  # value forced while the asynchronous pin is asserted (low)

    @property
    def initial_value(self) -> int | None:
        """Post-reset value, or None for a flop with no set/reset pin."""
        return self.async_value if self.async_pin else None


@dataclass(frozen=True)
class Gate:
    inst: str
    table: CellTable
    in_nets: tuple[str, ...]
    out_nets: tuple[str | None, ...]


@dataclass
class SeqModel:
    top: str
    inputs: list[str]
    outputs: list[str]
    ffs: list[FlipFlop]
    gates: list[Gate]  # topological order
    clock_net: str
    const_nets: dict[str, int] = field(default_factory=dict)
    undriven_nets: list[str] = field(default_factory=list)

    def ff_index(self) -> dict[str, int]:
        return {ff.name: i for i, ff in enumerate(self.ffs)}

    def q_nets(self) -> dict[str, str]:
        """Q net -> flip-flop name."""
        return {ff.q_net: ff.name for ff in self.ffs}


def build_model(nl: Netlist, tables: dict[str, CellTable], *, clock_port: str = "clk") -> SeqModel:
    inputs = [p.name for p in nl.ports if p.direction == "input"]
    outputs = [p.name for p in nl.ports if p.direction == "output"]
    if clock_port not in inputs:
        raise ModelError(f"{clock_port!r} is not an input port of {nl.top}")

    ffs: list[FlipFlop] = []
    raw_gates: list[Gate] = []
    driver: dict[str, tuple[str, str]] = {}  # net -> (instance, pin)
    const_nets: dict[str, int] = dict(CONSTANT_NETS)

    for inst in nl.instances:
        base = base_cell(inst.cell)
        if base in FF_CELLS:
            async_pin = None
            if "RESET_B" in inst.connections:
                async_pin, async_value = "RESET_B", 0
            elif "SET_B" in inst.connections:
                async_pin, async_value = "SET_B", 1
            else:
                async_value = 0
            ffs.append(
                FlipFlop(
                    name=inst.name,
                    cell=base,
                    d_net=inst.connections["D"],
                    q_net=inst.connections["Q"],
                    clk_net=inst.connections["CLK"],
                    async_pin=async_pin,
                    async_net=inst.connections[async_pin] if async_pin else None,
                    async_value=async_value,
                )
            )
            _claim(driver, inst.connections["Q"], inst.name, "Q")
            continue
        if is_fill(inst.cell):
            continue  # tap/decap/diode: no signal connectivity
        table = tables.get(inst.cell)
        if table is None:
            raise ModelError(f"no measured truth table for cell {inst.cell} (instance {inst.name})")
        in_nets = tuple(inst.connections[p] for p in table.inputs)
        missing = [p for p in table.inputs if p not in inst.connections]
        if missing:
            raise ModelError(f"{inst.name} ({inst.cell}): input pins {missing} are unconnected")
        out_nets: list[str | None] = []
        for pin in table.outputs:
            net = inst.connections.get(pin)
            out_nets.append(net)
            if net is not None:
                _claim(driver, net, inst.name, pin)
        raw_gates.append(Gate(inst.name, table, in_nets, tuple(out_nets)))

    for ff in ffs:
        _check_clock_path(ff, driver, clock_port, nl)

    port_inputs = set(inputs)
    q_nets = {ff.q_net for ff in ffs}
    known = port_inputs | q_nets | set(const_nets)

    undriven = sorted(
        {
            net
            for g in raw_gates
            for net in g.in_nets
            if net not in known and net not in driver
        }
    )

    ordered = _topological_order(raw_gates, known | set(undriven))
    return SeqModel(
        top=nl.top,
        inputs=inputs,
        outputs=outputs,
        ffs=ffs,
        gates=ordered,
        clock_net=clock_port,
        const_nets=const_nets,
        undriven_nets=undriven,
    )


def _claim(driver: dict[str, tuple[str, str]], net: str, inst: str, pin: str) -> None:
    if net in driver:
        prev = driver[net]
        raise ModelError(f"net {net} is driven by both {prev[0]}.{prev[1]} and {inst}.{pin}")
    driver[net] = (inst, pin)


def _check_clock_path(
    ff: FlipFlop, driver: dict[str, tuple[str, str]], clock_port: str, nl: Netlist
) -> None:
    """Walk CLK back to the clock port, allowing only non-inverting buffers."""
    by_name = {i.name: i for i in nl.instances}
    net = ff.clk_net
    seen: set[str] = set()
    while net != clock_port:
        if net in seen:
            raise ModelError(f"{ff.name}: cycle on the clock path at {net}")
        seen.add(net)
        src = driver.get(net)
        if src is None:
            raise ModelError(f"{ff.name}: clock net {net} has no driver")
        inst = by_name[src[0]]
        base = base_cell(inst.cell)
        if not base.startswith(CLOCK_BUFFERS):
            raise ModelError(
                f"{ff.name}: clock reaches it through {base} ({inst.name}), not a buffer — "
                "this model assumes one clock domain with no gating or inversion"
            )
        net = inst.connections["A"]


def _topological_order(gates: list[Gate], primary: set[str]) -> list[Gate]:
    producer: dict[str, int] = {}
    for idx, g in enumerate(gates):
        for net in g.out_nets:
            if net is not None:
                producer[net] = idx

    state = [0] * len(gates)  # 0 unvisited, 1 in progress, 2 done
    order: list[Gate] = []

    for root in range(len(gates)):
        if state[root]:
            continue
        stack: list[tuple[int, int]] = [(root, 0)]
        while stack:
            idx, pos = stack[-1]
            if state[idx] == 0:
                state[idx] = 1
            g = gates[idx]
            advanced = False
            while pos < len(g.in_nets):
                net = g.in_nets[pos]
                pos += 1
                if net in primary:
                    continue
                dep = producer.get(net)
                if dep is None or state[dep] == 2:
                    continue
                if state[dep] == 1:
                    raise ModelError(
                        f"combinational loop through net {net} "
                        f"({gates[dep].inst} -> {g.inst})"
                    )
                stack[-1] = (idx, pos)
                stack.append((dep, 0))
                advanced = True
                break
            if advanced:
                continue
            stack.pop()
            state[idx] = 2
            order.append(g)
    return order


# --------------------------------------------------------------------------
# concrete simulation
# --------------------------------------------------------------------------


@dataclass
class SimTrace:
    """Per-cycle record of a concrete run of `simulate`."""

    inputs: list[dict[str, int]]
    outputs: list[dict[str, int]]
    states: list[tuple[int, ...]]  # state *before* each cycle's clock edge


def initial_state(model: SeqModel, *, x_value: int = 0) -> tuple[int, ...]:
    """State after asynchronous reset.

    Flops with no set/reset pin have no defined power-up value in hardware;
    `x_value` picks the assumption made for them, and the caller is expected
    to say which assumption it made.
    """
    return tuple(ff.initial_value if ff.async_pin else x_value for ff in model.ffs)


def eval_comb(
    model: SeqModel, values: dict[str, int], *, undriven_value: int = 0
) -> dict[str, int]:
    """Evaluate every gate once, in topological order, extending `values`."""
    values.setdefault("1'b0", 0)
    values.setdefault("1'b1", 1)
    for net in model.undriven_nets:
        values.setdefault(net, undriven_value)
    for g in model.gates:
        pattern = 0
        for bit, net in enumerate(g.in_nets):
            if values[net]:
                pattern |= 1 << bit
        row = g.table.rows[pattern]
        for j, net in enumerate(g.out_nets):
            if net is not None:
                values[net] = int(row[j])
    return values


def step(
    model: SeqModel,
    state: tuple[int, ...],
    inputs: dict[str, int],
    *,
    undriven_value: int = 0,
) -> tuple[tuple[int, ...], dict[str, int]]:
    """One rising clock edge: returns `(next_state, outputs_before_the_edge)`."""
    values: dict[str, int] = {}
    for name in model.inputs:
        values[name] = inputs.get(name, 0)
    for ff, bit in zip(model.ffs, state, strict=True):
        values[ff.q_net] = bit
    eval_comb(model, values, undriven_value=undriven_value)

    next_state = []
    for ff in model.ffs:
        if ff.async_pin is not None and values[ff.async_net] == 0:
            next_state.append(ff.async_value)
        else:
            next_state.append(values[ff.d_net])
    outputs = {name: values[name] for name in model.outputs}
    return tuple(next_state), outputs


def simulate(
    model: SeqModel,
    input_seq: list[dict[str, int]],
    *,
    state: tuple[int, ...] | None = None,
    undriven_value: int = 0,
) -> SimTrace:
    """Run `len(input_seq)` clock cycles.

    `input_seq[t]` holds the input values applied *before* cycle `t`'s rising
    edge; `trace.states[t]` is the state at that moment and
    `trace.outputs[t]` what the outputs settle to with both, i.e. the values
    a testbench sampling just before that edge would see.

    `states` and `outputs` therefore have one more entry than `inputs`: the
    final entry is the state reached after the last edge, with the outputs it
    produces while the last input values are still applied.
    """
    cur = initial_state(model) if state is None else state
    trace = SimTrace(inputs=[], outputs=[], states=[])
    last: dict[str, int] = {}
    for values in input_seq:
        trace.states.append(cur)
        trace.inputs.append(dict(values))
        cur, outs = step(model, cur, values, undriven_value=undriven_value)
        trace.outputs.append(outs)
        last = values
    trace.states.append(cur)
    _, final_outs = step(model, cur, last, undriven_value=undriven_value)
    trace.outputs.append(final_outs)
    return trace
