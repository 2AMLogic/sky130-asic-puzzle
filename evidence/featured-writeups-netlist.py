"""Addendum (2026-11-14): the netlist-side claims made by Jane Street's 15
featured writeups, checked against `evidence/puzzle-extracted.v`.

One script per claim would be sixteen scripts; these are the claims that are
about *this* record's netlist, so they share one load of the design:

1. Flop census (Soto Franco, Smallwood): 84 dfrtp + 4 dfstp + 4 dfxtp.
2. Reset distribution (Wojcik claimed the 84 dfrtp are disconnected from
   `rst_n` in the layout; here every resettable flop reaches it).
3. The undriven net's forward cone (Ebert, Soto Franco: it reaches `O[1]`
   *and* `O[4]`; this record's README named `O[1]` alone).
4. The ditto byte under both static ties, plus the x-aware Icarus reading
   (Ebert: tie low -> TWO"NOT TOUCH, tie high -> TWO NOT TOUCJ then 0x02 0x10).
5. Jose Vargas's published "readable solution" board, which he reported as
   one of sixteen accepted inputs.
6. Gabriel Taboada's output-generator LFSR: 8 flops, 4-tap feedback plus the
   incoming `I` bit, characteristic polynomial x^8+x^4+x^3+x^2+1 (0x1D), and
   the keystream / stored-byte pair that decrypts to the answer — plus the
   8! bit-order x +/-7 cycle-offset search that pins the LSB-first
   chain-order readout as the only combination matching his published
   keystream.
7. The total-star counter's width (Aravapalli says 5 bits; Shapovalov and
   Ebert say 8).

Run from the repo root. No puzzle file is needed: the netlist is committed,
and the only external inputs are the sky130 cell models and Icarus.

    PDK_ROOT="$HOME/.volare" PYTHONPATH=. \
        python3 evidence/featured-writeups-netlist.py

`PDK_ROOT` is set here on purpose. `tools/sim/celltable.py` parses port
directions with a regex that matches `input A1;` but not `input wire A1;`,
and open_pdks switched to the latter, so on a host where `klt pdk find`
resolves the newer install the whole cycle model fails to build. Pinning the
older root (open_pdks c6d73a35, the one `evidence/puzzle-answer.md` used)
side-steps it. The parser gap is this repo's own, not `klt`'s, and is
tracked as #98; drop the override once that lands.
"""

import itertools
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.sim.seqmodel import simulate
from tools.sim.solve import (
    load_design,
    verify_by_simulation,
    windowed_scenario,
)

NETLIST = Path("evidence/puzzle-extracted.v")
WORK = Path(".sim-work/featured-writeups")

# The accepted word, from evidence/puzzle-solve.md §5 / puzzle-answer.md §3.
ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
# Jose Vargas's published grid (jlvargasme.github.io), his Figure 40.
VARGAS = "".join(
    """00000100010 10000001000 00000001010 10001000000 00100010000 00100010000
       00001000001 01000000100 00000000101 00010100000 01010000000""".split()
)
MESSAGE = "(* TWO STARS *)"
# Taboada's published printer constants.
TABOADA_KEYSTREAM = [0x65, 0x87, 0xDB, 0xD7, 0x44, 0x36, 0x3C, 0xE6,
                     0x2D, 0x22, 0x95, 0x3B, 0xB3, 0xDF, 0xA6]
TABOADA_STORED = [0x4D, 0xAD, 0xFB, 0x83, 0x13, 0x79, 0x1C, 0xB5,
                  0x79, 0x63, 0xC7, 0x68, 0x93, 0xF5, 0x8F]


def rule(title):
    print(f"\n== {title} " + "=" * max(0, 68 - len(title)))


