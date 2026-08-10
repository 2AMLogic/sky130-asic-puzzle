# Independent review — 2026-08-10

## Recommendation

**Send with wording changes, not as-is.** The 121-bit word, its uniqueness at the stated
bound, its gate-level replay, and the 15-byte output message reproduced. However:

1. Do not call the design exactly a “non-attacking placement validator.” The stated
   placement rules admit **31,197,434** rasters, whereas the extracted circuit accepts one
   word at the bound. Say instead that the unique accepted word has those properties and
   that the structure is consistent with checking some of them.
2. Qualify extraction fidelity. The only puzzle oracle has very low internal coverage: in
   my cycle-level reconstruction of its 312 rising edges, **152/728 functional cells never
   toggled**, including **120 cells in the transitive cone of `O[7:0]`** and **89 in the
   cone of `success`**. A cold-logic extraction error could escape the published replay.
3. Replace the CNF clause-count explanation. 108,609 versus 108,610 is deterministic:
   `run_solve --max-solutions 2` adds one solution-blocking clause for the uniqueness call;
   `run_answer` stops after the first solution and reports the base CNF.
4. Keep “unique” explicitly qualified as “the 121-bit active word” or “at the 121-cycle
   bound.” Longer active windows have multiple sequences with unused suffix bits.

## Verdicts

### Claim 1 — extraction is functionally faithful: **unverifiable**

Fresh extraction was byte-identical to both committed artifacts, the warm-up extraction
was structurally equivalent to its published netlist, and the puzzle replay reproduced all
post-initialization output values. Those checks establish reproducibility and some
functional agreement; they do not establish full puzzle extraction fidelity because no
ground-truth puzzle netlist exists.

The request says cell coverage is derivable from the “existing simulated VCD plus the
netlist,” but `.sim-work/replay/sim_out.vcd` contains only `clk`, `rst_n`, `enable`, `I`,
`O`, and `success`; it contains no internal nets. I therefore sampled all gate/flop outputs
with the repo's independently self-tested cycle model using the VCD input values at all 312
rising edges. I ran both uniform initial values for the four unresettable flops and took the
union. Of the 728 functional cells (636 combinational + 92 flops), 576 toggled and 152 did
not. The extractor also emits 10 antenna diodes, accounting for the difference between 728
functional cells and the inventory's 738 signal/sequential instances; diodes are excluded
from the Boolean model.

Static backward cones contain 696 cells for `O[7:0]` and 468 for `success`. The cold
intersections are respectively 120 and 89 cells. Thus unexercised logic is load-bearing for
the claimed outputs, and a dropped or miswired connection there would not necessarily be
caught by the 24 observed output transitions. A broader independent oracle (a published
reference netlist, layout-vs-netlist comparison using a second extractor, or high-coverage
differential tests against the original design) is needed to confirm claim 1.

`net_00575` physically resolves as one extracted island joining `A1` on
`a31oi_2_172770_89520` and `A1` on `a311o_2_177370_89520`; no cell output pin resolves to
that island. This is consistent with a genuinely floating routed stub in the GDS, not a
Verilog-emission omission. It is not an independent proof that the geometry tracer did not
miss a remote conductor/driver, so it does not retire the general extraction risk. Both
Boolean polarities produce `success=1` for the solved word.

### Claim 2 — the 121-bit word drives `success`: **confirmed relative to the extracted netlist**

The solver independently re-derived the recorded word, and Icarus against the fresh
extraction and installed sky130 models reported `success=1` at cycles 126–129 and
`RESULT PASS`. All 16 initial combinations of the four unresettable flops passed at the
goal; `net_00575=0` and `net_00575=1` both passed. This cannot independently validate the
GDS-to-netlist step for the reasons under claim 1.

### Claim 3 — uniqueness at the bound: **confirmed, with required qualification**

At 121 active cycles, a second SAT call with the found 121 input literals blocked returned
UNSAT. At 120 cycles the goal is UNSAT. At 124 cycles I found three solutions immediately;
they share the accepted 121-bit prefix and differ in the three unused suffix bits. Therefore
the 121-bit active word is unique, but arbitrary longer input sequences are not.

The reset/idle/active shape is internally consistent with the example VCD: 3 reset cycles,
1 idle cycle, then 121 active cycles. This still relies on interpreting the VCD clocking and
the extracted counter correctly; there is no external protocol specification that rules out
a jointly consistent extraction/scenario off-by-one.

