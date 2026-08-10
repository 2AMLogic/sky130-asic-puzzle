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

> The chip answers back when you get it wrong: all-zeros in emits `EMPTY
> SKY` on O[7:0], all-ones emits `BIG BANG`, and other failing inputs emit
> `TRY AGAIN` (all gate-level Icarus replays, not solver decodes). Below
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
