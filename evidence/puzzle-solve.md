# Puzzle solve: driving `success` (stage 7)

**Status: solved, verified by simulation, and proved unique.**
A 121-bit input sequence on `I` drives `success` high. It was found by
bounded model checking over the full 92-flop state (no state reduction, no
guessed structure), replayed through Icarus against
`evidence/puzzle-extracted.v` itself — not merely reported by the solver —
and a second SAT call with that answer blocked returns `UNSAT`, so it is
the *only* input sequence that works at the bound.

Everything below was executed on 2026-08-10 on the machine this repo is
checked out on, and every command is reproducible from a clean checkout
after `./scripts/fetch-puzzle.sh` plus one `pip install` (see
"Reproducing" at the end).

---

## 1. The structural question, answered first — and the prior discarded

`spec/puzzle.md` carries a prior into this stage:

> The warm-up's 16 flip-flops implemented two shift registers feeding a
> comparator against a constant; the same shape at this size is a reasonable
> prior, **and it is only a prior**.

Issue #15 makes settling that a deliverable, because getting it wrong is
silent: a search built on a false decomposition finds nothing, which looks
exactly like a search that needs more time. So it was answered mechanically
before any solver was installed, by `tools/sim/structure.py`, which collapses
the combinational logic away and reports the **state graph** — an edge
`X -> Y` whenever flop `X`'s output lies in the combinational fan-in cone of
flop `Y`'s `D` pin.

The same analysis run on both designs is the cleanest way to state the
answer. The warm-up:

```
Total flops: 16   combinational gates: 63
  weakly-connected components: 2 (sizes [8, 8])
  strongly-connected components: 16 (size:count {1: 16})
Shift-register chains (each stage loads exactly one predecessor, or holds):
  length 8: F00 -> F01 -> F02 -> F03 -> F04 -> F05 -> F06 -> F07
  length 8: F08 -> F09 -> F10 -> F11 -> F12 -> F13 -> F14 -> F15
Output cones (flops each output depends on):
  S: 16 flops
Verdict: DECOMPOSES into 2 independent clusters
```

That is literally the shape `spec/puzzle.md` describes: two independent
8-stage shift registers, no feedback anywhere, and one purely combinational
comparator reading all 16 bits. The puzzle:

```
Total flops: 92   combinational gates: 636
  92 nodes, 801 edges
  weakly-connected components: 1 (sizes [92])
  strongly-connected components: 51 (size:count {1: 25, 2: 23, 4: 1, 8: 1, 9: 1})
    feedback group of 9: F16 F21 F24 F26 F39 F42 F46 F51 F64
    feedback group of 8: F54 F55 F57 F59 F60 F61 F62 F63
    feedback group of 4: F76 F78 F79 F80
Broadcast flops (fan out to >= 1/4 of the design): F16 F21 F24 F26 F39 F42 F46 F51 F64
Shift-register chains:
  length 12: F52 -> F50 -> F53 -> F47 -> F40 -> F36 -> F43 -> F32 -> F34 -> F38 -> F44 -> F49
Widest fan-in flops (comparator-shaped sinks):
  F84: 57 state inputs
  F88: 57 state inputs
Verdict: DOES NOT DECOMPOSE — one connected cluster, every flop reachable from every other
```

**The prior is discarded, but not because nothing rhymes with it.** The
puzzle does contain a shift register (12 stages, `I` at its head) and it does
contain comparator-shaped sinks (`F88` is the `success` flop itself, reading
57 of the 92 flops; `F84` is its twin). What it does *not* have is the
property that made the warm-up easy: **independence.** All 92 flops sit in
one weakly-connected component; there is no sub-problem that can be solved on
its own and composed. Three feedback groups (a 9-flop group that fans out to
most of the design, an 8-flop group, and the 4 unresettable flops) make it
genuinely sequential rather than a load-then-compare datapath, and the two
57-input sinks couple everything into a single accept condition. There is no
"`A + B == 496`" to invert by construction.

So the answer to the structural question is **no, it does not decompose the
way the warm-up did**, and the consequence is that stage 7 needs the tool
`spec/puzzle.md` names for it: bounded model checking / SAT over the whole
state. That is what was done.

Facts the same report establishes, all checked rather than assumed (the
model refuses to build otherwise):

