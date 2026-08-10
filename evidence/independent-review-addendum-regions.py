#!/usr/bin/env python3
"""Independent review addendum, claim 9: re-derive the Star Battle regions.

Independent of evidence/easter-egg-lead4.py at every layer it could be wrong:

  - netlist parsing: own regex parser of puzzle-extracted.v; pin directions
    parsed out of the sky130 behavioural Verilog itself (not tools/ JSON);
  - structure: own Tarjan SCC over an independently built flop->flop graph;
  - traces: gate-level Icarus simulation of the extracted netlist (the
    committed script used the Python cycle model in tools/sim/seqmodel.py);
  - membership: one-hot differential traces re-run at gate level for all 121
    positions, PLUS two-hot perturbations across every 4-adjacent pair of
    cells lying in different recovered regions (every boundary cell);
  - uniqueness: own naive CNF encoding (triples for at-most-2, (n-1)-subsets
    for at-least-2), Glucose 4.2 backend (not CaDiCaL), enumerated to UNSAT;
  - the 31,197,434 published-rules count: exact dynamic programming over
    row masks and column counts, no SAT involved.

Run from the repo root:

    .sim-work/review-venv/bin/python \
        evidence/independent-review-addendum-regions.py
"""

import re
import subprocess
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NETLIST = REPO / ".sim-work/independent-review/puzzle-extracted.v"
WORK = REPO / ".sim-work/indrev-addendum/regions"
PDK_VERILOG = Path.home() / ".volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
PRIMITIVES = PDK_VERILOG / "primitives.v"
BEHAVIOURAL = PDK_VERILOG / "sky130_fd_sc_hd.v"

ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
COMMITTED_MAP = [
    "HHHHHCCKFFA",
    "HHIHHCKKFFA",
    "HHICCCCKKFA",
    "HHICGGGAKKA",
    "IHICGAAAAAA",
    "IIICGGGAEEE",
    "CCCCCCGAEBB",
    "CDDDGGGAEBB",
    "CDDJAAAAEBB",
    "CCDJJAAAEEE",
    "CDDJAAAAAAA",
]

TOTAL_CYCLES = 130
ACTIVE_START = 4


# ------------------------------------------------------------- netlist parse
def parse_pdk_output_pins():
    """module name -> set of output port names, from the PDK Verilog."""
    text = BEHAVIOURAL.read_text()
    outputs = defaultdict(set)
    current = None
    for line in text.splitlines():
        m = re.match(r"\s*module\s+(sky130_fd_sc_hd__\w+)", line)
        if m:
            current = m.group(1)
            continue
        if current is None:
            continue
        m = re.match(r"\s*output\s+(\w+)\s*;", line)
        if m:
            outputs[current].add(m.group(1))
        if re.match(r"\s*endmodule", line):
            current = None
    return outputs


def parse_netlist():
    text = NETLIST.read_text()
    # strip the wire declarations / ports; find instances
    inst_re = re.compile(
        r"(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((.*?)\);", re.S)
    pin_re = re.compile(r"\.([A-Za-z0-9_]+)\s*\(\s*([^\s)]*)\s*\)")
    instances = []
    for m in inst_re.finditer(text):
        cell, name, body = m.group(1), m.group(2), m.group(3)
        pins = {p: n for p, n in pin_re.findall(body)}
        instances.append({"cell": cell, "name": name, "pins": pins})
    return instances


def build_graph(instances, out_pins):
    driver = {}  # net -> (instance index, pin)
    for i, inst in enumerate(instances):
        outs = out_pins.get(inst["cell"], set())
        for pin, net in inst["pins"].items():
            if pin in outs:
                if net in driver:
                    print(f"MULTIPLE DRIVERS on {net}")
                    sys.exit(1)
                driver[net] = (i, pin)
    flops = [i for i, inst in enumerate(instances)
             if re.match(r"sky130_fd_sc_hd__df", inst["cell"])]
    return driver, flops


