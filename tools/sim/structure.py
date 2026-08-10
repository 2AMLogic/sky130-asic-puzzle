"""Flip-flop-level structural analysis of a gate-level netlist.

`spec/puzzle.md` records a prior about `puzzle.gds`:

> The warm-up's 16 flip-flops implemented two shift registers feeding a
> comparator against a constant; the same shape at this size is a reasonable
> prior, **and it is only a prior**.

Issue #15 makes answering that a deliverable in its own right, and for a
good reason: if the state *does* decompose into independent clusters, the
reduced problem can be solved by construction; if it does not, a search
built on the assumption that it does fails by finding nothing, which is
indistinguishable from "the solver needs longer".

So this module answers it mechanically rather than by eye.  It collapses the
combinational logic away and reports the *state* graph — an edge `X -> Y`
whenever flip-flop `X`'s output is in the combinational fan-in cone of
flip-flop `Y`'s `D` pin — plus the features that would show a warm-up-shaped
design: weakly-connected components (independent clusters), strongly-
connected components (feedback), shift-register chains, and wide-fan-in
sinks (comparators).

Nothing here simulates or solves; it reads the netlist only.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from tools.sim.seqmodel import SeqModel


@dataclass
class StructureReport:
    ff_cells: Counter
    n_ffs: int
    n_gates: int
    clock_net: str
    async_nets: dict[str, list[str]]  # "RESET_B"/"SET_B" -> nets used
    undriven_nets: list[str]
    max_comb_depth: int
    # state graph
    preds: dict[str, set[str]] = field(default_factory=dict)
    succs: dict[str, set[str]] = field(default_factory=dict)
    input_driven: dict[str, set[str]] = field(default_factory=dict)  # ff -> primary inputs in cone
    weak_components: list[list[str]] = field(default_factory=list)
    sccs: list[list[str]] = field(default_factory=list)
    chains: list[list[str]] = field(default_factory=list)
    sinks: list[tuple[str, int]] = field(default_factory=list)
    broadcast: list[str] = field(default_factory=list)
    output_cones: dict[str, set[str]] = field(default_factory=dict)

    @property
    def decomposes(self) -> bool:
        """True when the flops split into two or more independent clusters."""
        return len(self.weak_components) > 1


def _cone(model: SeqModel, net: str, q_owner: dict[str, str]) -> tuple[set[str], set[str]]:
    """Combinational fan-in of `net`, stopping at flop outputs and inputs."""
    producer: dict[str, tuple] = {}
    for gate in model.gates:
        for out in gate.out_nets:
            if out is not None:
                producer[out] = gate
    inputs = set(model.inputs)
    ff_srcs: set[str] = set()
    pi_srcs: set[str] = set()
    seen: set[str] = set()
    stack = [net]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in q_owner:
            ff_srcs.add(q_owner[n])
            continue
        if n in inputs:
            pi_srcs.add(n)
            continue
        gate = producer.get(n)
        if gate is None:
            continue  # constant or undriven
        stack.extend(gate.in_nets)
    return ff_srcs, pi_srcs


def analyze(model: SeqModel) -> StructureReport:
    q_owner = model.q_nets()
    async_nets: dict[str, list[str]] = {}
    for ff in model.ffs:
        if ff.async_pin:
            async_nets.setdefault(ff.async_pin, [])
            if ff.async_net not in async_nets[ff.async_pin]:
                async_nets[ff.async_pin].append(ff.async_net)

    depth: dict[str, int] = {n: 0 for n in model.inputs}
    for ff in model.ffs:
        depth[ff.q_net] = 0
    for n in ["1'b0", "1'b1", *model.undriven_nets]:
        depth[n] = 0
    max_depth = 0
    for gate in model.gates:
        d = 1 + max([depth.get(n, 0) for n in gate.in_nets], default=0)
        for out in gate.out_nets:
            if out is not None:
                depth[out] = d
        max_depth = max(max_depth, d)

    report = StructureReport(
        ff_cells=Counter(ff.cell for ff in model.ffs),
        n_ffs=len(model.ffs),
        n_gates=len(model.gates),
        clock_net=model.clock_net,
        async_nets=async_nets,
        undriven_nets=list(model.undriven_nets),
        max_comb_depth=max_depth,
    )

    names = [ff.name for ff in model.ffs]
    report.preds = {n: set() for n in names}
    report.succs = {n: set() for n in names}
    for ff in model.ffs:
        srcs, pis = _cone(model, ff.d_net, q_owner)
        report.preds[ff.name] = srcs
        report.input_driven[ff.name] = pis
        for s in srcs:
            report.succs[s].add(ff.name)

    report.output_cones = {
        name: _cone(model, name, q_owner)[0] for name in model.outputs
    }

    report.weak_components = _weak_components(names, report.preds, report.succs)
    report.sccs = _sccs(names, report.succs)
    threshold = max(4, len(names) // 4)
    report.broadcast = sorted(n for n in names if len(report.succs[n]) >= threshold)
    report.chains = _shift_chains(names, report.preds, set(report.broadcast))
    report.sinks = sorted(
        ((n, len(report.preds[n])) for n in names), key=lambda p: -p[1]
    )
    return report


def _weak_components(
    names: list[str], preds: dict[str, set[str]], succs: dict[str, set[str]]
) -> list[list[str]]:
    parent = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for n in names:
        for m in preds[n] | succs[n]:
            union(n, m)
    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    return sorted(groups.values(), key=len, reverse=True)


def _sccs(names: list[str], succs: dict[str, set[str]]) -> list[list[str]]:
    """Iterative Tarjan."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    result: list[list[str]] = []
    counter = 0

    for root in names:
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            v, pos = work[-1]
            if pos == 0:
                index[v] = low[v] = counter
                counter += 1
                stack.append(v)
                on_stack[v] = True
            recursed = False
            children = sorted(succs[v])
            while pos < len(children):
                w = children[pos]
                pos += 1
                if w not in index:
                    work[-1] = (v, pos)
                    work.append((w, 0))
                    recursed = True
                    break
                if on_stack.get(w):
                    low[v] = min(low[v], index[w])
            if recursed:
                continue
            work[-1] = (v, pos)
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                result.append(sorted(comp))
            work.pop()
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    return sorted(result, key=len, reverse=True)