| Property | Value |
|---|---|
| Flops | 84 `dfrtp_2`, 4 `dfstp_2`, 4 `dfxtp_2` (92) |
| Clock | one domain; every `CLK` reaches `clk` through non-inverting buffers only |
| Async reset | `RESET_B` = `rst_n` (84 flops), `SET_B` = `rst_n` (4 flops) |
| Combinational gates | 636 (after tap/decap/diode fill is dropped) |
| Max combinational depth | 14 gate levels |
| Combinational loops | none (the model is a DAG; a loop is a hard error) |
| Undriven net read by logic | `net_00575` (see §6) |

Reproduce:

```sh
python3 -m tools.sim.run_solve --netlist evidence/puzzle-extracted.v --structure \
    --active-cycles 121 --max-solutions 2 --verify --grid-width 11
python3 -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from tools.sim.solve import load_design
from tools.sim.structure import analyze, format_report
d = load_design(Path('puzzle/warmup/01_netlist.v'), work_dir=Path('.sim-work/warmup'))
print(format_report(analyze(d.model)))
"
```

## 2. Turning the netlist into something a solver can reason about

Two new layers sit between `evidence/puzzle-extracted.v` and the SAT solver.
Neither invents any semantics:

**`tools/sim/celltable.py` — cell functions are measured, not remembered.**
Writing "`a21bo` is `(A1 & A2) | ~B1_N`, probably" from memory is exactly the
kind of unbacked claim CLAUDE.md §5 rules out: one transcription slip changes
the circuit the solver reasons about and the mistake is invisible until the
answer is wrong. So the truth table of every cell is *measured* — a generated
Verilog testbench instantiates each of the 63 combinational cell types the
netlist uses, sweeps every input combination, and reads the outputs back out
of the same `sky130_fd_sc_hd` behavioural models `tools/sim` already
simulates against. Port directions come from the model file's own
declarations. Sequential cells are excluded and modelled explicitly.

**`tools/sim/seqmodel.py` — a cycle-level Boolean model.** Flops (D/Q/clock,
async set/reset) plus the combinational gates between them in topological
order. The reduction is only valid under assumptions it *checks*: single
clock through non-inverting buffers, no multiply-driven nets, no
combinational loops. Two consumers walk that one structure — the concrete
simulator here, and the CNF unroller in `tools/sim/bmc.py`. Sharing it is
deliberate: if the solver and the simulator disagreed about what the circuit
is, neither result would mean anything.

## 3. Model fidelity, checked three independent ways

A solver answer is only as good as the model it was derived from, so the
model was validated before it was trusted.

**(a) Against the recorded trace, on the real subject.** The cycle model is
driven with `example_inputs.vcd`'s recorded inputs and its `O[7:0]`/`success`
outputs compared against the recording:

```sh
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from pathlib import Path
from tools.sim.solve import load_design
from tools.sim.seqmodel import simulate
from tools.vcd import read_vcd

design = load_design(Path("evidence/puzzle-extracted.v"), work_dir=Path(".sim-work/solve"))
doc = read_vcd("puzzle/example_inputs.vcd")
hist = {v.name: doc.signal_history(v.name) for v in doc.vars}

def at(name, t):
    cur = None
    for tt, vv in hist[name]:
        if tt > t:
            break
        cur = vv
    return cur

edges = [t for t, v in hist["clk"] if v == "1"]
seq = [{"clk": 1, "rst_n": int(at("rst_n", t - 1) == "1"),
        "enable": int(at("enable", t - 1) == "1"), "I": int(at("I", t - 1) == "1")}
       for t in edges]
trace = simulate(design.model, seq)
checked = mismatches = 0
for k, t in enumerate(edges):
    rec_o, rec_s = at("O", t - 1), at("success", t - 1)
    if rec_o is None or "x" in rec_o:
        continue
    got_o = "".join(str(trace.outputs[k][f"O[{b}]"]) for b in range(7, -1, -1))
    checked += 1
    mismatches += (rec_o != got_o) or (rec_s != str(trace.outputs[k]["success"]))
print(f"{len(edges)} recorded clock edges; {checked} sampled; {mismatches} mismatches on O/success")
PY
```

```
312 recorded clock edges; 311 sampled; 0 mismatches on O/success
```

(The one unsampled edge is the first, where the recording is still `x`.) This
is a stronger statement than stage 6's replay: stage 6 compared *Icarus* to
the recording, this compares the *Boolean model the solver actually uses* to
the recording, over the same 3.12 µs trace, at every clock edge.