def main():
    design = load_design(NETLIST, work_dir=WORK / "model",
                         table_cache=WORK / "tables.json")
    model = design.model
    print(f"netlist: {NETLIST}   PDK: {design.pdk.version}")
    print(f"cells: {len(model.gates)} combinational + {len(model.ffs)} flops")

    # ---------------------------------------------------------------- 1, 2
    rule("1/2. flop census and reset distribution")
    print("flop cells:", dict(Counter(ff.cell for ff in model.ffs)))
    print("async pin/post-reset value:",
          dict(Counter((ff.async_pin, ff.async_value) for ff in model.ffs)))
    async_nets = Counter(ff.async_net for ff in model.ffs)
    print("async nets:", dict(async_nets))
    resettable = [ff for ff in model.ffs if ff.async_pin]
    on_rst = [ff for ff in resettable if ff.async_net == "rst_n"]
    print(f"resettable flops: {len(resettable)}; of those on rst_n: {len(on_rst)}")
    print("Wojcik's 'all 84 dfrtp disconnected from rst_n':",
          "NOT reproduced" if len(on_rst) == len(resettable) else "reproduced")

    # ------------------------------------------------------------------- 3
    rule("3. the undriven net's forward cone")
    print("undriven nets:", model.undriven_nets)
    net = model.undriven_nets[0]
    loads = [(g.inst, g.in_nets.index(net)) for g in model.gates if net in g.in_nets]
    print(f"{net} loads:", loads)

    fanout = defaultdict(list)
    for g in model.gates:
        for n in g.in_nets:
            for o in g.out_nets:
                if o:
                    fanout[n].append(o)
    d_of = defaultdict(list)
    for ff in model.ffs:
        d_of[ff.d_net].append(ff.name)

    def cone(start):
        seen, stack, ffs = {start}, [start], set()
        while stack:
            n = stack.pop()
            ffs.update(d_of.get(n, ()))
            for nxt in fanout.get(n, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen, ffs

    nets, ffs = cone(net)
    q_of = {ff.name: ff.q_net for ff in model.ffs}
    seen_ff, frontier, allnets = set(ffs), list(ffs), set(nets)
    while frontier:
        n2, f2 = cone(q_of[frontier.pop()])
        allnets |= n2
        for x in f2:
            if x not in seen_ff:
                seen_ff.add(x)
                frontier.append(x)
    outs = sorted(o for o in model.outputs if o in allnets)
    print(f"combinational cone: {len(nets)} nets, {len(ffs)} flop D inputs")
    print(f"transitive closure: {len(seen_ff)} flops")
    print("top-level outputs reached:", outs)
    print("reaches success:", "success" in allnets)

    # ---------------------------------------------------------------- 4, 5
    rule("4/5. the ditto byte under both ties, and Vargas's board")
    sc = windowed_scenario(model, reset_cycles=3, idle_cycles=1,
                           active_cycles=121, tail_cycles=65, free_ports=["I"],
                           enable_port="enable", reset_port="rst_n",
                           goal_output="success")
    active = sc.free_cycles("I")
    window = list(range(125, sc.cycles))

    def drive_for(word):
        seq = [{p: (sc.schedule[t].get(p) or 0)
                for p in model.inputs if p != "clk"} for t in range(sc.cycles)]
        for t, b in zip(active, word):
            seq[t]["I"] = int(b)
        return seq

    def run(word, tie):
        tr = simulate(model, drive_for(word), undriven_value=tie)
        bs = [sum(tr.outputs[c][f"O[{i}]"] << i for i in range(8)) for c in window]
        succ = [c for c in range(len(tr.outputs))
                if tr.outputs[c].get("success") == 1]
        return bs, succ, tr

    def render(bs):
        return "".join(chr(b) if 32 <= b < 127 else "." for b in bs).rstrip(".")

    boards = [("accepted", ACCEPTED), ("Vargas", VARGAS),
              ("zeros", "0" * 121), ("ones", "1" * 121)]
    for name, word in boards:
        b0, s0, _ = run(word, 0)
        b1, _, _ = run(word, 1)
        diffs = [(window[i], f"{b0[i]:02x}", f"{b1[i]:02x}")
                 for i in range(len(b0)) if b0[i] != b1[i]]
        print(f"{name:9s} tie=0 {render(b0)!r}")
        print(f"{'':9s} tie=1 {render(b1)!r}")
        print(f"{'':9s} success@{(s0[:1] or [None])[0]}  byte diffs={diffs}")

    print("\nx-aware (Icarus) reading of Vargas's board:")
    drive = {p: [(sc.schedule[t].get(p) or 0) for t in range(sc.cycles)]
             for p in model.inputs if p != "clk"}
    for t, b in zip(active, VARGAS):
        drive["I"][t] = int(b)
    watch = [f"\\O[{i}]" for i in range(8)] + ["success"]
    v = verify_by_simulation(design, drive=drive, watch=watch, expect=[],
                             work_dir=WORK / "icarus")
    print("  icarus ok:", v.ok)
    for cyc in range(125, 143):
        bits = [str(v.samples[cyc].get(f"O[{i}]")) for i in range(8)]
        xs = [i for i, b in enumerate(bits) if b not in "01"]
        s = "".join(bits[::-1])
        if xs:
            print(f"  cycle {cyc}: O[7:0]={s}  x on bits {xs}")
        else:
            val = int(s, 2)
            ch = chr(val) if 32 <= val < 127 else "."
            print(f"  cycle {cyc}: O[7:0]={s}  {val:#04x} {ch}")

    # ------------------------------------------------------------------- 6
    rule("6. Taboada's output-generator LFSR")
    idx = model.ff_index()
    q_net_of = {ff.q_net: ff.name for ff in model.ffs}
    by_name = {ff.name: ff for ff in model.ffs}
    driver = {}
    for g in model.gates:
        for o in g.out_nets:
            if o:
                driver[o] = g
    primary = set(model.inputs) | set(model.const_nets) | set(model.undriven_nets)

    def support(n):
        if n in q_net_of:
            return {q_net_of[n]}
        if n in primary or n not in driver:
            return {n}
        s = set()
        for x in driver[n].in_nets:
            s |= support(x)
        return s

    # The register is the flop closure grown from the four dfstp cells (the
    # only flops in the design that reset high).
    seeds = [n for n in by_name if by_name[n].cell == "dfstp_2"]
    group, frontier = set(seeds), list(seeds)
    while frontier:
        for x in support(by_name[frontier.pop()].d_net):
            if x in by_name and x not in group:
                group.add(x)
                frontier.append(x)
    # Keep the flops that form a shift chain while a bit is being consumed.
    tr = simulate(model, drive_for(ACCEPTED), undriven_value=0)
    loadc = list(range(active[0], active[-1] + 1))

    def val(t, n):
        return tr.states[t][idx[n]]

    succ_of = {}
    for b in group:
        cands = [a for a in group
                 if all(val(t + 1, b) == val(t, a) for t in loadc)]
        if len(cands) == 1:
            succ_of[b] = cands[0]
    chain_set = set(succ_of) | set(succ_of.values())
    head = [n for n in chain_set if n not in succ_of]
    if len(head) != 1:
        print("could not identify a unique shift chain head:", head)
        return 1
    pred = {v: k for k, v in succ_of.items()}
    chain = [head[0]]
    while chain[-1] in pred:
        chain.append(pred[chain[-1]])
    print(f"shift chain: {len(chain)} flops, head (feedback + I) first")
    for i, n in enumerate(chain):
        print(f"  b{i} {n:34s} {by_name[n].cell:9s} reset={by_name[n].initial_value}")

    def state(t):
        return [val(t, n) for n in chain]

    reset_state = state(active[0])
    print("reset state b0..b7:", "".join(map(str, reset_state)),
          f"(weight {sum(reset_state)})")
    taps = None
    for r in range(1, 9):
        for comb in itertools.combinations(range(8), r):
            if all((sum(state(t)[i] for i in comb)
                    + drive_for(ACCEPTED)[t]["I"]) % 2 == state(t + 1)[0]
                   for t in loadc):
                taps = comb
                break
        if taps:
            break
    print("feedback taps:", taps,
          "-> b0(t+1) = I(t) XOR " + " XOR ".join(f"b{i}" for i in taps))
    # s(t+1) = XOR of s(t-i) for i in taps  =>  x^8 + sum x^(7-i) + ... ; print it
    powers = sorted({8} | {7 - i for i in taps})
    poly = " + ".join(f"x^{p}" if p > 1 else ("x" if p == 1 else "1")
                      for p in sorted(powers, reverse=True))
    mask = sum(1 << p for p in powers if p < 8)
    print(f"characteristic polynomial: {poly}  (= {mask:#04x})")
    print("post-load state b0..b7:", "".join(map(str, state(active[-1] + 1))))

    # keystream: the 8 chain bits read LSB-first at each message cycle
    msg_cycles = [126 + j for j in range(15)]
    keystream = [sum(state(c)[k] << k for k in range(8)) for c in msg_cycles]
    stored = [k ^ ord(ch) for k, ch in zip(keystream, MESSAGE)]
    print("keystream:", " ".join(f"{b:02x}" for b in keystream))
    print("  Taboada:", " ".join(f"{b:02x}" for b in TABOADA_KEYSTREAM),
          "-> match:", keystream == TABOADA_KEYSTREAM)
    print("stored   :", " ".join(f"{b:02x}" for b in stored))
    print("  Taboada:", " ".join(f"{b:02x}" for b in TABOADA_STORED),
          "-> match:", stored == TABOADA_STORED)
    decoded = "".join(chr(s ^ k) for s, k in zip(stored, keystream))
    print(f"stored XOR keystream = {decoded!r}  -> match: {decoded == MESSAGE}")

    # The LSB-first chain-order readout was not assumed: sweep every bit
    # order (bit k taken from chain index perm[k]) against every cycle offset
    # in ±7 around the nominal message cycles, and count the combinations
    # that reproduce Taboada's published keystream. The first byte acts as a
    # cheap filter: a wrong (perm, offset) pair passes it only 1/256 of the
    # time, so the sweep stays in seconds.
    lo, hi = -7, 7
    offsets = list(range(lo, hi + 1))
    bits_at = {off: [[state(c + off)[k] for k in range(8)]
                     for c in msg_cycles] for off in offsets}
    perms = list(itertools.permutations(range(8)))
    matches, candidates = [], 0
    for perm in perms:
        for off in offsets:
            candidates += 1
            if sum(bits_at[off][0][perm[k]] << k for k in range(8)) \
                    != TABOADA_KEYSTREAM[0]:
                continue
            ks = [sum(bits_at[off][j][perm[k]] << k for k in range(8))
                  for j in range(len(msg_cycles))]
            if ks == TABOADA_KEYSTREAM:
                matches.append((off, perm))
    print(f"readout search: offsets {lo}..{hi} ({len(offsets)}); "
          f"perms {len(perms)}; candidates {candidates}; matches: {len(matches)}")
    for off, perm in matches:
        tag = " identity" if perm == tuple(range(8)) else ""
        print(f"  offset {off} perm {perm}{tag}")

    # ------------------------------------------------------------------- 7
    rule("7. width of the total-star counter")
    sc2 = windowed_scenario(model, reset_cycles=3, idle_cycles=1,
                            active_cycles=121, tail_cycles=5, free_ports=["I"],
                            enable_port="enable", reset_port="rst_n",
                            goal_output="success")
    act2 = sc2.free_cycles("I")

    def end_state(word):
        seq = [{p: (sc2.schedule[t].get(p) or 0)
                for p in model.inputs if p != "clk"} for t in range(sc2.cycles)]
        for t, b in zip(act2, word):
            seq[t]["I"] = int(b)
        return simulate(model, seq, undriven_value=0).states[act2[-1] + 1]

    # k stars for k = 0..31, under two unrelated placement patterns, so a flop
    # that happens to track bit j under one of them drops out.
    def spread_for(step, offset):
        out = {}
        for k in range(32):
            w = ["0"] * 121
            for j in range(k):
                w[(offset + j * step) % 121] = "1"
            out[k] = end_state("".join(w))
        return out

    spreads = [spread_for(3, 0), spread_for(5, 2)]
    bits = []
    for j in range(8):
        hits = [ff.name for ff in model.ffs
                if all(sp[k][idx[ff.name]] == ((k >> j) & 1)
                       for sp in spreads for k in range(32))]
        # bit j is real only if some k in 0..31 actually sets it
        if any((k >> j) & 1 for k in range(32)):
            bits.append((j, hits))
    for j, hits in bits:
        print(f"  bit {j}: {hits}")
    print(f"=> the counter is {len(bits)} bits wide"
          f" (Aravapalli: 5; Shapovalov/Ebert: 8)")
    # confirm it wraps mod 32: 22 and 54 contiguous stars read the same
    cnt = [h[0] for _, h in bits if len(h) == 1]
    if len(cnt) == len(bits):
        for k in (22, 54):
            w = ["0"] * 121
            for j in range(min(k, 121)):
                w[j] = "1"
            s = end_state("".join(w))
            v2 = sum(s[idx[n]] << i for i, n in enumerate(cnt))
            print(f"  {k} contiguous stars -> counter reads {v2} ({k} mod 32 = {k % 32})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