def flop_graph(instances, driver, flops):
    """edges[src flop] -> dst flop when src.Q feeds dst.D combinationally."""
    flop_set = set(flops)
    edges = defaultdict(set)
    cone_cache = {}

    def source_flops(net):
        """flops whose Q reaches `net` through combinational cells only."""
        if net in cone_cache:
            return cone_cache[net]
        seen_nets = set()
        result = set()
        stack = [net]
        while stack:
            n = stack.pop()
            if n in seen_nets:
                continue
            seen_nets.add(n)
            d = driver.get(n)
            if d is None:
                continue  # primary input or undriven
            idx, _pin = d
            if idx in flop_set:
                result.add(idx)
                continue
            for pin, pn in instances[idx]["pins"].items():
                if pin not in out_pins.get(instances[idx]["cell"], set()):
                    stack.append(pn)
        cone_cache[net] = result
        return result

    for f in flops:
        d_net = instances[f]["pins"].get("D")
        if d_net is None:
            continue
        for src in source_flops(d_net):
            edges[src].add(f)
    return edges


def tarjan_sccs(nodes, edges):
    index = {}
    low = {}
    on_stack = set()
    stack = []
    sccs = []
    counter = [0]
    sys.setrecursionlimit(100000)

    def strongconnect(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in edges.get(v, ()):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in nodes:
        if v not in index:
            strongconnect(v)
    return sccs


# ------------------------------------------------------------- gate-level TB
def make_tb(q_nets):
    fmt = "%b" * len(q_nets)
    args = ", ".join(f"dut.{n}" for n in q_nets)
    return f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0, enable = 0, I = 0;
  wire success;
  wire o0, o1, o2, o3, o4, o5, o6, o7;
  reg word [0:120];
  integer t;
  puzzle dut (.I (I), .clk (clk), .enable (enable), .rst_n (rst_n),
    .success (success),
    .\\O[0] (o0), .\\O[1] (o1), .\\O[2] (o2), .\\O[3] (o3),
    .\\O[4] (o4), .\\O[5] (o5), .\\O[6] (o6), .\\O[7] (o7));
  always #5 clk = ~clk;
  initial begin
    $readmemb("word.mem", word);
    for (t = 0; t < {TOTAL_CYCLES}; t = t + 1) begin
      rst_n = (t >= 3);
      enable = (t >= {ACTIVE_START} && t < {ACTIVE_START + 121});
      I = (t >= {ACTIVE_START} && t < {ACTIVE_START + 121})
          ? word[t - {ACTIVE_START}] : 1'b0;
      #4;
      $display("S %0d {fmt}", t, {args});
      #6;
    end
    $finish;
  end
endmodule
"""


def compile_tb(q_nets):
    WORK.mkdir(parents=True, exist_ok=True)
    tb_path = WORK / "tb.v"
    tb_path.write_text(make_tb(q_nets))
    out = WORK / "sim.vvp"
    cmd = ["iverilog", "-g2005", "-o", str(out), "-D", "FUNCTIONAL",
           "-D", "UNIT_DELAY=#1", "-s", "tb",
           str(tb_path), str(NETLIST), str(PRIMITIVES), str(BEHAVIOURAL)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        sys.exit(f"iverilog failed:\n{proc.stderr}")
    return out


def run_word(vvp_path, word, label):
    d = WORK / "runs" / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "word.mem").write_text("\n".join(word) + "\n")
    proc = subprocess.run(["vvp", str(vvp_path)], capture_output=True,
                          text=True, timeout=120, cwd=d)
    if proc.returncode != 0:
        sys.exit(f"vvp failed for {label}:\n{proc.stderr}")
    states = []
    for line in proc.stdout.splitlines():
        if line.startswith("S "):
            states.append(line.split()[2])
    assert len(states) == TOTAL_CYCLES, (label, len(states))
    return states


def one_hot(pos):
    return "0" * pos + "1" + "0" * (120 - pos)


def two_hot(p, q):
    w = ["0"] * 121
    w[p] = w[q] = "1"
    return "".join(w)


def changed_groups(states, zero_states, pair_slices):
    changed = set()
    for g, sl in enumerate(pair_slices):
        for row, zrow in zip(states, zero_states):
            if any(row[i] != zrow[i] for i in sl):
                changed.add(g)
                break
    return changed


# ------------------------------------------------------------------ CNF part
def neighbours(pos):
    r, c = divmod(pos, 11)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < 11 and 0 <= nc < 11:
                yield nr * 11 + nc


def exactly2_clauses(varset):
    clauses = []
    for triple in combinations(varset, 3):
        clauses.append([-v for v in triple])
    for sub in combinations(varset, len(varset) - 1):
        clauses.append(list(sub))
    return clauses


def enumerate_star_battle(region_of, max_solutions=10):
    from pysat.solvers import Solver
    clauses = []
    for r in range(11):
        clauses += exactly2_clauses([r * 11 + c + 1 for c in range(11)])
    for c in range(11):
        clauses += exactly2_clauses([r * 11 + c + 1 for r in range(11)])
    regions = defaultdict(list)
    for pos, reg in enumerate(region_of):
        regions[reg].append(pos + 1)
    for reg in sorted(regions):
        clauses += exactly2_clauses(regions[reg])
    for a in range(121):
        for b in neighbours(a):
            if b > a:
                clauses.append([-(a + 1), -(b + 1)])
    sols = []
    with Solver(name="glucose42", bootstrap_with=clauses) as s:
        while len(sols) < max_solutions and s.solve():
            model = set(v for v in s.get_model() if v > 0)
            word = "".join("1" if p + 1 in model else "0" for p in range(121))
            sols.append(word)
            s.add_clause([-(p + 1) if b == "1" else (p + 1)
                          for p, b in enumerate(word)])
    return sols, len(clauses)


def dp_count_published_rules():
    """Grids with exactly 2 per row and column, no two marks touching
    (including diagonally). Exact count by DP over rows."""
    masks = []
    for c1 in range(11):
        for c2 in range(c1 + 2, 11):  # horizontal non-adjacency
            masks.append((1 << c1) | (1 << c2))
    spread = {m: m | (m << 1) | (m >> 1) for m in masks}
    spread[0] = 0  # state before the first row
    # state: column counts 0..2 encoded base 3, plus previous row mask
    states = {(0, 0): 1}  # (counts_base3, prev_mask) -> ways
    for _row in range(11):
        nxt = defaultdict(int)
        for (counts, prev), ways in states.items():
            for m in masks:
                if m & spread[prev]:
                    continue
                c = counts
                ok = True
                new = 0
                for col in range(11):
                    cnt = (c // 3 ** col) % 3
                    if m >> col & 1:
                        cnt += 1
                        if cnt > 2:
                            ok = False
                            break
                        new += 3 ** col
                if ok:
                    nxt[(counts + new, m)] += ways
        states = nxt
    full = sum(3 ** col * 2 for col in range(11))
    return sum(w for (counts, _), w in states.items() if counts == full)


# ------------------------------------------------------------------- driver
out_pins = None


def main():
    global out_pins
    out_pins = parse_pdk_output_pins()
    print(f"PDK modules with parsed output pins: {len(out_pins)}")
    instances = parse_netlist()
    print(f"netlist instances parsed: {len(instances)}")
    driver, flops = build_graph(instances, out_pins)
    logic = [i for i in range(len(instances))
             if any(p in out_pins.get(instances[i]['cell'], set())
                    for p in instances[i]['pins'])]
    undriven = set()
    for inst in instances:
        for pin, net in inst["pins"].items():
            if net.startswith("net_") and net not in driver:
                undriven.add(net)
    print(f"flops: {len(flops)}; cells with outputs: {len(logic)}; "
          f"undriven internal nets read by logic: {sorted(undriven)}")

    edges = flop_graph(instances, driver, flops)
    sccs = tarjan_sccs(flops, edges)
    pairs = sorted([sorted(instances[i]["name"] for i in comp)
                    for comp in sccs if len(comp) == 2])
    print(f"flop-graph SCCs: sizes "
          f"{sorted((len(c) for c in sccs), reverse=True)[:8]}... "
          f"two-flop SCCs: {len(pairs)}")

    name_to_idx = {instances[i]["name"]: i for i in flops}
    q_nets = []
    q_index = {}
    for i in flops:
        q_nets.append(instances[i]["pins"]["Q"])
        q_index[instances[i]["name"]] = len(q_nets) - 1
    pair_slices = [[q_index[n] for n in pair] for pair in pairs]

    vvp_path = compile_tb(q_nets)
    zero_states = run_word(vvp_path, "0" * 121, "zero")

    membership = []
    for pos in range(121):
        states = run_word(vvp_path, one_hot(pos), f"onehot-{pos:03d}")
        membership.append(changed_groups(states, zero_states, pair_slices))
    hist = defaultdict(int)
    for m in membership:
        hist[len(m)] += 1
    print(f"one-hot membership histogram: "
          f"{' '.join(f'{k}:{v}' for k, v in sorted(hist.items()))}")

    # classify groups by footprint
    group_cells = defaultdict(list)
    for pos, groups in enumerate(membership):
        for g in groups:
            group_cells[g].append(pos)
    columns, regions_g, other = [], [], []
    for g, cells in sorted(group_cells.items()):
        cols = {p % 11 for p in cells}
        rows = {p // 11 for p in cells}
        if len(cells) == 11 and len(cols) == 1:
            columns.append(g)
        elif len(cells) >= 100:
            other.append(g)
        else:
            regions_g.append(g)
    print(f"groups: columns={len(columns)} region-like={len(regions_g)} "
          f"large(row-reuse)={len(other)}")
    for g in other:
        cells = group_cells[g]
        missing = sorted(set(range(121)) - set(cells))
        print(f"  large group {g}: {len(cells)} cells; missing positions "
              f"{['r%dc%d' % divmod(p, 11) for p in missing]}")

    region_of = [None] * 121
    for gi, g in enumerate(sorted(regions_g)):
        for p in group_cells[g]:
            if region_of[p] is not None:
                print(f"REGION OVERLAP at {p}")
                sys.exit(1)
            region_of[p] = gi
    if any(r is None for r in region_of):
        print("UNCOVERED CELLS:", [p for p, r in enumerate(region_of) if r is None])
        sys.exit(1)
    print("recovered region map (independent labels a..k):")
    for r in range(11):
        print("  " + "".join(chr(ord("a") + region_of[r * 11 + c])
                             for c in range(11)))

    # partition equality with the committed map (label-invariant)
    committed_of = [COMMITTED_MAP[p // 11][p % 11] for p in range(121)]
    mapping, reverse = {}, {}
    same = True
    for mine, theirs in zip(region_of, committed_of):
        if mapping.setdefault(mine, theirs) != theirs:
            same = False
        if reverse.setdefault(theirs, mine) != mine:
            same = False
    print(f"partition identical to committed map: {same}")

    # two-hot cross-check on every 4-adjacent cross-region pair
    checked = mismatches = 0
    for p in range(121):
        r, c = divmod(p, 11)
        for q in ((r * 11 + c + 1) if c < 10 else None,
                  ((r + 1) * 11 + c) if r < 10 else None):
            if q is None or region_of[p] == region_of[q]:
                continue
            states = run_word(vvp_path, two_hot(p, q), f"twohot-{p:03d}-{q:03d}")
            got = changed_groups(states, zero_states, pair_slices)
            want = membership[p] | membership[q]
            checked += 1
            if got != want:
                mismatches += 1
                print(f"  two-hot mismatch p={p} q={q}: "
                      f"extra={sorted(got - want)} missing={sorted(want - got)}")
    print(f"two-hot boundary pairs checked: {checked}; mismatches: {mismatches}")
    boundary_cells = {p for p in range(121)
                      for q in neighbours(p) if region_of[p] != region_of[q]}
    print(f"boundary cells (8-neighbourhood): {len(boundary_cells)} of 121")

    # independent uniqueness
    sols, n_clauses = enumerate_star_battle(region_of)
    print(f"\nnaive CNF clauses: {n_clauses}; glucose42 enumeration found "
          f"{len(sols)} solution(s)")
    for i, w in enumerate(sols):
        print(f"  solution {i}: {w}")
    print(f"unique and equal to accepted word: {sols == [ACCEPTED]}")

    # exact count under published rules only
    count = dp_count_published_rules()
    print(f"\nDP count, published rules only (2/row, 2/col, no touching): "
          f"{count}")


if __name__ == "__main__":
    main()