**(b) Against Icarus, on a netlist with published ground truth.**
`tools/sim/selftest_solve.py` runs the whole solver stack against the
warm-up, where `warmup/00_source.v` supplies an oracle no solver was involved
in producing. Five checks, run in one command:

```sh
python3 -m tools.sim.selftest_solve
```

```
== 1. cycle model vs Icarus, random stimulus ==
  trial 0: ok — 40 cycles agree
  trial 1: ok — 40 cycles agree
  trial 2: ok — 40 cycles agree

== 2. enumerate every solution of S=1 after an 8-bit load ==
  bound 12 cycles, 324 vars, 1740 clauses, 0.02s total
  15 solutions: [(241, 255), (242, 254), (243, 253), (244, 252), (245, 251), (246, 250), (247, 249), (248, 248), (249, 247), (250, 246), (251, 245), (252, 244), (253, 243), (254, 242), (255, 241)]
  ok — exactly the 15 pairs with A + B == 496, and no more

== 3. Icarus confirms a solved sequence asserts S ==
  A=242 B=254 (sum 496)
  ok — RESULT PASS from Icarus

== 4. negative control: one flipped bit must not assert S ==
  ok — model and Icarus both report S=0 for the corrupted sequence

== 5. UNSAT control: S cannot be high before the load completes ==
  ok — UNSAT at bound 7 (0.00s)

RESULT PASS
```

Check 2 is the important one for this stage: the *same* block-and-re-solve
loop the puzzle's uniqueness claim rests on is checked here against a count
computed independently in Python (the 15 pairs summing to 496), so the
machinery is known to be both complete and terminating before it is pointed
at the puzzle. Checks 4 and 5 exist because a checker that cannot fail is not
a checker.

**(c) Against Icarus, on the puzzle itself.** §7 below.

## 4. The encoding, the solver, the bound, the time

| | |
|---|---|
| **Encoding** | Bit-level CNF. Every net at every cycle is a literal; each gate contributes the clauses of its measured truth table (`2^k` clauses of length `k+1` for `k` non-constant inputs). Flops are the only thing crossing a cycle boundary: `s[t+1] = async_asserted(t) ? async_value : D(t)`. Constants are folded during the unroll, and single-input residual gates (buffers/inverters after folding) reuse the source literal instead of allocating a variable. |
| **Free variables** | `I` at each of the 121 active cycles, plus the power-up values of the 4 unresettable `dfxtp_2` flops (left free — they have no defined power-up value in hardware, so pinning them would be an assumption). |
| **Fixed** | `rst_n` low for 3 cycles then high; `enable` high for the 121-cycle window and low outside it; `I` pinned to 0 outside the window. |
| **Goal** | `success == 1` at the final cycle of the bound. |
| **Bound** | 130 clock cycles (3 reset + 1 idle + 121 active + 5 tail). |
| **CNF size** | 19,985 variables, 108,610 clauses. |
| **Solver** | CaDiCaL 1.9.5 via `python-sat` 1.9.dev12 (`pysat.solvers.Solver(name="cadical195")`). |
| **Time** | 0.49 s for the first SAT call; 0.98 s for SAT + the follow-up UNSAT (uniqueness) call. Whole pipeline — cell characterisation, model build, structural analysis, solve, uniqueness proof, Icarus verification — **1.7 s wall clock**. |

The bound is not a guess. It is the number of enabled cycles in
`example_inputs.vcd` (121 = 11 × 11), and the design's own 9-flop
broadcast counter reaches its terminal state after exactly that many
enabled cycles. It was also checked from both sides by sweeping it:

```sh
for n in 118 119 120 121 122 123 124; do
  echo -n "active=$n: "
  python3 -m tools.sim.run_solve --netlist evidence/puzzle-extracted.v \
      --active-cycles $n --max-solutions 1 | grep -E "^RESULT UNSAT|^Solutions found"
done
```

```
active=118: RESULT UNSAT at bound 127 — no input sequence in this window drives success to 1
active=119: RESULT UNSAT at bound 128 — no input sequence in this window drives success to 1
active=120: RESULT UNSAT at bound 129 — no input sequence in this window drives success to 1
active=121: Solutions found: 1
active=122: Solutions found: 1
active=123: Solutions found: 1
active=124: Solutions found: 1
```

Windows shorter than 121 are provably impossible; windows longer than 121
succeed with **the same first 121 bits** and arbitrary trailing bits — the
design stops accepting input once the counter terminates. (Checked directly:
at `--active-cycles 124 --max-solutions 3` the three answers share an
identical 121-bit prefix and differ only in the last three, unused, bits.)
So 121 is the true word length, not an artefact of the scenario.

