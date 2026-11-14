# Easter egg hunt

This is the append-only evidence record requested by `EASTER-EGG-HUNT.md`.

## Lead 2 — cold output logic and alternate message

The independent-review coverage count was first reproduced unchanged:

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
```

A committed extension, `evidence/easter-egg-cold-connectivity.py`, prints
the complete sorted 152-cell set and its 120-cell `O[7:0]` subset, then adds
an undirected adjacency whenever two cold cells share a directed
producer-to-consumer net. Its connectivity summary was:

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-cold-connectivity.py
```

The script emits both complete sorted lists. Its literal summary lines are:

```text
all cold cells (152):
cold cells in O cone (120):
induced directed edges: 178
weak components: 7; sizes: 112 3 1 1 1 1 1
```

Thus the cold output logic is not wholly connected, but 112/120 cells form
one large weakly connected subcircuit. The remaining components contain 3,
1, 1, 1, 1, and 1 cells.

The alternate-output BMC asked for any byte on `O[7:0]` that does not occur
in the recorded trace or the independently decoded `(* TWO STARS *)`
message. The query used the same 3-reset, 1-idle, 121-active, 65-tail
scenario as `run_answer`, with no `success` constraint. The first witness
was independently replayed against the extracted gate-level Verilog with
Icarus:

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-bmc-unseen-o.py
```

```text
recorded O bytes: 00 20 28 29 2a 41 47 49 4e 4f 52 53 54 57 59
SAT: cycle=126 O=0x42 solver=cadical195 seconds=0.129592
active I bits: 1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111
success at target: 0
gate-level verification: PASS
RESULT PASS
index0_lsb: .BIG BANG........................................................
index0_lsb longest printable: 'BIG BANG'
index0_msb: .B...B.r.........................................................
index0_msb longest printable: 'B'
```

The 121-bit all-ones word is therefore a verified failing input
(`success=0`) that selects a second output message, **`BIG BANG`**. This is
not merely an alternate top-level value: cycle-model replay of the witness
toggled 78 cells that were cold under the recorded accepted trace, all 78
within the `O[7:0]` cone:

```text
formerly cold cells toggled by all-ones witness: 78
formerly cold O-cone cells toggled by all-ones witness: 78
```

The SAT result alone was not treated as proof. `RESULT PASS` above is from
the separate Icarus replay against `.sim-work/independent-review/puzzle-extracted.v`.

## Lead 3 — longer accepting inputs and failing-input messages

`evidence/easter-egg-lead3.py` enumerates up to eight solutions at four
active bounds, compares every sampled word's first 121 bits with the unique
accepted word, and gate-level replays representative accepting and failing
inputs. Unlike `run_answer`, it always begins output sampling at cycle 125;
therefore enlarging the active window cannot truncate the beginning of a
message.

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-lead3.py
```

```text
== longer accepting windows ==
active=121: solutions_sampled=1 exhausted=True material_prefix_differences=0 suffixes=(none)
active=122: solutions_sampled=2 exhausted=True material_prefix_differences=0 suffixes=0 1
active=124: solutions_sampled=8 exhausted=True material_prefix_differences=0 suffixes=000 100 010 110 001 101 011 111
active=128: solutions_sampled=8 exhausted=False material_prefix_differences=0 suffixes=0000000 0001000 0010000 0011000 0000100 0001100 0010100 0011100
== gate-level output decoding ==
accepted-121: sim=PASS success_cycles=126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189
accepted-121: .(* TWO STARS *).................................................
accepted-121: longest_printable='(* TWO STARS *)'
accepted-128-representative: sim=PASS success_cycles=126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189
accepted-128-representative: .(* TWO STARS *).................................................
accepted-128-representative: longest_printable='(* TWO STARS *)'
fail-all-zero: sim=PASS success_cycles=none
fail-all-zero: .EMPTY SKY.......................................................
fail-all-zero: longest_printable='EMPTY SKY'
fail-all-one: sim=PASS success_cycles=none
fail-all-one: .BIG BANG........................................................
fail-all-one: longest_printable='BIG BANG'
fail-alternating-01: sim=PASS success_cycles=none
fail-alternating-01: .TRY AGAIN.......................................................
fail-alternating-01: longest_printable='TRY AGAIN'
fail-alternating-10: sim=PASS success_cycles=none
fail-alternating-10: .TRY AGAIN.......................................................
fail-alternating-10: longest_printable='TRY AGAIN'
fail-accepted-complement: sim=PASS success_cycles=none
fail-accepted-complement: .TRY AGAIN.......................................................
fail-accepted-complement: longest_printable='TRY AGAIN'
fail-single-one-first: sim=PASS success_cycles=none
fail-single-one-first: .TRY AGAIN.......................................................
fail-single-one-first: longest_printable='TRY AGAIN'
fail-single-one-last: sim=PASS success_cycles=none
fail-single-one-last: .TRY AGAIN.......................................................
fail-single-one-last: longest_printable='TRY AGAIN'
```

No materially different accepting prefix was found. At 122 and 124 active
cycles the complete solution spaces are exactly the accepted 121-bit word
followed by arbitrary unused suffix bits. The eight sampled 128-cycle
solutions have the same property, and a representative gate-level replay
emits the unchanged `(* TWO STARS *)` message.

Failing inputs deliberately select at least three messages:

- all zero: **`EMPTY SKY`**;
- all one: **`BIG BANG`**;
- the five other structured failures tested: **`TRY AGAIN`**.

Every message above came from an Icarus simulation of the extracted
gate-level netlist; none is a SAT-model-only decode.

## Lead 1 — the layout as a picture

Method: a census of all 41 GDS layers of `puzzle/puzzle.gds` (flat shape
counts, bounding boxes, text objects, and per-cell shape origins), a
rendering of every layer to an image, a placement scatter of all 9,875
top-level instances by class, and two anomaly scans (non-rectilinear
polygons; clusters of small square tiles on wiring layers). Two deliberate
marks were found; everything else was negative.

### Found: Morse code below the die — `PER ARENAM AD ASTRA`

Layer **200/0** (no sky130 assignment) holds exactly 36 rectangles in a
2.72 um tall strip **outside the die**, at y = -52.72..-50.00 um. The 36
shapes are contributed by the 36 `INTERNAL_3`/`INTERNAL_7` placements (one
rectangle each) — the "bookkeeping" cells were the easter egg all along.
Rectangle widths are exactly 1.38 um and 4.14 um (1:3), and the gaps
between them are exactly 1, 3, or 7 units of 1.38 um: International Morse
code (dot, dash; element/letter/word spacing).

```sh
PYTHONPATH=. python3 evidence/easter-egg-morse-strip.py
```

```text
layer 200/0 shapes: 36
defining cells: INTERNAL_3, INTERNAL_7
strip bbox um: (1.33,-52.72) - (198.67,-50.00)
rect widths um: min 1.38 max 4.14 (unit = 1.38)
gaps seen (units): [1, 3, 7]
morse: . - - . . . - . . - . - . . - . . - - - . - - . . . - . . . - . - . . -
DECODED: PER ARENAM AD ASTRA
wrote evidence/easter-egg-morse-strip.svg
```

*"Through sand, to the stars"* — the sky130 pun on *per aspera ad astra*,
and a companion to the accepted-input message `(* TWO STARS *)`. (The
Voyager Golden Record is the famous carrier of *per aspera ad astra* in
Morse; a record-like glyph also appears below.) A to-scale rendering is in
`evidence/easter-egg-morse-strip.svg`.

### Found: a concentric-ring glyph drawn in met2

met2 (69/20) carries a compact cluster of 1,366 axis-aligned 0.30 um
square tiles forming **three concentric broken rings**, centered at
(43.39, 43.71) um, outer radius 8.93 um. It is the only isolated
artwork-like cluster on any wiring layer (all other small-tile clusters
coincide with routed logic regions), it exists on met2 only, and it
connects to nothing.

```sh
PYTHONPATH=. python3 evidence/easter-egg-met2-ring.py
```

```text
met2 tiles inside window (34.0, 33.0, 54.0, 53.0): 1366
tile width um: min 0.300 med 0.300 max 0.300
tile height um: min 0.300 med 0.300 max 0.300
glyph center um: (43.39,43.71)
outer radius um: 8.93
ring r=3.5-5.0 um: 300 tiles, covered 334.5 deg, gaps: 25.5 deg at 309.5 deg
ring r=5.3-7.0 um: 470 tiles, covered 344.0 deg, gaps: 16.0 deg at 193.5 deg
ring r=7.4-8.8 um: 596 tiles, covered 346.0 deg, gaps: 14.0 deg at 46.5 deg
wrote evidence/easter-egg-met2-ring.svg
```

Each ring has exactly one gap, and the gaps rotate inward by ~145 deg per
ring (46.5 -> 193.5 -> 309.5): the glyph reads as a small circular maze —
or a record seen from above, which pairs with the Morse motto. The
rendering is in `evidence/easter-egg-met2-ring.svg`.