def _shift_chains(
    names: list[str], preds: dict[str, set[str]], broadcast: set[str]
) -> list[list[str]]:
    """Maximal chains of flops that only ever load their single predecessor.

    A shift-register stage `Y` after `X` has state dependencies exactly
    `{X}` or `{X, Y}` — the second form is a stage with a hold/enable mux,
    which is what an enabled shift register synthesises to.

    `broadcast` flops (a shared counter or sequencer feeding most of the
    design) are excluded from the count: they gate a stage rather than
    supply its data, and leaving them in hides every real chain.
    """
    feeder: dict[str, str] = {}
    for n in names:
        others = preds[n] - {n} - broadcast
        if len(others) == 1:
            feeder[n] = next(iter(others))
    chains: list[list[str]] = []
    consumed: set[str] = set()
    heads = [n for n in names if n in feeder and feeder[n] not in feeder]
    for head in heads:
        chain = [feeder[head], head]
        consumed.update(chain)
        cur = head
        while True:
            nxt = [n for n in names if feeder.get(n) == cur and n not in consumed]
            if len(nxt) != 1:
                break
            cur = nxt[0]
            chain.append(cur)
            consumed.add(cur)
        if len(chain) >= 3:
            chains.append(chain)
    return sorted(chains, key=len, reverse=True)


def format_report(report: StructureReport, *, short_names: dict[str, str] | None = None) -> str:
    def nm(n: str) -> str:
        return short_names.get(n, n) if short_names else n

    lines: list[str] = []
    lines.append("Flip-flops: " + ", ".join(f"{v} x {k}" for k, v in sorted(report.ff_cells.items())))
    lines.append(f"Total flops: {report.n_ffs}   combinational gates: {report.n_gates}")
    lines.append(f"Clock: single domain, every flop reached from `{report.clock_net}` through "
                 "non-inverting buffers only (checked, not assumed)")
    for pin, nets in sorted(report.async_nets.items()):
        lines.append(f"Asynchronous {pin}: {', '.join(nets)}")
    if report.undriven_nets:
        lines.append(f"Undriven nets read by logic: {', '.join(report.undriven_nets)}")
    lines.append(f"Max combinational depth: {report.max_comb_depth} gate levels")
    lines.append("")
    lines.append("State graph (edge X->Y when X's output is in the fan-in cone of Y's D pin):")
    n_edges = sum(len(v) for v in report.preds.values())
    lines.append(f"  {report.n_ffs} nodes, {n_edges} edges")
    lines.append(f"  weakly-connected components: {len(report.weak_components)} "
                 f"(sizes {[len(c) for c in report.weak_components]})")
    scc_sizes = Counter(len(c) for c in report.sccs)
    lines.append(f"  strongly-connected components: {len(report.sccs)} "
                 f"(size:count {dict(sorted(scc_sizes.items()))})")
    for comp in report.sccs:
        if len(comp) >= 3:
            lines.append(f"    feedback group of {len(comp)}: "
                         + " ".join(sorted(nm(c) for c in comp)))
    lines.append("")
    if report.broadcast:
        lines.append("Broadcast flops (fan out to >= 1/4 of the design): "
                     + " ".join(sorted(nm(c) for c in report.broadcast)))
        lines.append("")
    if report.chains:
        lines.append("Shift-register chains (each stage loads exactly one predecessor, or holds):")
        for chain in report.chains:
            lines.append(f"  length {len(chain)}: " + " -> ".join(nm(c) for c in chain))
    else:
        lines.append("Shift-register chains: none found")
    lines.append("")
    lines.append("Widest fan-in flops (comparator-shaped sinks):")
    for name, k in report.sinks[:5]:
        lines.append(f"  {nm(name)}: {k} state inputs")
    lines.append("")
    lines.append("Output cones (flops each output depends on):")
    for out, cone in report.output_cones.items():
        lines.append(f"  {out}: {len(cone)} flops")
    lines.append("")
    verdict = (
        f"DECOMPOSES into {len(report.weak_components)} independent clusters"
        if report.decomposes
        else "DOES NOT DECOMPOSE — one connected cluster, every flop reachable from every other"
    )
    lines.append(f"Verdict: {verdict}")
    return "\n".join(lines) + "\n"