## 5. The answer

The unique 121-bit sequence applied to `I`, one bit per enabled clock cycle,
first bit first:

```
0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000
```

121 = 11 × 11, and read row-major into an 11 × 11 grid the word is visibly
structured:

```
.......#.#.
#....#.....
.......#.#.
#.#........
....#.#....
..#.....#..
....#.....#
.#....#....
...#......#
.....#..#..
.#.#.......
```

Measured properties of that word (a description of the answer, not a
verified claim about the circuit's intent): popcount 22; exactly 2 marks in
every row and exactly 2 in every column; minimum Chebyshev distance between
any two marks is 2, i.e. no two marks touch, even diagonally.

Three things in the structural report line up with that reading, each of
them measured:

- **22 two-flop feedback groups**, 11 of them fed only by the low half of
  the broadcast counter and 11 by all of it — the shape of one saturating
  counter per row and per column.
- **An 8-flop group whose value is the running count of 1s on `I`.** Driving
  the model with `example_inputs.vcd`'s recorded input and reading that group
  at the end of the window gives 38, which is exactly the number of 1s the
  recording puts on `I` during `enable`.
- **The 12-stage shift register's taps.** One flop (`F48`) reads stages 1,
  10, 11 and 12 of that chain and nothing else from it — offsets `1` and
  `11 ± 1`, i.e. precisely the neighbours of the current cell in an 11-wide
  raster.

Even so, the only thing asserted here as *established* is the sequence itself
and the `success` it produces; the paragraph above is corroboration, not a
simulated proof of what the accept condition means.

## 6. Uniqueness, and what the answer does not depend on

**Unique.** With the 121 free `I` literals of the found answer blocked, the
same instance is `UNSAT`. There is exactly one input sequence at this bound
that drives `success`.

That uniqueness result holds under the weakest assumptions available:

- **Power-up state of the 4 unresettable flops** (`dfxtp_2`) was left as free
  variables throughout, so no answer was ruled out by assuming one.
  Separately, replaying the found answer through the cycle model under **all
  16** power-up combinations asserts `success` in all 16.
- **`net_00575`** is read by two gates and driven by nothing in the extracted
  netlist. Re-solving with that net *also* left free still yields the same
  unique answer, and replaying the answer with it tied to 0 and to 1 asserts
  `success` either way. Icarus, where the net is genuinely undriven (`z`),
  also asserts `success` — so the answer does not depend on how that net is
  resolved. (The net itself is an extraction observation worth a separate
  look; it is not load-bearing here and no claim is made about it.)
- **Solver independence.** The same CNF, solved by three back ends, gives the
  same word and the same uniqueness verdict:

```
cadical195   solutions=1 unique=True time=1.01s
glucose42    solutions=1 unique=True time=1.61s
minisat22    solutions=1 unique=True time=1.73s
```

## 7. Verification by simulation — the step that makes this evidence

A SAT model is a claim about an *encoding*. Only a simulation is a claim
about the *netlist*. So the answer is replayed, bit by bit, through Icarus
against `evidence/puzzle-extracted.v` and the real `sky130_fd_sc_hd`
behavioural models, with the testbench sampling `success` once per cycle:

```sh
python3 -m tools.sim.run_solve --netlist evidence/puzzle-extracted.v \
    --structure --verify --max-solutions 2 --grid-width 11
```

```
PDK variant: sky130A
PDK version: open_pdks c6d73a35f524070e85faff4a6a9eef49553ebc2b
Resolved via: klt pdk find --pdk sky130A (root: /home/ubuntu/.volare)
Model files:
  /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

Netlist: evidence/puzzle-extracted.v (top `puzzle`)
Cell truth tables: 63 cell types, measured from the models above
...
== bounded model checking ==
Bound: 130 clock cycles (3 reset, 1 idle, 121 active, 5 tail)
Free inputs: I during the active window (121 cycles each), pinned to 0 outside it
Goal: success == 1 at cycle 129
CNF: 19985 variables, 108610 clauses
Solver: cadical195   total solve time: 0.98s
Solutions found: 1
  solution 0: I[4..124] = 0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000
UNIQUE — a further solve with the 1 solution(s) above blocked returned UNSAT, so no other input sequence works at this bound

== verification by simulation (Icarus, against the real netlist) ==
Testbench: .sim-work/solve/sequence_tb.v
Sources:   .sim-work/solve/sequence_tb.v evidence/puzzle-extracted.v /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
RESULT PASS
VERIFIED — the solved sequence drives success to 1 in a gate-level simulation of the netlist
```

`success` reads 0 at every one of cycles 0–125 and 1 at cycles 126–129, in
the simulation, on the extracted netlist. That is acceptance criterion 1.

**Negative controls, so the verification is known to be capable of failing.**
Every one of the 121 single-bit flips of the answer was replayed through the
cycle model, and three of them (first, middle, last bit) through Icarus:

```
== negative control: every single-bit flip of the 121-bit word (cycle model) ==
  121 flips tried, 0 still asserted success (expected 0)

== negative control in Icarus (3 flips, against the real netlist) ==
  flip bit 0: Icarus says success=0 at the final cycle -> True
  flip bit 60: Icarus says success=0 at the final cycle -> True
  flip bit 120: Icarus says success=0 at the final cycle -> True
```

The full robustness/negative-control script that produced §6's and this
section's numbers is reproduced in `tools/README.md` § "Solving for an
output".

## 8. Reproducing this

Prerequisites already documented elsewhere: a resolvable sky130A PDK
(`tools/sim/pdk.py`, `tools/README.md`) and Icarus Verilog. One new
dependency, installed for this stage and recorded here because a result
nobody can re-run is not evidence:

```sh
pip install python-sat          # 1.9.dev12 here; provides CaDiCaL/Glucose/MiniSat
```

`z3-solver` (5.0.0) was also installed while scoping the work, but is not
used: the problem reduces to plain propositional CNF, so an SMT layer buys
nothing over a SAT solver and `tools/sim/bmc.py` has no dependency on it.
`tools/sim/bmc.py` imports `pysat` lazily, so nothing else in `tools/`
acquires a hard dependency on a solver, and CI (which installs neither a PDK
nor a simulator nor a solver) is unaffected.

```sh
./scripts/fetch-puzzle.sh
python3 -m tools.sim.selftest_solve          # known-answer test, warm-up only
python3 -m tools.sim.run_solve --netlist evidence/puzzle-extracted.v \
    --structure --verify --max-solutions 2 --grid-width 11
```

## 9. What this does *not* claim, and the handoff to stage 8

- **Not a claim that the design "is" an 11 × 11 placement puzzle.** §5's grid
  reading is a description of the unique answer plus a structural
  correspondence, not a simulated proof of the accept condition's intent.
  Nothing downstream depends on it.
- **Not a claim about `O[7:0]`.** After the input window closes, `O` emits one
  byte per cycle; in the recorded `example_inputs.vcd` (which does *not*
  assert `success`) those bytes are nine printable ASCII characters.
  Simulating the output generator under the solved input and reading the
  message it produces is stage 8 (`spec/puzzle.md`), tracked separately —
  this stage stops at `success`.
- **Not a claim of correctness against Jane Street's own answer.** There is no
  independent oracle short of submission. What is established is that this
  sequence drives `success` in the recovered netlist, that it is the only one
  that does, and that the recovered netlist reproduces the one recorded trace
  the puzzle ships (§3a, and `evidence/puzzle-replay.md`).
- **Embargo.** Everything on this page is puzzle-derived and stays in this
  repository until 2026-09-04 (CLAUDE.md §1). The tooling added for it
  (`tools/sim/celltable.py`, `seqmodel.py`, `bmc.py`, `structure.py`,
  `solve.py`) is subject-independent and its warm-up self-test is not
  embargoed; the answer above is.

## 10. Stage 8, landed — see `evidence/puzzle-answer.md`

This section is an append made for issue #16 (stage 8), on top of the
recorded result above — nothing above has been edited, per this repo's
append-only evidence convention.

Stage 8 is done: `tools/sim/run_answer.py` re-derives the 121-bit sequence
above via the same `solve.py` machinery (rather than retyping it from §5),
extends the simulated window past the goal cycle, and decodes `O[7:0]`.
The "nine printable ASCII characters" note two bullets up (§9) is now
resolved rather than open: it was an artifact of an insufficient
observation window, not the message's true length — the full message is
15 bytes. The bit order this section flagged as "not yet established" is
now checked (both candidates computed, the printable one selected and
reported alongside the non-printable alternative) rather than assumed. See
`evidence/puzzle-answer.md` for the full command, output, self-test, and
the answer itself.