### Claim 4 — exact non-attacking-placement validator: **refuted as worded**

An independent dynamic-programming enumeration of exactly the stated predicate—11×11,
two marks in each row, two in each column, and minimum Chebyshev distance at least 2—found
31,197,434 valid rasters. The extracted circuit's bounded model has exactly one accepted
121-bit word. It therefore cannot implement exactly that predicate at the reviewed bound.

The accepted word itself does satisfy the predicate: length 121, popcount 22, every row and
column count is 2, and minimum pairwise Chebyshev distance is 2. The structural observations
may show that the circuit checks these conditions among additional constraints. They do not
justify naming those conditions as the complete validator semantics.

### Claim 5 — answer message `(* TWO STARS *)`: **confirmed relative to the extracted netlist**

A fresh 195-cycle gate-level run emitted a single 15-byte printable run on cycles 126–140
when `O[0]` is the LSB: `(* TWO STARS *)`. The reverse order had only five printable bytes
and no printable run longer than one. The next 54 observed bytes were zero, so the 15-byte
boundary is not an observation-tail artifact. The 9-byte result under the short tail is the
literal prefix `(* TWO ST`, not a complete competing message. Selecting the conventional
`O[7:0]` numeric bit order is stronger justification than printability alone; extraction
fidelity remains the upstream caveat.

## Commands run and literal output

### Fetch and warm-up regression

```sh
./scripts/fetch-puzzle.sh
```

```text
puzzle/ already present — updating
Already up to date.
...
puzzle/ ready. It is gitignored; do not commit its contents.
```

```sh
./scripts/warmup-regression.sh
```

```text
30 passed, 0 failed, 0 skipped
19 passed, 0 failed, 0 skipped
14 passed, 0 failed, 0 skipped
EQUIVALENT
  signal cells    79 matched 1:1 (A has 79, B has 79)
  nets            84 matched (A has 84, B has 84)
  verification  independent re-check of the full mapping passed
Warm-up regression complete.
```

### Fresh puzzle extraction

```sh
tools/extract puzzle/puzzle.gds \
  -o .sim-work/independent-review/puzzle-extracted.v \
  --json .sim-work/independent-review/puzzle-netlist.json --stats
shasum -a 256 evidence/puzzle-extracted.v \
  .sim-work/independent-review/puzzle-extracted.v \
  evidence/puzzle-netlist.json .sim-work/independent-review/puzzle-netlist.json
```

```text
instances (top cell, all classes): 9875
  logic: 646
  sequential: 92
  fill: 880
  via: 8221
  other: 36
emitted signal instances: 738
flip-flops: 92 {'dfrtp': 84, 'dfstp': 4, 'dfxtp': 4}
nets: 739  named ports: 13
cd9599ddcafda0bf986777676f7797110c0b20702b62e3ecbb022847af35de77  evidence/puzzle-extracted.v
cd9599ddcafda0bf986777676f7797110c0b20702b62e3ecbb022847af35de77  .sim-work/independent-review/puzzle-extracted.v
448117d3298d393c3ab7adde50f58fd6432e93c6ec9f059c52691771c1f3f195  evidence/puzzle-netlist.json
448117d3298d393c3ab7adde50f58fd6432e93c6ec9f059c52691771c1f3f195  .sim-work/independent-review/puzzle-netlist.json
```

Both `diff -u` comparisons produced no output and exited 0.

### Puzzle VCD replay

```sh
python3 -m tools.sim.run_vcd_replay --netlist \
  .sim-work/independent-review/puzzle-extracted.v \
  --vcd puzzle/example_inputs.vcd --top puzzle \
  --inputs clk,rst_n,enable,I --outputs O,success \
  --port-map 'clk=clk,rst_n=rst_n,enable=enable,I=I,success=success,O=\O[0]:\O[1]:\O[2]:\O[3]:\O[4]:\O[5]:\O[6]:\O[7]'
```

```text
Compared through t=3120000 (1ps units)
Simulated trace: .sim-work/replay/sim_out.vcd
RESULT FAIL — first divergence at t=1000 signal=O
  expected: xxxxxxxx
  actual:   00000000
```

This is a literal failure under exact timestamp comparison. The separately checked value
sequence agrees after initialization, but I do not relabel the command PASS.

### Solve and simulation