### Searched and negative

- **Text objects.** 11,944 text objects across 8 layers; all 118 unique
  strings are standard cell pin names, cell-name labels, the chip ports
  (`I`, `O[0..7]`, `clk`, `enable`, `rst_n`, `success`), `LO`/`HI`, plus
  12x `resistive_li1_ok` and 12x `no_jumper_check` DRC-waiver markers
  (their shape counts match marker layers 66/15 and 81/23). No hidden
  words.
- **Non-rectilinear polygons.** Zero anywhere in the layout — both eggs
  above are pixel-art from axis-aligned rectangles.
- **met3/met4/met5 and via3/via4 geometry** (the layers `klt extract`
  ignores): met5 is 9 horizontal power-strap pairs, met4 is vertical
  straps plus signal risers, met3 is ordinary signal routing. No artwork.
- **Fill uniformity.** 676 `tapvpwrvgnd_1` on a regular grid, 204
  `decap_3` in two die-edge columns, 10 scattered `diode_2` (antenna
  diodes). No pattern in fill.
- **Placement scatter.** Logic, flop, and via positions cluster by
  function only; the 4 `dfstp_2` and 4 `dfxtp_2` sit together near
  (165-180, 180-255) um but spell nothing.

## Lead 5 — floating net, unusual flops, and timing offset

`evidence/easter-egg-lead5.py` builds forward cones for the eight unusual
flops and `net_00575`, compares both initial values of the four unresettable
flops, and compares both Boolean interpretations of the floating net on
the four known output-message classes.

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-lead5.py
```

```text
== unusual flop structure ==
dfxtp_2_169550_250000: cell=dfxtp_2 D=net_00123 Q=net_00010 async=none async_value=0 forward_cells=203 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfxtp_2_167710_247280: cell=dfxtp_2 D=net_00047 Q=net_00009 async=none async_value=0 forward_cells=203 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfxtp_2_168630_252720: cell=dfxtp_2 D=net_00101 Q=net_00004 async=none async_value=0 forward_cells=203 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfxtp_2_168630_241840: cell=dfxtp_2 D=net_00058 Q=net_00011 async=none async_value=0 forward_cells=203 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfstp_2_167710_190160: cell=dfstp_2 D=net_00347 Q=net_00020 async=SET_B async_value=1 forward_cells=79 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfstp_2_166790_187440: cell=dfstp_2 D=net_00360 Q=net_00033 async=SET_B async_value=1 forward_cells=79 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfstp_2_172770_198320: cell=dfstp_2 D=net_00362 Q=net_00334 async=SET_B async_value=1 forward_cells=79 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
dfstp_2_167710_179280: cell=dfstp_2 D=net_00322 Q=net_00319 async=SET_B async_value=1 forward_cells=79 reaches=O[0],O[1],O[2],O[3],O[4],O[5],O[6],O[7]
== special-flop activity and floating-net sensitivity ==
accepted: special_flops_toggled=8 names=dfxtp_2_169550_250000,dfxtp_2_167710_247280,dfxtp_2_168630_252720,dfxtp_2_168630_241840,dfstp_2_167710_190160,dfstp_2_166790_187440,dfstp_2_172770_198320,dfstp_2_167710_179280 dfxtp_initializations_converge_at_cycle=1 dfxtp_init_changes_outputs=False net_00575_changes_outputs=False
accepted special state cycles 0..6: 0:00001111 1:00001111 2:00001111 3:00001111 4:00001111 5:00000000 6:00001011
all-zero: special_flops_toggled=8 names=dfxtp_2_169550_250000,dfxtp_2_167710_247280,dfxtp_2_168630_252720,dfxtp_2_168630_241840,dfstp_2_167710_190160,dfstp_2_166790_187440,dfstp_2_172770_198320,dfstp_2_167710_179280 dfxtp_initializations_converge_at_cycle=1 dfxtp_init_changes_outputs=False net_00575_changes_outputs=False
all-one: special_flops_toggled=8 names=dfxtp_2_169550_250000,dfxtp_2_167710_247280,dfxtp_2_168630_252720,dfxtp_2_168630_241840,dfstp_2_167710_190160,dfstp_2_166790_187440,dfstp_2_172770_198320,dfstp_2_167710_179280 dfxtp_initializations_converge_at_cycle=1 dfxtp_init_changes_outputs=False net_00575_changes_outputs=False
alternating: special_flops_toggled=8 names=dfxtp_2_169550_250000,dfxtp_2_167710_247280,dfxtp_2_168630_252720,dfxtp_2_168630_241840,dfstp_2_167710_190160,dfstp_2_166790_187440,dfstp_2_172770_198320,dfstp_2_167710_179280 dfxtp_initializations_converge_at_cycle=1 dfxtp_init_changes_outputs=False net_00575_changes_outputs=False
== net_00575 forward reachability ==
consumers: a31oi_2_172770_89520 a311o_2_177370_89520
forward_cells=10 reaches=O[1],O[4]
```

The unusual flops are the output generator's eight state bits. The set
flops deliberately establish four ones during reset (`00001111` in the
script's dfxtp-then-dfstp order). The plain flops need no reset because
their two extreme initializations converge after the first modeled edge,
long before message emission. This is implementation economy, not an
additional hidden payload.

The floating net is a real extracted island with two consumers, as already
shown physically by the independent review. Its ten-cell forward cone can
reach only `O[1]` and `O[4]`; forcing it low or high did not change any
sampled output for the accepted, all-zero, all-one, or alternating traces.
This does not prove global irrelevance for every possible input, but the
search produced no evidence that it is an Easter egg.

Finally, the fixed +1000 ps offset is exactly one functional-model
``UNIT_DELAY=#1`` under the PDK primitives' `1ns/1ps` timescale. Flip-flop
clock-to-Q changes receive that one delay; the functional combinational
models are zero-delay, so the offset does not accumulate with static gate
depth. The initial -4000 ps outlier is the separate asynchronous-reset
settling event documented in `evidence/puzzle-replay.md`. This is a
simulation timing artifact, not a hidden message or physical delay claim.

## Lead 4 — the missing constraint and recovered regions

The answer and its “two stars” message suggest a two-star Star Battle, whose
rules also require exactly two stars in each irregular region. This was
tested structurally rather than accepted from the name. For each of the 121
raster positions, `evidence/easter-egg-lead4.py` compares an all-zero trace
with a one-hot trace and records which two-flop feedback groups change.

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-lead4.py
```

The full script output lists every group, cell position, and flop pair.
Selected literal lines and the complete recovered map are:

```text
two-flop feedback groups: 23
membership-count histogram: 2:11 3:110
group 0: cells=11 positions=r0c5 r1c5 r2c5 r3c5 r4c5 r5c5 r6c5 r7c5 r8c5 r9c5 r10c5 flops=dfrtp_2_113430_236400,dfrtp_2_115730_239120
group 1: cells=11 positions=r0c4 r1c4 r2c4 r3c4 r4c4 r5c4 r6c4 r7c4 r8c4 r9c4 r10c4 flops=dfrtp_2_113430_230960,dfrtp_2_115730_228240
group 11: cells=28 positions=r0c10 r1c10 r2c10 r3c7 r3c10 r4c5 r4c6 r4c7 r4c8 r4c9 r4c10 r5c7 r6c7 r7c7 r8c4 r8c5 r8c6 r8c7 r9c5 r9c6 r9c7 r10c4 r10c5 r10c6 r10c7 r10c8 r10c9 r10c10 flops=dfrtp_2_114810_138480,dfrtp_2_118030_133040
group 22: cells=110 positions=r0c0 r0c1 r0c2 r0c3 r0c4 r0c5 r0c6 r0c7 r0c8 r0c9 r1c0 r1c1 r1c2 r1c3 r1c4 r1c5 r1c6 r1c7 r1c8 r1c9 r2c0 r2c1 r2c2 r2c3 r2c4 r2c5 r2c6 r2c7 r2c8 r2c9 r3c0 r3c1 r3c2 r3c3 r3c4 r3c5 r3c6 r3c7 r3c8 r3c9 r4c0 r4c1 r4c2 r4c3 r4c4 r4c5 r4c6 r4c7 r4c8 r4c9 r5c0 r5c1 r5c2 r5c3 r5c4 r5c5 r5c6 r5c7 r5c8 r5c9 r6c0 r6c1 r6c2 r6c3 r6c4 r6c5 r6c6 r6c7 r6c8 r6c9 r7c0 r7c1 r7c2 r7c3 r7c4 r7c5 r7c6 r7c7 r7c8 r7c9 r8c0 r8c1 r8c2 r8c3 r8c4 r8c5 r8c6 r8c7 r8c8 r8c9 r9c0 r9c1 r9c2 r9c3 r9c4 r9c5 r9c6 r9c7 r9c8 r9c9 r10c0 r10c1 r10c2 r10c3 r10c4 r10c5 r10c6 r10c7 r10c8 r10c9 flops=dfrtp_2_78930_108560,dfrtp_2_81690_97680
recovered region map (A=group11 through K=group21):
HHHHHCCKFFA
HHIHHCKKFFA
HHICCCCKKFA
HHICGGGAKKA
IHICGAAAAAA
IIICGGGAEEE
CCCCCCGAEBB
CDDDGGGAEBB
CDDJAAAAEBB
CCDJJAAAEEE
CDDJAAAAAAA
accepted region counts: A=2 B=2 C=2 D=2 E=2 F=2 G=2 H=2 I=2 J=2 K=2
region cells total: 121
```