```sh
.sim-work/review-venv/bin/python -m tools.sim.run_solve \
  --netlist .sim-work/independent-review/puzzle-extracted.v \
  --structure --verify --max-solutions 2 --grid-width 11
```

```text
Flip-flops: 84 x dfrtp_2, 4 x dfstp_2, 4 x dfxtp_2
Total flops: 92   combinational gates: 636
Undriven nets read by logic: net_00575
Bound: 130 clock cycles (3 reset, 1 idle, 121 active, 5 tail)
CNF: 19985 variables, 108610 clauses
Solutions found: 1
  solution 0: I[4..124] = 0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000
UNIQUE — a further solve with the 1 solution(s) above blocked returned UNSAT, so no other input sequence works at this bound
Cycles where success == 1: [126, 127, 128, 129]
RESULT PASS
VERIFIED — the solved sequence drives success to 1 in a gate-level simulation of the netlist
```

The solver self-test printed `RESULT PASS`; the answer-decoder self-test printed
`SELF-TEST PASS (3/3 checks passed)`.

### Coverage analysis

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  .sim-work/independent-review/analyze.py
```

```text
rising edges sampled: 312
cells total: 728 (gates=636, flops=92)
toggled with dfxtp initial 0: 576
toggled with dfxtp initial 1: 576
toggled union: 576; never toggled: 152
success transitive cone: 468 cells; cold intersection: 89
O[7:0] transitive cone: 696 cells; cold intersection: 120
either observed output cone: 696 cells; cold intersection: 120
net_00575 consumers: a31oi_2_172770_89520 a311o_2_177370_89520
```

### Robustness, grid arithmetic, and longer windows

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  .sim-work/independent-review/robustness.py
```

```text
unresettable flops: 4; power-up combinations passing at goal: 16/16
net_00575=0: success@129=1
net_00575=1: success@129=1
word length=121 popcount=22 rows=[2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2] cols=[2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2] min_chebyshev=2
```

```text
active=120: RESULT UNSAT at bound 129
active=121: Solutions found: 1
active=124: Solutions found: 3
```

The three 124-cycle words had the identical solved 121-bit prefix and suffixes `000`,
`100`, and `010` (printed first-bit first).

### Independent predicate count

```text
independent constraint solutions: 31197434
DP states: 438748
```

This was a memoized row-by-row enumeration. Candidate rows contain exactly two
non-adjacent marks; transitions reject vertical/diagonal touching; the state tracks all 11
column counts and requires each to equal two after row 11.

### Answer and clause count

```sh
.sim-work/review-venv/bin/python -m tools.sim.run_answer \
  --netlist .sim-work/independent-review/puzzle-extracted.v \
  --active-cycles 121 --observe-cycles 65
```

```text
CNF: 19985 variables, 108609 clauses
RESULT PASS
index0_lsb (O[0]=LSB): 15/70 printable bytes, longest printable run 15 bytes
  .(* TWO STARS *)......................................................
index0_msb (O[0]=MSB): 5/70 printable bytes, longest printable run 1 bytes
  ..T.*....*.J..T.......................................................
Message cycles: 126..140 (15 bytes)
Message: '(* TWO STARS *)'
```

Inspection of `enumerate_solutions` explains the count exactly: the uniqueness run's
second solve adds one blocking clause; the one-solution answer run does not.

## Timing-offset anomaly

The common +1000 ps does not demonstrate equal physical path delay. These simulations use
functional models with ``UNIT_DELAY=#1`` on the flip-flop UDP, not extracted/SDF delays.
`success` is a `dfrtp_2.Q` and therefore changes one `UNIT_DELAY` after the edge. Each `O`
bit ends at a zero-delay functional `and3_2`; for the observed transitions its upstream
combinational inputs have already settled and the clocked state change arrives one quantum
late. Thus both observed ports can change at +1000 ps even though their static gate depths
differ. This explains the observation in this simulator; it is not a timing-fidelity check.

## What remains unchecked

- No independent puzzle netlist or second physical extractor was available, so cold-logic
  connectivity remains unverified.
- The coverage calculation uses the repo's cycle model, not an internal-net VCD; the
  supplied replay VCD simply lacks internal signals. An instrumented full internal VCD or
  toggle report from a separate simulator would cross-check the exact counts.
- I did not perform transistor-level LVS or analog simulation.
- I did not obtain an external protocol specification beyond `example_inputs.vcd`; it is
  therefore impossible to eliminate every jointly consistent extraction/scenario error.