Groups 0–10 are the 11 column counters. Groups 11–21 are 11 disjoint
irregular regions that cover the entire board. Group 22 is the reused
per-row counter: the one-hot method sees columns 0–9, while the last-cell
transition is combined with end-of-row handling and does not persist as a
separate differential state. This is why most positions affect three
groups (column, region, row) and the 11 last-column positions affect two.

As an independent check, the script builds a fresh CNF containing only the
recovered puzzle rules: exactly two marks in every row, column, and region,
plus no horizontally, vertically, or diagonally touching pair. It does not
use the gate-level acceptance circuit. Blocking its first solution and
solving again gives:

```text
independent recovered-rule CNF: vars=1309 clauses=2796 solutions_up_to_2=1
recovered-rule solution 0: 0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000
recovered rules unique and equal accepted: True
```

Therefore the previously unknown predicate is the omitted Star Battle
region rule. Adding the 11 recovered irregular regions cuts the
31,197,434 grids satisfying only the published row/column/non-touching
properties to exactly the circuit's one accepted word.

## Deliverable — draft for the form's "Easter Eggs" field

Everything below is verified in the sections above; each clause traces to
a committed script and its literal output.

*(Historical note: the version actually submitted on 2026-08-10 predates the
fifth-message discovery — it is preserved in git at `74a2703`. The paragraph
below is the current five-message version, kept for the post-close
publication and any operator-chosen supplement to Jane Street.)*

> The chip answers back when you get it wrong — and we proved the complete
> message set by exhaustive BMC over all failing inputs. All-zeros input
> emits `EMPTY SKY` on O[7:0], all-ones emits `BIG BANG`, and a grid that
> satisfies every row, column, and region count but lets two stars touch
> gets a targeted diagnostic: **`TWO"NOT TOUCH`** — the `"` a ditto mark
> for STARS. Every other failing word emits `TRY AGAIN`; exactly these two
> failure streams exist, for all 16 power-up states of the unresettable
> flops (gate-level Icarus replays, not solver decodes). Below
> the die, GDS layer 200/0 spells **`PER ARENAM AD ASTRA`** — "through
> sand, to the stars" — in Morse code built from the 36 `INTERNAL_*`
> placements (1:3 dot/dash rectangle widths, 1/3/7-unit gaps). met2
> carries a hidden ~18 µm glyph of three concentric broken rings connected
> to nothing — a tiny circular maze, or a record seen from above. And the
> rules page omitted one constraint on purpose: differential analysis of
> the circuit's two-flop counters recovers **11 irregular Star Battle
> regions**; with "exactly two stars per region" added, the accepted grid
> is uniquely determined (31,197,434 candidates → 1) with no reference to
> the acceptance circuit.

## Addendum (2026-08-10, post-review-scoping) — claim 8 re-derived geometrically

The "connected to nothing" assertion for the met2 glyph originally rested on
cluster isolation. `evidence/easter-egg-ring-connectivity.py` re-tests it
with KLayout boolean `Region` interactions — a different method: electrical
connection to met2 requires met2 contact or a via1/via2 landing, and
met1/met3 crossing the same XY without a via is only an underpass.

```sh
PYTHONPATH=. python3 evidence/easter-egg-ring-connectivity.py
```

```text
glyph tiles: 1366  other met2 shapes in window: 0
  electrical met2 (non-tile): 0 shapes in window, 0 interacting with glyph tiles
  electrical via1 68/44: 0 shapes in window, 0 interacting with glyph tiles
  electrical via2 69/44: 0 shapes in window, 0 interacting with glyph tiles
  projection-only met1 68/20: 21 shapes in window, 7 crossing under/over the glyph (no via -> no connection)
  projection-only met3 70/20: 0 shapes in window, 0 crossing under/over the glyph (no via -> no connection)
RING VERDICT: ELECTRICALLY UNCONNECTED — no met2 contact and no via lands on it

morse strip shapes: 36
STRIP VERDICT: ISOLATED — no other layer's geometry touches the strip
```

Seven met1 wires pass beneath the glyph with no via reaching it; the glyph
exchanges no current with the design. The Morse strip touches nothing on
any other layer. An earlier draft of this script scored those met1
underpasses as "connected" — the refinement to electrical semantics is
recorded here deliberately, as the kind of false alarm the independent
reviewer should also guard against.

## Addendum (2026-08-10, second) — claims 7 and 8 finished off

**Claim 7, independent tooling.** `evidence/easter-egg-morse-independent.py`
re-derives the Morse message with no KLayout at all: a standard-library
GDSII binary parser (records, structures, BOUNDARY/XY, SREF transforms)
and its own Morse table. Two unrelated readers of the same bytes agree:

```sh
python3 evidence/easter-egg-morse-independent.py
```

```text
structures parsed: 81
cells with 200/0 geometry: {'INTERNAL_3': 1, 'INTERNAL_7': 1}
placed 200/0 rectangles: 36
strip y (dbu): bottom [-52720] top [-50000]
widths (dbu): min 1380 max 4140 unit 1380
INDEPENDENT DECODE: PER ARENAM AD ASTRA
```

**Claim 8, window caveat closed.** `evidence/easter-egg-glyph-survey.py`
drops the fixed search window and surveys the entire die: every met2 shape
that is an exact 0.30 um square is collected and clustered.

```sh
PYTHONPATH=. python3 evidence/easter-egg-glyph-survey.py
```

```text
met2 shapes: 1366 exact 0.3 um tiles, 7151 other
clusters (>= 50 tiles) over the whole die:
   1366 tiles  bbox (34.9,35.2)-(52.0,52.3)  non-tile met2 overlapping bbox:    0  -> ARTWORK-LIKE (no wiring inside)
SURVEY VERDICT: 1 artwork-like cluster(s) on met2 across the whole die
  -> 1366 tiles at (34.9,35.2)-(52.0,52.3)
```

All 1,366 exact-tile shapes on met2 belong to the one glyph; no other such
tile exists anywhere on the layer, so there is no fourth ring, tail, or
second glyph outside the original window.

## Addendum (2026-08-11) — a FIFTH message, and the complete message map, proven

The independent review's one open limitation was "`TRY AGAIN` universality is
sampled (169 failing words). A per-cycle BMC over all failing inputs would
close it; not run." Running it refuted universality:
`evidence/easter-egg-try-again-universality.py` enumerates every distinct
O[7:0] stream a failing word can produce (blocking clauses until UNSAT, the
4 unresettable power-up bits left free throughout) and proves the firing
condition of the new stream exactly.

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-try-again-universality.py
```

```text
accepted-word validation: success asserts
stream 1: '.TRY AGAIN'  (0.04s)
  witness word: 1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111110
stream 2: '.TWO"NOT TOUCH'  (0.84s)
  witness word: 1000000001000001010000000000010100011000000010000010000000001001000100000010000000100001000100000010000100100001100000000
enumeration COMPLETE: exactly 2 failure streams exist
diagnostic bytes: 00 54 57 4f 22 4e 4f 54 20 54 4f 55 43 48 00 00
class proof (counts-ok+touch => diagnostic): sat=False (2.71s)
converse proof: 66 queries, 0 unexpected SAT
power-up sweep: 1 distinct stream(s) across 16 combos
icarus sim ok: True
success cycles: none
icarus vs model: 0 mismatches; x-pessimism cycles [129, 138, 139, 140] (model proves these constant across all 16 power-ups)

COMPLETE MESSAGE MAP (proven, all 16 power-ups):
  accepted word                          -> (* TWO STARS *), success
  all-zeros                              -> EMPTY SKY
  all-ones                               -> BIG BANG
  all counts == 2 and >=1 touching pair  -> TWO"NOT TOUCH
  everything else                        -> TRY AGAIN
```

The fifth message is **`TWO"NOT TOUCH`** — 0x22, a ditto mark, between `TWO`
and `NOT`: read against the answer `(* TWO STARS *)`, it says *two stars,
not touch*. It fires **iff** a word satisfies every row, column, and
recovered-region count (all == 2) and violates only the adjacency rule —
the chip diagnoses the one subtle way to fail. The 169-word review sample
never saw it because every sampled family (random words, near-misses,
complements, alternations) breaks a counting constraint.

The Icarus replay confirms the witness gate-level (`success` never asserts;
every defined byte matches), with `x` at exactly four byte-cycles — classic
x-pessimism from the unresettable flops, at positions the 16-way power-up
sweep proves constant.

The earlier statement "every other failing input we tested emits `TRY
AGAIN`" (169 words) remains literally true; it is now superseded by the
exact map above. This addendum also completes the review's limitation list:
nothing about the message behavior is sampled any more — it is enumerated.

## Addendum (2026-09-08, post-close) — corrections from other solvers' writeups

Submissions closed 2026-09-04 and five external writeups are now public (README, "Other
solutions"). Reading them against this record turned up one error, one misidentification,
and two things never looked at. Each was verified here before being recorded.

### The ditto mark is the floating net — the fifth message is `TWO NOT TOUCH`

Two other solvers report the adjacency diagnostic as `TWO NOT TOUCH`. Lead 5 above notes
that `net_00575` (undriven, two consumers) can reach only `O[1]` and `O[4]`, and that forcing
it did not change the accepted / all-zero / all-one / alternating traces. The 2026-08-11
addendum's witness was never put through that check, and 0x22 vs 0x20 differ in exactly
bit 1. `evidence/easter-egg-floating-net-ditto.py` replays every message class under both
constants and prints Icarus's per-bit view of the witness:

```sh
PYTHONPATH=. .sim-work/review-venv/bin/python \
  evidence/easter-egg-floating-net-ditto.py
```

```text
undriven nets: ['net_00575']
accepted     uv=0 '.(* TWO STARS *)'  uv=1 '.(* TWO STARS *)'  success@[126]/[126]  diffs=[]
diag(touch)  uv=0 '.TWO"NOT TOUCH'  uv=1 '.TWO NOT TOUCJ'  success@[]/[]  diffs=[(129, '22', '20'), (138, '48', '4a'), (139, '00', '02'), (140, '00', '10')]
zeros        uv=0 '.EMPTY SKY'  uv=1 '.EMPTY SKY'  success@[]/[]  diffs=[]
ones         uv=0 '.BIG BANG'  uv=1 '.BIG BANG'  success@[]/[]  diffs=[]
tryagain     uv=0 '.TRY AGAIN'  uv=1 '.TRY AGAIN'  success@[]/[]  diffs=[]
icarus ok: True
  cycle 125: O[7:0]=00000000 -> 00 .
  cycle 126: O[7:0]=01010100 -> 54 T
  cycle 127: O[7:0]=01010111 -> 57 W
  cycle 128: O[7:0]=01001111 -> 4f O
  cycle 129: O[7:0]=001000x0 -> x
  cycle 130: O[7:0]=01001110 -> 4e N
  cycle 131: O[7:0]=01001111 -> 4f O
  cycle 132: O[7:0]=01010100 -> 54 T
  cycle 133: O[7:0]=00100000 -> 20  
  cycle 134: O[7:0]=01010100 -> 54 T
  cycle 135: O[7:0]=01001111 -> 4f O
  cycle 136: O[7:0]=01010101 -> 55 U
  cycle 137: O[7:0]=01000011 -> 43 C
  cycle 138: O[7:0]=010010x0 -> x
  cycle 139: O[7:0]=000000x0 -> x
  cycle 140: O[7:0]=000x00x0 -> x
  cycle 141: O[7:0]=00000000 -> 00 .
  cycle 142: O[7:0]=00000000 -> 00 .
  cycle 143: O[7:0]=00000000 -> 00 .
  cycle 144: O[7:0]=00000000 -> 00 .
```

So: with the net forced low the model says `TWO"NOT TOUCH`; forced high it says
`TWO NOT TOUCJ` plus two stray bytes; Icarus, which leaves the net `x`, reports `O[1]` as
`x` at the disputed byte (cycle 129) and at cycles 138–140, with `O[4]` also `x` at 140.
No single constant reproduces a clean `TWO NOT TOUCH`, which is consistent with the net
being a signal that should have been wired rather than a tie-off. The 2026-08-11 addendum's
line "x-pessimism cycles [129, 138, 139, 140] (model proves these constant across all 16
power-ups)" was true of the power-up bits and beside the point — the `x` is the undriven net.
jestoph reported this net ("a wire that's only connected to two input pins", "a connection on
a neighboring pin that isn't even an input or an output") to Jane Street and had it confirmed
as a bug the next day. The intended text, read from the ROM by Sunaabh, is `TWO NOT TOUCH`;
on silicon the affected bits are undefined. The "two stars, not touch" ditto reading is
withdrawn. The other four messages are unaffected (no diffs under either constant).

### The met2 glyph is the Jane Street logo

The concentric broken rings found under Lead 1 are Jane Street's registered
concentric-circle mark — three rings, one gap each, gaps rotating — compare
`evidence/easter-egg-met2-ring.svg` with the mark on janestreet.com. The "maze / record"
reading above is withdrawn. Two other writeups (Sunaabh, jestoph) identified it on sight.

### The VCD header was never read

`puzzle/example_inputs.vcd` opens with:

```text
$date
  Sat Dec 31 23:59:60 2016
$end
$version
	Leave no stone unturned! But for this file, consider looking at it in a waveform viewer instead.
$end
```

23:59:60 UTC on 2016-12-31 is the leap second — a timestamp that existed for exactly one
second. Nothing in this repo had looked at the header. One writeup links the date to Jane
Street's December 2016 puzzle "Star Search" and calls it a Star Battle variant; Jane Street's
solution page for that puzzle describes movie trivia (answer *Inception*), so the link is a
pun on "star" at most. The example input itself, decoded as two 11×11 words (242 enabled
cycles, 38 ones each), draws no picture we can recognise.

### The regions read as "JS" — partly

`evidence/region-map-render.py` renders the Lead 4 map as `evidence/region-map.png`.
Region G (rows 3–7, columns 4–6) is a block-letter S. Region A — bar on row 4, stem down
column 7, hook across rows 8–10 — reads as a J wrapped around it, with extra cells along the
right edge. One writeup calls the map "JS", the Jane Street wordmark. The S is certain; the J
is a fair reading, not a proof.

## Addendum (2026-10-02) — against Jane Street's official list

Jane Street published [Results from the ASIC puzzle](https://blog.janestreet.com/asic-puzzle-results/)
on 2026-10-02, with the full egg list: six intended eggs, plus a seventh that started as a
layout bug. Below, each one is checked against this record. "Submitted" means it was in the
2026-08-10 form; "later" means it was found after that.

| Official egg | Here | When |
|---|---|---|
| The two failed attempts in `example_inputs.vcd` decode as 7-bit ASCII to "THE NIGHT SKY AWAITS" | missed, then reproduced below | 2026-10-02 |
| VCD `$date` is the 2016 leap second; `$version` nudges you toward a waveform viewer | header found | later (2026-09-08) |
| Morse `PER ARENAM AD ASTRA` on an otherwise unused layer | found | submitted |
| Failure messages `EMPTY SKY`, `BIG BANG`, `TWO NOT TOUCH`, `TRY AGAIN` | three submitted, the fourth found after | submitted + later |
| About 1,400 isolated met2 squares form a 57×57 Jane Street logo | found, misread as a maze (our three rings hold 1,366 tiles) | submitted; identified 2026-09-08 |
| The eleven regions spell "JSC" | read as "JS" (partly) | later (2026-09-08) |
| A floating wire on the `TWO NOT TOUCH` path, which makes `TWO"NOT TOUCH` show up in simulation | found the floating input, but not until after we submitted | later (2026-08-11 / 2026-09-08) |

### "THE NIGHT SKY AWAITS" — reproduced

The post gives the plaintext but not the encoding. `evidence/easter-egg-vcd-night-sky.py`
finds it. Each attempt is the usual 121-bit word, fed in one bit per enabled clock. Lay it
out as an 11×11 grid in feed order, and the first seven cells of each row, read LSB first,
make one character. In all 22 rows, columns 7–10 are zero. So the "failed attempts" are
text written into the board.

```sh
python3 evidence/easter-egg-vcd-night-sky.py
```

```text
attempts: 2, lengths [121, 121]
message: 'The night sky awaits  '
```

The 2026-09-08 addendum above read these same two words as pictures ("draws no picture we
can recognise"). They hold text, not a picture.

### The regions spell "JSC" — the C was there too

In `evidence/region-map.png` the orange region is a block-letter C: a bar across row 5,
a stem down column 8, and a bar across row 9, open to the right. With region G's S and
region A's J, the map spells "JSC". The J is now confirmed rather than a fair reading.

### The ditto mark: what the 2026-09-08 correction got right and wrong

According to Jane Street, the floating wire was a real layout bug. They caught it in their own LVS
pass and left it in on purpose as an extra egg. In their words, solvers "diagnosed it down
to the floating `a31oi` input". Ours is `net_00575`, which drives
`a31oi_2_172770_89520.A1` (and `a311o_2_177370_89520.A1`) in `evidence/puzzle-extracted.v`.
So:

- The 2026-09-08 correction was right that the `"` comes from the floating net, and right
  that the ROM text is `TWO NOT TOUCH`.
- It was wrong to call the `"` an *extraction artifact*. The net is undriven in the layout
  itself. `klt` extracted it faithfully, and seeing `TWO"NOT TOUCH` in simulation, then
  tracing it to the floating input, was the seventh egg.
- The 2026-08-11 "two stars, not touch" ditto reading is still wrong: the `"` carries no meaning.
  The supplement email in `SUBMISSION.md` stays unsent, which is still correct.

### Scorecard

The submission carried three of the six intended eggs: Morse, the logo (found but misread),
and three of the four failure messages. Two more (the VCD header, and two of the
three "JSC" letters) were found after the close by reading other writeups. The VCD
plaintext was missed until today. Jane Street reports that two entrants found all six intended
eggs, and six found six of the seven. This writeup was not among the 15 they featured, and
the post names no winners or prizes.

## Addendum (2026-11-14) — the 15 featured writeups, one by one

Jane Street's results post featured 15 writeups (README §"Featured by Jane Street"), and
until today this record had not checked any of them against itself. This addendum does
that, one entry per writeup, in the post's order. Each entry has the same four fields:

- **Reached** — what was actually parsed, with type and size or page/word count. A 200 on
  the table URL is not evidence a writeup was read, and two of the 15 URLs serve a viewer
  page rather than the document.
- **Method** — one line, as the writeup presents it.
- **Against our record** — `nothing new`, `addition`, or `contradiction`, with the claim.
- **Status** — `reproduced` (naming the command), `already recorded` (citing file and
  line), or `unverified` (saying why not).

Three reproducers were added for this pass, and every `reproduced` below is one of their
printed lines:

```sh
# needs the sky130 cell models and Icarus; no puzzle file (the netlist is committed)
PDK_ROOT="$HOME/.volare" PYTHONPATH=. python3 evidence/featured-writeups-netlist.py
# pure Python, no inputs at all
python3 evidence/featured-writeups-grids.py
# the only one that reads puzzle/ — run ./scripts/fetch-puzzle.sh first
PYTHONPATH=. python3 evidence/featured-writeups-warmup-logo.py
```

The `PDK_ROOT` override is not cosmetic: `tools/sim/celltable.py` cannot parse the
`input wire X;` port declarations that current open_pdks emits, so on this host
`load_design()` fails against the `klt`-resolved PDK and the whole `tools/sim` stack is
unusable without it. That is our own defect, not `klt`'s, and is filed as #98. The pinned
root is open_pdks `c6d73a35`, the same one `evidence/puzzle-answer.md` recorded.

Most of these 15 differ from us in *method*, not in findings — an own C++ pipeline, an
FPGA, Minecraft, analog SPICE, a Groth16 proof. A method difference asserts nothing about
this record, so it needs no reproducer; the entries that do carry a claim are the ones
with commands attached.

### What this pass changed in our record

Two corrections and six additions. They are summarised here and carried into `README.md`;
the per-writeup entries below are the evidence.

**Correction 1 — README's "no other writeup contains" sentence was wrong on all three
counts.** README §"What the other solutions taught us" closed with: *"Things in our record
that no other writeup so far contains: the complete message map, proven … the
31,197,434-grid enumeration … and the SAT-independent uniqueness check from the recovered
rules alone."* Every one of the three is in the featured set:

- **31,197,434** is David Garner's number too, derived independently from a Perl generator,
  and he then simulated all ~31M boards through his netlist (about 6 hours on 16 cores),
  finding the one hit at line 29,300,056. `featured-writeups-grids.py` re-derives
  `31,197,434` and confirms the two counts are of the same thing.
- **The complete message map, proven** is Soto Franco's too: he enumerated the output
  generator's readable messages by solver until unsatisfiable and got exactly five. Amruth
  Gulawani's playable version reproduces all five, `TWO NOT TOUCH` included.
- **The SAT-independent uniqueness check** is Stephen Ebert's (backtracking that visits
  8,989 states, run with site packages disabled so it cannot import Z3) and Soto Franco's
  (solving the four recovered rules directly). `featured-writeups-grids.py` re-derives it
  here as well: exactly 1 board.

That sentence should not be replaced with a narrower boast. What is genuinely unusual in
this record is nothing on that list; it is the per-cell `klt` extraction trail and the
warm-up regression, which is the repo's actual purpose.

**Correction 2 — the floating net reaches `O[1]` *and* `O[4]`.** The 2026-10-02 addendum
above, and README item (1), name `O[1]` alone: *"Icarus … reports bit `O[1]` as `x` at
exactly that byte — and again at three cycles around the final `H`."* Ebert and Soto
Franco both say the cone reaches `O[1]` and `O[4]`, and they are right. The structural
cone of `net_00575` is 11 nets wide, touches no flip-flop D input, cannot reach `success`,
and lands on exactly `O[1]` and `O[4]`. The `O[4]` effect is invisible in the earlier
reading because it only shows on one cycle, 140 — the second trailing zero byte after the
message, not inside it:

```text
top-level outputs reached: ['O[1]', 'O[4]']
reaches success: False
  cycle 129: O[7:0]=001000x0  x on bits [1]
  cycle 138: O[7:0]=010010x0  x on bits [1]
  cycle 139: O[7:0]=000000x0  x on bits [1]
  cycle 140: O[7:0]=000x00x0  x on bits [1, 4]
```

Everything the earlier addendum concluded from this still holds — the net is a real layout
bug, the `"` carries no meaning, and the supplement email in `SUBMISSION.md` stays unsent.
Only the list of affected output bits was short by one.

**Addition 1 — the output generator's stream cipher, in full.** This is the largest thing
the featured set adds, and `NOTES-FOR-NEXT-TIME.md` line 49 already leans on it
(*"The answer string was XORed with an LFSR keyed on the board … someone reverse-engineered
the LFSR"*) without attribution and without any of the mechanism. It is Gabriel Taboada's,
and all of it reproduces against `evidence/puzzle-extracted.v`:

```text
shift chain: 8 flops, head (feedback + I) first
  b0 dfstp_2_172770_198320              dfstp_2   reset=1
  b1 dfrtp_2_167710_195600              dfrtp_2   reset=0
  b2 dfstp_2_167710_190160              dfstp_2   reset=1
  b3 dfrtp_2_173690_192880              dfrtp_2   reset=0
  b4 dfrtp_2_174610_182000              dfrtp_2   reset=0
  b5 dfstp_2_166790_187440              dfstp_2   reset=1
  b6 dfrtp_2_168630_176560              dfrtp_2   reset=0
  b7 dfstp_2_167710_179280              dfstp_2   reset=1
reset state b0..b7: 10100101 (weight 4)
feedback taps: (3, 4, 5, 7) -> b0(t+1) = I(t) XOR b3 XOR b4 XOR b5 XOR b7
characteristic polynomial: x^8 + x^4 + x^3 + x^2 + 1  (= 0x1d)
keystream: 65 87 db d7 44 36 3c e6 2d 22 95 3b b3 df a6   match: True
stored   : 4d ad fb 83 13 79 1c b5 79 63 c7 68 93 f5 8f   match: True
stored XOR keystream = '(* TWO STARS *)'  -> match: True
```

Read as a recurrence, taps at b3/b4/b5/b7 give `s(t+1) = s(t-3) ^ s(t-4) ^ s(t-5) ^ s(t-7)`,
whose characteristic polynomial is `x^8 + x^4 + x^3 + x^2 + 1` — `0x1d`, the CRC-8
SAE-J1850 polynomial, exactly as Taboada says. The register's eight flops are the only
four `dfstp_2` in the design (which reset high) plus four `dfrtp_2` (which reset low), so
the seed is four ones and four zeros. The keystream byte emitted on message cycle `126+j`
is those eight bits read LSB-first in chain order; searching all 8! bit orders against all
offsets in ±7 cycles finds that reading **uniquely** (1 match out of 564,480 candidates),
and it yields Taboada's 15 keystream bytes exactly. XORing them with the message this
record independently decoded recovers his 15 stored ROM bytes exactly. So the success row
is not stored as plaintext at all: it is a ROM row XORed with a CRC-8 of the board, which
is why forcing `success` on a wrong board prints garbage, and why no constant-address
probe of the printer ever reveals it. The four failure rows are plaintext and leak through
any cut; the winning row's address is the whole 121-bit board.

One caveat, stated rather than smoothed over: Taboada writes the seed as `00001111` and
the post-load register as `00101110`. Ours are `10100101` and `10100110` in chain order.
These are the same two states under a permutation of the flop-to-bit assignment — the
multiset of (reset, post-load) bit pairs matches — but it is *not* the assignment his own
keystream readout uses, which is the identity on our chain order. His bit labelling is
internally inconsistent between those two places in his writeup; the substance, and every
one of the 30 bytes, is right.

**Addition 2 — the Jane Street logo is in the warm-up layout too, bit for bit.** Sanjay
Ravishankar and David Garner both mention it in passing. This record had only ever looked
at `puzzle.gds` (`evidence/easter-egg-met2-ring.py`, 1,366 tiles). Both layouts carry the
*same* glyph:

```text
puzzle:  met2 shapes: 8517; isolated square tiles: 1366; tile side(s) um: [0.3]
         glyph bbox um: x[34.9, 51.7] y[35.2, 52.0];  position on the die: lower-left
warm-up: met2 shapes: 2104; isolated square tiles: 1366; tile side(s) um: [0.3]
         glyph bbox um: x[65.9, 82.7] y[66.2, 83.0];  position on the die: upper-right
offset warm-up -> puzzle: dx=+31.000 um dy=+31.000 um
symmetric difference: 0
identical glyph: True
```

1,366 tiles in each, the two tile sets equal once normalised to their own lower-left
corner, and the offset exactly 31.000 µm in both axes. Garner's "lower-left in the puzzle,
upper-right in the warm-up" is right as stated. Worth noting for the repo's own purposes:
the warm-up is not embargoed, so this is a non-embargoed instance of the same glyph.

**Addition 3 — the exact size of the `TWO NOT TOUCH` preimage.** Ravishankar reports
113,758,569 boards behind that message. Counting boards with two stars in every row,
column and region, with touching allowed, gives 113,758,570 — his number plus the one
clean board. So his figure is precisely the set of boards that satisfy every count and
break only the no-touch rule, which is exactly the message's precondition. This sharpens
the 2026-08-11 "complete message map" result from "exactly two failure streams exist
besides the three constant ones" to a cardinality, and the `-1` is an independent
restatement of our uniqueness claim.

**Addition 4 — the total-star counter is five bits, not eight.** Lokesh Aravapalli says
five and worries about what happens at 54 stars (54 mod 32 = 22); Shapovalov names eight
flops (`q57..q64`) and Ebert says "8 track total population". Our record says nothing, so
this is an addition rather than a correction, and the netlist settles it for Aravapalli.
Driving 0..31 stars under two unrelated placement patterns pins one flop per bit for bits
0–4 and finds no sixth bit, and the counter does wrap:

```text
  bit 0: ['dfrtp_2_80770_54160']   bit 1: ['dfrtp_2_80770_37840']
  bit 2: ['dfrtp_2_82610_43280']   bit 3: ['dfrtp_2_81690_48720']
  bit 4: ['dfrtp_2_77550_35120']
=> the counter is 5 bits wide (Aravapalli: 5; Shapovalov/Ebert: 8)
  22 contiguous stars -> counter reads 22 (22 mod 32 = 22)
  54 contiguous stars -> counter reads 22 (54 mod 32 = 22)
```

Aravapalli's worry is real and harmless: a 54-star board does set the "total is 22" wire,
but two stars per row caps an accepted board at 22 anyway, so the row and column checks
reject it long before the total matters. Five bits are sufficient *because* of the other
constraints, which is a design economy worth recording.

**Addition 5 — Smallwood's row combinatorics.** All of it checks out, and it is a cheaper
route to the search-space shape than the full enumeration: 45 legal rows out of
C(11,2) = 55, 420 of the 2,025 ordered legal row pairs survive the no-touch rule between
rows, and the surviving-prefix counts within a row are Fibonacci (2, 3, 5, 8, … 144 — the
count of length-*n* rows with no two consecutive stars).

**Addition 6 — no static tie of the floating net produces a clean `TWO NOT TOUCH`.**
Ebert's observation, reproduced exactly, including the two trailing bytes:

```text
Vargas    tie=0 '.TWO"NOT TOUCH'
          tie=1 '.TWO NOT TOUCJ'
          success@None  byte diffs=[(129, '22', '20'), (138, '48', '4a'), (139, '00', '02'), (140, '00', '10')]
```

Tie low gives the ditto; tie high gives `TOUCJ` followed by `0x02` and `0x10`. The clean
phrase is what the ROM holds, which is how Sunaabh read it, not what any static tie
prints. README item (1) is right that the ROM text is `TWO NOT TOUCH`; it is worth being
explicit that this is a ROM reading rather than a reachable simulation output.

### Two attributions this record owes

`NOTES-FOR-NEXT-TIME.md` already absorbed two lessons from this set without naming either
source. Both are now attributable:

- Line 36, *"A featured writeup's simulator reproduced the trace with every tie-high cell
  wrong"* — that is **Soto Franco** (his §3.2 and §7.2). His constant cells were classified
  apart from the combinational ones and never evaluated, so every tie-high read as zero,
  the adjacency term could never assert, and a solver run returned sixteen accepted inputs.
  The supplied trace exercises no path through a tie cell, so replay passed throughout.
- Line 49, *"someone reverse-engineered the LFSR"* — that is **Taboada**, and as of this
  addendum the mechanism is ours too (Addition 1).

### The 15, in the post's order

**1. Vladislav Shapovalov** — [PDF](https://figurez.s-ul.eu/i6GwNvSU.pdf)
- **Reached**: PDF v1.7, 674,613 bytes, 10 pages, 6,687 words.
- **Method**: own 7.1 kLOC C++20 extractor with no EDA dependencies; each flip-flop's
  next-state function expanded symbolically until written in terms of other flops and the
  primary inputs; five escalating warm-up checks run before `puzzle.gds` was opened at all.
- **Against our record**: **contradiction**. His Table III lists four output strings and
  states "No fifth message is reachable", from enumerating all 2^12 states of the character
  generator "against each of the four end states of the checker". There are five, and
  `TWO NOT TOUCH` is the one he misses — it is on Jane Street's own egg list. His four end
  states are the gap: the state where every count is right and only the no-touch rule is
  broken is not among them.
- **Status**: our record stands, **reproduced**. `featured-writeups-netlist.py` prints
  `TWO"NOT TOUCH` for a counts-correct touching board under the same netlist, and
  `featured-writeups-grids.py` gives 113,758,569 boards that reach it. Independently
  corroborated by Soto Franco's solver enumeration (exactly five) and Gulawani's app.
  His flop census (92, with 84 asynchronously reset), 728 logic cells and 739 signal nets
  all agree with ours; his `total` width does not (Addition 4).

**2. Stephen Ebert** — [PDF](https://drive.google.com/file/d/1lmpogbV_alS9vgaNRp4DcAbzbfTtkt0a/view?usp=drive_link)
- **Reached**: the table URL is a Drive viewer page; the document is at the download
  endpoint — PDF v1.4, 1,425,324 bytes, 13 pages, 3,405 words.
- **Method**: gdstk + Shapely extraction, cross-checked against an independent KLayout
  extraction (same 728 instances, 13 ports, 739 endpoint partitions); three-valued
  zero-delay simulator; then two independent solving paths — backtracking with no Z3, and
  Z3 over the unrolled circuit — plus a circuit-versus-rules equivalence proof over all
  2^121 boards.
- **Against our record**: **addition**, three of them. (a) The floating net reaches `O[1]`
  and `O[4]`; we named `O[1]` alone (Correction 2). (b) No static tie yields a clean
  `TWO NOT TOUCH`; tie high gives `TWO NOT TOUCJ` then `0x02 0x10` (Addition 6). (c) His
  no-Z3 backtracking is the SAT-independent uniqueness check we claimed was ours alone
  (Correction 1). His board matches ours bit for bit.
- **Status**: **reproduced** — all three, by `featured-writeups-netlist.py` (cone and tie
  bytes, quoted above) and `featured-writeups-grids.py` (uniqueness = 1, board identical).
  His 636 combinational cells and 92 flops agree with ours exactly; his "8 track total
  population" does not (Addition 4).

**3. Alejandro Soto Franco** — [PDF](https://www.sotofranco.dev/pdfs/asic-reverse-engineering.pdf)
- **Reached**: PDF v1.7 (zip deflate), 92,583 bytes, 8 pages, 3,075 words.
- **Method**: KLayout connectivity with the device layers deliberately excluded; extraction
  proved isomorphic to the published warm-up netlist by iterated colour refinement to a
  discrete partition; two independent simulators required to agree on every verdict;
  solver run to exhaustion rather than stopping at the first answer.
- **Against our record**: **addition**, and the most useful entry in the set.
  (a) Region sizes 4, 5, 6, 7, 8, 8, 9, 11, 14, 21, 28. (b) The floating net's cone reaches
  `O[1]` and `O[4]` (Correction 2). (c) He enumerated the readable messages by solver until
  unsatisfiable and got exactly five — the "complete message map, proven" we claimed was
  ours alone (Correction 1). (d) He solved the four recovered rules directly for a second,
  SAT-independent uniqueness result (Correction 1). (e) He ran both simulators over all 16
  power-up states of the four unresettable flops and got identical verdict and reply in
  every one. (f) His §7.2 is the source of `NOTES-FOR-NEXT-TIME.md` line 36.
- **Status**: **reproduced** for (a)–(d). `featured-writeups-grids.py`:
  `ours: [4, 5, 6, 7, 8, 8, 9, 11, 14, 21, 28]  Soto Franco: [...] -> match: True`, and
  uniqueness = 1. Cone reproduced as above. (e) is **unverified** here — it needs 16 Icarus
  runs this pass did not do, and it supports rather than challenges the 2026-10-02
  correction that re-attributed those `x` cycles from the unresettable flops to the
  floating net, so nothing in our record turns on it. His 725-net count differs from
  Ebert's and Shapovalov's 739 by convention, not substance. His board matches ours.

**4. Sanjay Ravishankar** — [HackMD](https://hackmd.io/@sanrav2016/fh9_eHBIQ_upRtm6F9S4wA)
- **Reached**: HTML, 75,759 bytes, 2,884 words of static text.
- **Method**: Magic `ext2spice` to SPICE, then to Verilog; Yosys to simplify 9,876 cells to
  696; DEF coordinates merged into a GraphViz view so the netlist graph could be drawn in
  die position; floorplan islands excised into 11 submodules and analysed one at a time.
- **Against our record**: **addition**, two. (a) "the Jane Street logo inscribed into both
  the warmup and puzzle layouts" — we had only ever checked the puzzle (Addition 2).
  (b) 113,758,569 boards satisfy two-per-row/column/region with some stars touching
  (Addition 3).
- **Status**: **reproduced**, both. `featured-writeups-warmup-logo.py` shows the warm-up
  glyph is bit-identical to the puzzle's (1,366 tiles, symmetric difference 0);
  `featured-writeups-grids.py` gives 113,758,570 total, his figure plus the one clean board.

**5. Aaron Shi** — [site](https://pakkachan.github.io/asic/)
- **Reached**: HTML, 28,889 bytes, 3,861 words.
- **Method**: impulse response — hold every input at zero, set a single 1, clock, and diff
  every flop against the all-zeros baseline; then push `success = 1` backwards through 47
  gates to a required state over 56 flops and check the two derivations against each other
  (56 of 56 agreeing, 0 disagreements).
- **Against our record**: **nothing new**. His Bank D region map is our
  `region-map-render.py` `REGIONS` under a letter relabelling (ours H↔his A, C↔B, K↔C,
  F↔D, A↔E, I↔F, G↔G, E↔H, B↔I, D↔J, J↔K), and his solution grid is ours bit for bit. His
  "there is not a single adder anywhere in the design" agrees with the reasoning in
  `NOTES-FOR-NEXT-TIME.md`'s Crypto-1 comparison.
- **Status**: **reproduced** as agreement — `featured-writeups-grids.py` prints
  `Shi 121 bits identical to ours`.

**6. Lokesh Aravapalli** — [site](https://avnlk.github.io/reverse-engineering-an-ASIC.html)
- **Reached**: HTML, 151,724 bytes, 9,146 words.
- **Method**: gdstk + Shapely union-find extraction (lost substantial time to gdstk
  returning rotations in radians where GDSII stores degrees); Z3 on the unrolled netlist;
  then regions recovered twice — once by fixing a reference cell and pairing it with every
  other, once by symbolic dependency tracing — with both agreeing cell for cell.
- **Against our record**: **addition**. The total-star counter is five bits, not eight
  (Addition 4). Two further claims are interpretive rather than factual: that
  `INTERNAL_3`/`INTERNAL_7` are named for Morse timing ratios, and that the string `EGG'`
  in `layout.png` is an egg.
- **Status**: counter width **reproduced** (quoted above). The Morse geometry is
  **already recorded** — `evidence/easter-eggs.md` lines 165–179 already have the 36
  `INTERNAL_3`/`INTERNAL_7` placements, the 1.38/4.14 µm 1:3 widths and the 1/3/7-unit
  gaps — so only his *naming* reading is new, and it is **unverified**: the ratios 3 and 7
  are indeed the Morse dash and word-gap units, but the 1.38 µm **dot** cell is the one
  named `INTERNAL_3`, so the names do not encode their own widths and the mapping is a
  guess. `EGG'` is **unverified and almost certainly coincidental**, which is his own
  conclusion: it sits at offset 21,028 inside the PNG's compressed IDAT bytes, it
  disappears when that section is decompressed, and the file holds 202 other runs of four
  or more ASCII letters — so one three-letter run carries no information.

**7. Gabriel Taboada** — [site](https://gabbytab.github.io/blog/asic-puzzle-2026/)
- **Reached**: HTML, 22,077 bytes, 2,818 words.
- **Method**: KLayout `LayoutToNetlist` plus custom pin-attach; MST clustering by physical
  locality with the hatched output generator seeded as its own cluster; small clusters
  brute-forced, then SAT over all 695 cells; afterwards the printer cut out and driven with
  the exact bus the rest of the chip feeds it, and its Boolean pieces checked with BooFun.
- **Against our record**: **addition**, and the biggest in the set — the whole output-
  generator stream cipher: an 8-bit LFSR, 4-tap feedback plus the incoming `I` bit,
  characteristic polynomial `0x1d`, a 15-byte stored ROM row, and the keystream that
  decrypts it (Addition 1). `NOTES-FOR-NEXT-TIME.md` line 49 has the existence of the LFSR
  from him, unattributed, and none of the mechanism.
- **Status**: **reproduced**, completely — the eight flops, the shift chain, the four taps,
  the polynomial, all 15 keystream bytes and all 15 stored bytes, by
  `featured-writeups-netlist.py` (quoted above). His 147-cell region lookup also matches
  van Driel's independent count. His `g9`/`g6`/`g7` decomposition is consistent with ours.

**8. Joshua Stapleton** — [site](https://js-chip-solution.vercel.app/)
- **Reached**: HTML, 147,207 bytes, 3,425 words of static text. Worth correcting the
  expectation set at curation: this is a substantive technical note, not merely a
  side-by-side viewer with identifiers — the interactive panes sit inside real prose.
- **Method**: gdstk + Shapely; one-hot intervention to cluster response signatures into
  regions; the 79-of-92 flop slice that can influence `success` normalised with Yosys and
  translated into Z3 (490 ANDs, 341 ORs, 181 NOTs), then blocked and re-solved to UNSAT.
- **Against our record**: **nothing new**. His 79-of-92 success cone agrees with Ebert's;
  his board, extracted from the star grid rendered in the page, is ours bit for bit.
- **Status**: **reproduced** as agreement — `Stapleton 121 bits identical to ours`.

**9. José Vargas** — [site](https://jlvargasme.github.io/posts/reverse-engineering-an-asic.html)
- **Reached**: HTML, 133,116 bytes, 5,980 words.
- **Method**: genuinely transistor-level — poly ∩ diff to locate gates, nwell overlap to
  classify PMOS/NMOS, diffusion partitioned into source/drain nodes, then each cell
  simulated with both PySpice and Z3 rather than pattern-matched to a named gate. The one
  writeup in the set that does not lean on the surviving cell names.
- **Against our record**: **contradiction**. He reports "16 valid inputs in total" from
  blocking and re-solving in Z3, and publishes a different winning board; he also reports
  `BBIG BANG` and `EEMPTY SKY` (nine characters, first letter doubled) and never recovered
  the regions.
- **Status**: our record stands, **reproduced**, and the cause is diagnosable. His
  published board satisfies every count — rows, columns *and* regions — but has five
  touching pairs, so it is a `TWO NOT TOUCH` board, not an accepted one:

  ```text
    Vargas       121 bits  DIFFERENT
      22 stars; rows=True cols=True regions=True; touching pairs=5
      touching: [((1, 7), (2, 7)), ((4, 2), (5, 2)), ((4, 6), (5, 6)), ((7, 8), (8, 8)), ((9, 3), (10, 3))]
  ```

  Driven through our netlist it prints `TWO"NOT TOUCH` and `success` never asserts
  (`success@None`, quoted in Addition 6). That is exactly the signature Soto Franco
  diagnosed in his own earlier run: with tie-high cells mis-evaluated the adjacency term
  can never assert, and the accepted set inflates to sixteen — fifteen of them carrying
  touching stars. Vargas appears to have shipped the artifact Soto Franco caught, which
  makes `NOTES-FOR-NEXT-TIME.md` line 36 a lesson with two featured witnesses rather than
  one. His doubled first letters point the same way, at an output decode off by a cycle.

**10. Amruth Gulawani** — [app](https://notcleo.github.io/GDS-to-RTL/TwoNotTouch-Interactive-Puzzle/)
- **Reached**: HTML, 14,039 bytes, but only 235 words of static text — the content is the
  app's behaviour, not prose. Reachable, not prose-checkable; the claims below are from
  its visible copy.
- **Method**: the recovered puzzle rebuilt as a playable 11×11 two-star Star Battle, with
  the chip's own output line reproduced for whatever grid is placed.
- **Against our record**: **nothing new**, but a useful corroboration: the page states it
  reproduces all five messages "including `TWO NOT TOUCH`, which only appears when every
  count is right and the only rule broken is the no-touch one", and that exactly one grid
  out of 2^121 is accepted, "proved unique at the gate level".
- **Status**: **already recorded** — that is the 2026-08-11 addendum's message map and the
  stage-7 uniqueness result. It also independently contradicts Shapovalov's "no fifth
  message", and its `TWO NOT TOUCH` precondition is Addition 3's 113,758,569 boards.

**11. Kjartan van Driel** — [site](https://kjartanvandriel.github.io/asic/)
- **Reached**: HTML, 55,376 bytes, 5,740 words.
- **Method**: li1/metal tracing from pin labels and an own cycle simulator; regions ordered
  by "trophic level" to decide which to attack first, then read one at a time.
- **Against our record**: **nothing new** — and this is the one entry of the 15 that was
  already in our record before this pass. It is the same URL as README §"Found
  independently" line 219 (Kjartan van Driel & Leander Post), and it fed the 2026-09-08
  reconciliation. Listed here for completeness only. His "eleven patches … from four cells
  to twenty-eight, with rather odd outlines" is already quoted there, and his 147-gate
  patch map matches Taboada's independent count.
- **Status**: **already recorded** — README line 219 and the 2026-09-08 addendum above. The
  genuinely unchecked set this pass covered was therefore 14, not 15.

**12. Alexander Smallwood** — [PDF](https://raw.githubusercontent.com/alexseekingalpha/jsasicsolved/main/myjanestreetwriteup.pdf)
- **Reached**: PDF v1.7, 1,290,702 bytes, 14 pages, 4,089 words.
- **Method**: KLayout Python macros, built up one question at a time from pin geometry to a
  full netlist; then Z3; then the recovered gate graph transplanted onto a Basys 3 FPGA
  (Artix-7), where the 121 bits were sent over USB-UART and the 15 output bytes read off
  the LEDs by hand.
- **Against our record**: **addition**. His row combinatorics — 45 legal rows, 420 legal
  ordered row pairs, Fibonacci surviving-prefix counts (Addition 5). Independently, his
  eight output-stage registers reset to `00001111` (bits 0–3 SET, 4–7 RESET), which is a
  second, independent sighting of Taboada's LFSR seed.
- **Status**: **reproduced**. `featured-writeups-grids.py`: 45 of 55, `ordered legal row
  pairs: 420 of 2025 -> match: True`, and `[2, 3, 5, 8, 13, 21, 34, 55, 89, 144]`. The
  seed corroboration is **reproduced** too — `featured-writeups-netlist.py` shows the
  LFSR's four `dfstp_2` reset high and four `dfrtp_2` reset low. His board matches ours.
  He is admirably explicit that his `dfxtp` zero-initial-state assumption is shared by his
  solver and his verifier, so their agreement does not independently establish it — Soto
  Franco's 16-power-up-state sweep is the check that would.

**13. Nikhil Kaniyeri** — [Drive](https://drive.google.com/file/d/1ZmbmW6kK7hxcqemHxb7zkxzubLMro7pP/view?usp=sharing)
- **Reached**: reachable, but **not text-checkable**. The table URL serves a Drive viewer
  page; the download endpoint returns `video/mp4`, 33,729,270 bytes, which `file` reports
  as `ISO Media, MP4 Base Media v1`. There is no text to extract.
- **Method**: as the results post describes it — the extracted netlist compiled into
  Minecraft command blocks.
- **Against our record**: **unknown**. Nothing is claimed here either way.
- **Status**: **unverified**, and listed as such rather than folded in. Watching or
  transcribing the video was explicitly out of scope for this pass. A method difference of
  this kind asserts nothing about our record, so the gap is recorded, not a loose end that
  changes any conclusion above.

**14. David Garner** — [PDF](https://github.com/davidg351/Jane-Street-Puzzle-August-2026/blob/main/JaneStreetPuzzleWriteup_DavidGarner_FINAL.pdf)
- **Reached**: the table URL is a GitHub blob page (166,991 bytes of UI); the document is
  on `raw.githubusercontent.com` — PDF v1.7, 3,436,836 bytes, 22 pages, 5,187 words.
- **Method**: entirely Cadence — Virtuoso stream-in, PVS LVS in extraction-only mode to a
  SPICE/CDL netlist, a Perl converter to Verilog, Xcelium for digital simulation, and then
  a full-transistor Spectre analog simulation of the whole chip as a cross-check.
- **Against our record**: **addition** and **contradiction**. (a) His Perl generator
  produced 31,197,434 regionless two-star boards — our number, independently — and he
  simulated all of them, which retires our "no other writeup contains" claim
  (Correction 1). (b) The logo is in the warm-up layout, upper-right (Addition 2).
  (c) His analog run found large glitches on `O[7:0]` between successive bits, harmless if
  the bus is sampled on falling clock edges — something no simulation in this record could
  have seen. (d) He reports 5,296,794 regionless one-star boards; the true count is
  5,296,790.
- **Status**: (a), (b) **reproduced** — `31,197,434 -> match: True`, and the warm-up glyph
  identity above. (d) **reproduced as a correction to him**: a one-star board is a
  permutation `s` with `|s(i+1) - s(i)| >= 2`, i.e. Hertzsprung's problem, OEIS A002464;
  `featured-writeups-grids.py` computes 5,296,790, validates the method against brute force
  for n ≤ 8 and against the published values to n = 11, and shows his figure is high by 4.
  His conclusion is untouched — no one-star board is accepted on either count. (c) is
  **unverified** and will stay so: it needs a transistor-level analog simulation of the
  whole chip, which this record has no path to and which `~/.claude/CLAUDE.md`'s host rules
  would route to the batch fleet rather than run here. Recorded as a real finding of his,
  not adopted as ours. His input vector matches ours.

**15. Marcin Wójcik** — [site](https://synhex.com/notes/jane-street-puzzle-solution.html)
- **Reached**: HTML, 27,213 bytes, 2,462 words.
- **Method**: a Rust GDS-to-netlist pipeline built with coding agents against the warm-up
  as oracle; Yosys BMC (one run, about seven seconds); then a Groth16 proof over BN254,
  via a Rust checker inside the SP1 RISC-V zkVM, that he possesses a winning trace without
  revealing it — 36 public bytes, being the model hash and `PASS = 1`.
- **Against our record**: **contradiction**, though he half-retracts it himself. He writes
  that "in the layout, all 84 resettable dfrtp cells were disconnected from the top-level
  `rst_n` net", and that he reconnected them. That is a property of his extractor, not of
  the layout.
- **Status**: our record stands, **reproduced**:

  ```text
  async nets: {'rst_n': 88, None: 4}
  resettable flops: 88; of those on rst_n: 88
  Wojcik's 'all 84 dfrtp disconnected from rst_n': NOT reproduced
  ```

  All 88 flops with an asynchronous pin — 84 `dfrtp_2` reset pins and 4 `dfstp_2` set pins
  — reach `rst_n` in `evidence/puzzle-extracted.v`; only the 4 `dfxtp_2` have no async pin,
  which is the real and separate fact. His own account of why BMC first returned garbage
  (26 undriven input pins left free for the solver to choose) is a genuinely useful warning
  and is consistent with Vargas's and Soto Franco's experience. His remaining driverless
  pin, `u_a311o_2_3326.A1`, is our `net_00575`'s load on `a311o_2_177370_89520.A1`; his
  finding that tying it 0, 1 or free does not change the winning behaviour agrees with the
  cone result above — it cannot reach `success`. He is also candid that his proof binds a
  witness to the model's hash without establishing that the model came from the public GDS,
  which is the honest limitation.

### Scorecard for this pass

14 of the 15 were genuinely unchecked (van Driel was already in the record). 13 of those 14
were read as text; Kaniyeri is a video and Gulawani is an app whose 235 words of copy were
all that could be read. Two corrections to our record, six additions, four contradictions
in which our record held, and two attributions paid. The single largest gain is Taboada's
stream cipher, which turns `NOTES-FOR-NEXT-TIME.md` line 49 from a borrowed sentence into
30 reproduced bytes. The most useful correction is the least flattering one: all three
things README claimed no other writeup contained were in this set, two of them in more
than one writeup.
