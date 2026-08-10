# Independent review — addendum claims 6–9 and the three closures

Adversarial review of the claims added by the 2026-08-10 addendum to
`REVIEW-REQUEST.md`. Reviewed as though wrong; every check below was run with
methods and, where practical, tools different from the committed scripts. No
existing evidence file was edited. The committed easter-egg scripts were read
but **not** re-run as evidence — everything below is a fresh derivation.

Four new scripts carry the re-derivations (committed alongside this file):

| Script | Claim | Independent of the committed path how |
|---|---|---|
| `independent-review-addendum-messages.py` | 6 | Own Verilog testbench text, own iverilog/vvp invocation, own O[7:0] decoder; no `tools/` import; 172 input words across 8 families vs. the committed 7 |
| `independent-review-addendum-morse.py` | 7 | gdstk 0.9.62 (not KLayout), integer-nm snapping, threshold from the width histogram, own Morse table |
| `independent-review-addendum-met2.py` | 8 | gdstk; no fixed window — same-layer flood fill across the whole die, via1/via2 overlap test, whole-die tile-cluster census, radial bands derived from data |
| `independent-review-addendum-regions.py` | 9 | Own netlist parser (pin directions parsed from the PDK Verilog, not `tools/` JSON), own Tarjan SCC, **gate-level Icarus** one-hot traces (committed script used the Python cycle model), two-hot boundary checks, naive CNF + Glucose 4.2 (not seqcounter + CaDiCaL), full enumeration, and an exact DP recount of 31,197,434 |

Environment, for re-running: Python 3.14.6 (`.sim-work/review-venv`, python-sat
1.9.dev12) and system `python3` with gdstk 0.9.62; Icarus Verilog 13.0;
sky130 models from `~/.volare/sky130A` (open_pdks
`c6d73a35f524070e85faff4a6a9eef49553ebc2b`), resolved to
`libs.ref/sky130_fd_sc_hd/verilog/{primitives.v,sky130_fd_sc_hd.v}`.

Inputs under test, pinned by hash (`shasum -a 256`):

```text
8913ea4be5367b484d5886c3c5f7608942b67544a0dbe364b17223503b8d851a  puzzle/puzzle.gds
bcd26d7c199967452d466fe3e24b5e201ae19d9c97283096399d961d027dce37  puzzle/example_inputs.vcd
cd9599ddcafda0bf986777676f7797110c0b20702b62e3ecbb022847af35de77  .sim-work/independent-review/puzzle-extracted.v
```

Mid-review, commits `658a6d4` and `812b797` landed re-derivations of claims 7
and 8 from the contributing side (stdlib GDSII parser; KLayout Region
connectivity; whole-die tile survey). The scripts below were written and run
without reading those, and agree with them — claims 7 and 8 now have three
mutually independent readers each.

---

## Claim 6 — failure messages (`EMPTY SKY` / `BIG BANG` / `TRY AGAIN`)

**Verdict: CONFIRMED, with the universality of `TRY AGAIN` qualified as
sampled, not proven.**

```sh
.sim-work/review-venv/bin/python evidence/independent-review-addendum-messages.py
```

The script compiles one self-written testbench (cycle protocol: 3 reset
cycles, 1 idle, 121 active on `I`, sampled 1 ns before each rising edge — the
device protocol, not the committed code) against
`.sim-work/independent-review/puzzle-extracted.v` plus the PDK models, then
replays 172 words by swapping a `$readmemb` file: the accepted word, the 7
committed structured failures, 5 population probes, 20 seeded random words at
three densities, **all 121 single-bit flips of the accepted word**, 10 star
moves, and 8 SAT-generated near-misses that satisfy every *published* rule
(2/row, 2/col, no touching) and differ only in the withheld region rule.
O[7:0] is decoded by this script's own decoder, scanning **all 190 cycles**
in both bit orders for printable runs. Literal output:

```text
words to replay: 172

== per-family longest-printable tally ==
accepted: '(* TWO STARS *)':1
all-one: 'BIG BANG':1
all-zero: 'EMPTY SKY':1
alt: 'TRY AGAIN':2
complement: 'TRY AGAIN':1
flip: 'TRY AGAIN':121
near-valid: 'TRY AGAIN':8
one-first: 'TRY AGAIN':1
one-last: 'TRY AGAIN':1
pop: 'TRY AGAIN':3
pop-120-zero-first: 'TRY AGAIN':1
pop-120-zero-last: 'TRY AGAIN':1
rand-dense: 'TRY AGAIN':5
rand-half: 'TRY AGAIN':10
rand-sparse: 'TRY AGAIN':5
star-move: 'TRY AGAIN':10

== overall (message, start-cycle) tally ==
'(* TWO STARS *)' @ cycle 126: 1
'BIG BANG' @ cycle 126: 1
'EMPTY SKY' @ cycle 126: 1
'TRY AGAIN' @ cycle 126: 169

anomalies: 0
```

What this establishes:

- **`EMPTY SKY` and `BIG BANG` confirmed**, from a decoder and testbench that
  share no code with the committed path. Both are point messages: 120 ones
  with a single zero (either end) already falls back to `TRY AGAIN`, as does
  a single one — so the specials are exactly the all-zeros and all-ones
  words among everything tested, not density classes.
- **`TRY AGAIN` is not just one failure class**: near-misses one bit from the
  answer, words valid under every published rule but the region rule, random
  words at three densities, and structured patterns all emit it — 169 of 169
  failing words that are not the two specials.
- **No additional messages found**: no other printable run of length ≥ 3
  anywhere in any 190-cycle window, in either bit order, on any of the 172
  runs; `success` asserted on the accepted word only (cycles 126–189), and on
  no failing word.
- These replays are Icarus gate-level runs, fully independent of the SAT
  model — answering the addendum's independence question directly.

Qualification: 172 samples cannot prove `TRY AGAIN` is universal over all
2^121 − 3 remaining failing words. What would prove it: a BMC query asserting
the O byte at each message cycle differs from all four known messages, run to
UNSAT. Not run here; the sampled evidence (plus lead 2's unseen-byte BMC,
which surfaced only `BIG BANG`) is consistent with exactly three failure
messages.

## Claim 7 — layer 200/0 Morse strip reads `PER ARENAM AD ASTRA`

**Verdict: CONFIRMED.**

```sh
python3 evidence/independent-review-addendum-morse.py
```

gdstk (no KLayout anywhere in the path) flattens the layout and snaps to the
1 nm database grid, so every measurement below is exact integer arithmetic.
Literal output, abridged only by cutting the middle of the 36-row table
(re-run the script for the full table):

```text
gdstk 0.9.62; unit=1e-06 precision=1e-09
top cells: ['puzzle']
layer 200/0 polygons (flattened): 36
strip bbox um: (1.33,-52.72) - (198.67,-50.00)
distinct heights nm: [2720]
distinct widths nm: [1380, 4140]
dash/dot width ratio: 3.0000

idx  left_nm  width_nm  gap_before_nm  symbol  gap_units
  0      1330      1380              0    .     0
  1      4090      4140           1380    -     1
  2      9610      4140           1380    -     1
  3     15130      1380           1380    .     1
  4     20650      1380           4140    .     3
  ...
 34    191770      1380           4140    .     3
 35    194530      4140           1380    -     1

morse letters: .--. . .-. / .- .-. . -. .- -- / .- -.. / .- ... - .-. .-
DECODED: PER ARENAM AD ASTRA
```

- Exactly 36 axis-aligned rectangles, two widths (1380/4140 nm, ratio exactly
  3), every gap exactly 1, 3, or 7 dot-widths with zero residue on the nm
  grid. The dot/dash threshold was taken from the measured width histogram,
  not an assumed unit, so a wrong-`unit` garble is excluded.
- The spacing convention the decode relies on — dash = 3 dots; gaps of 1
  (intra-letter), 3 (inter-letter), 7 (inter-word) — is the International
  Morse standard (ITU-R M.1677-1 §2), which answers the residual
  Morse-convention check left open in the updated claim 7 row.
- Cell provenance re-checked with gdstk: exactly two cells own 200/0
  geometry, one rectangle each — `INTERNAL_3` (21 placements = the 21 dots)
  and `INTERNAL_7` (15 placements = the 15 dashes) — matching the committed
  "the bookkeeping cells were the easter egg" claim.

## Claim 8 — met2 three-ring glyph, connected to nothing

**Verdict: CONFIRMED, and strengthened from "apparently isolated" to
"proven unconnected" at the geometry level.**

```sh
python3 evidence/independent-review-addendum-met2.py
```

Literal output:

```text
met2 polygons: 8517; via1: 6869; via2: 3423
seed tiles inside committed window: 1366
glyph connected component: 1366 shapes (0 non-0.3um-tile), exact fallbacks used: 0
component extent um: (34.90,35.20) - (52.00,52.30)
component escapes committed window: False
via1 (met1<->met2) overlapping component: 0 (edge-touch: 0)
via2 (met2<->met3) overlapping component: 0 (edge-touch: 0)

0.3um met2 tiles on the whole die: 1366
tile clusters with >=10 tiles: 3
  cluster n=596 bbox um (34.90,35.20)-(52.00,52.30) touches_routing=False overlaps_via=False
  cluster n=470 bbox um (36.70,37.00)-(50.20,50.50) touches_routing=False overlaps_via=False
  cluster n=300 bbox um (38.80,39.10)-(48.10,48.40) touches_routing=False overlaps_via=False

glyph center um: (43.39,43.71); radius range 3.59..8.72
radial bands (from data): 3
  band r=3.6-4.9um: 300 tiles, covered 335.0deg, gaps: 25.0deg@309.5deg
  band r=5.5-6.9um: 470 tiles, covered 344.5deg, gaps: 15.5deg@194.0deg
  band r=7.5-8.8um: 596 tiles, covered 346.0deg, gaps: 14.0deg@46.5deg
```

- **The window caveat is closed**: flood-filling same-layer met2 connectivity
  from the committed window's tiles across the entire die adds nothing — the
  component never escapes the window, and a whole-die census finds **all
  1,366** exact-0.30 µm met2 tiles belong to these rings; there is no fourth
  ring, tail, or second glyph anywhere.
- **"Connected to nothing" is now electrical, not visual**: met2 can only
  connect downward through via1 and upward through via2. Zero via1 and zero
  via2 shapes overlap (or even edge-touch) any glyph tile, and no glyph tile
  touches any non-tile met2 shape. Within sky130 layer semantics that is
  proof of an unconnected island. (The concurrent `easter-egg-ring-connectivity.py`
  reached the same zeros via KLayout Region interactions.)
- **Three rings confirmed with no prior**: radial bands derived from the
  measured radius histogram — not hardcoded — come out as exactly three
  (3.6–4.9, 5.5–6.9, 7.5–8.8 µm), each with a single gap, gaps rotating
  46.5° → 194.0° → 309.5°. One nuance the committed record understates: the
  three rings are three *separate* met2 islands — they do not even touch each
  other. "A compact cluster … forming three concentric broken rings" remains
  a fair description.

## Claim 9 — the withheld rule is the Star Battle region map; regions make the answer unique

**Verdict: CONFIRMED at every layer, including the boundary cells and the
31,197,434 count.**

```sh
.sim-work/review-venv/bin/python evidence/independent-review-addendum-regions.py
```

Literal output (the recovered map uses this script's own labels; letters are
arbitrary):

```text
PDK modules with parsed output pins: 416
netlist instances parsed: 1618
flops: 92; cells with outputs: 728; undriven internal nets read by logic: ['net_00575']
flop-graph SCCs: sizes [9, 8, 4, 2, 2, 2, 2, 2]... two-flop SCCs: 23
one-hot membership histogram: 2:11 3:110
groups: columns=11 region-like=11 large(row-reuse)=1
  large group 22: 110 cells; missing positions ['r0c10', 'r1c10', 'r2c10', 'r3c10', 'r4c10', 'r5c10', 'r6c10', 'r7c10', 'r8c10', 'r9c10', 'r10c10']
recovered region map (independent labels a..k):
  fffffddkbbg
  ffiffdkkbbg
  ffiddddkkbg
  ffideeegkkg
  ifidegggggg
  iiideeegaaa
  ddddddegahh
  dccceeegahh
  dccjggggahh
  ddcjjgggaaa
  dccjggggggg
partition identical to committed map: True
two-hot boundary pairs checked: 98; mismatches: 0
boundary cells (8-neighbourhood): 115 of 121

naive CNF clauses: 9813; glucose42 enumeration found 1 solution(s)
  solution 0: 0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000
unique and equal to accepted word: True

DP count, published rules only (2/row, 2/col, no touching): 31197434
```

Each attack surface named in the addendum, answered:

- **Different perturbation scheme / different trace engine.** Membership was
  re-derived from one-hot differential traces run **gate-level in Icarus**
  against the extracted netlist (the committed script used the Python cycle
  model), on top of an independently written netlist parser and Tarjan SCC.
  The 23 two-flop feedback pairs, the 11 column groups, the 110-cell reused
  row group (missing exactly column 10), and the 11-region partition all
  reproduce. The partition is **identical** to the committed map under label
  renaming.
- **Every boundary cell checked.** 115 of 121 cells are boundary cells
  (8-neighbourhood). Beyond each cell's own one-hot trace, every 4-adjacent
  pair straddling a region boundary (98 pairs — every boundary edge, hence
  every boundary cell) was re-run as a **two-hot** trace: in all 98 cases the
  changed counter set equals the union of the two one-hot sets. No
  perturbation-scheme ambiguity at any boundary.
- **CNF encodes only recovered rules, enumerated to exhaustion.** This
  script's own encoding (naive triples / (n−1)-subsets — no library
  cardinality encoder, no auxiliary-variable scheme shared with the committed
  script) under Glucose 4.2 (not CaDiCaL), enumerated with blocking clauses
  until UNSAT: exactly **one** solution, equal to the accepted word — which
  this review's claim-6 testbench independently confirmed asserts `success`
  gate-level.
- **The 31,197,434 candidate count re-derived without SAT**: exact dynamic
  programming over row masks and column counts gives 31,197,434 grids under
  the published rules alone. The regions cut that to 1.

One caveat on wording, not correctness: the region *map* is recovered from
the circuit, so "with no reference to the circuit" is true of the final CNF
check only. `SUBMISSION.md`'s phrasing ("we encoded only the recovered rules
… as a fresh CNF with no reference to the gate-level circuit") is scoped
correctly.

## Closure claims

### UNIT_DELAY timing explanation — **CONFIRMED against model source**

Audited `~/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v`
(the file the replays compile) directly:

- Every `timescale` in both model files is `1ns / 1ps`, so `#1` = 1000 ps.
- `UNIT_DELAY` occurs 116 times; **all** attach to sequential UDP instances —
  90 `sky130_fd_sc_hd__udp_dff$…`, 26 `…udp_dlatch$…` (census:
  `grep UNIT_DELAY sky130_fd_sc_hd.v | awk '{print $1}' | sed -E 's/\$.*//' | sort | uniq -c`).
  The netlist's dfrtp/dfxtp/dfstp functional models all instantiate
  `` …udp_dff$PR… `UNIT_DELAY dff0 (…) ``.
- The FUNCTIONAL combinational models are bare zero-delay gate primitives —
  e.g. `sky130_fd_sc_hd__and3_2`: `and and0 (…); buf buf0 (X, and0_out_X);`
  with no delay expression anywhere.

So every registered output moves exactly one 1 ns quantum after its clock
edge and combinational depth adds nothing — which is precisely why `success`
(bare Q) and `O[0]`/`O[7]` (Q through gates) show the *same* +1000 ps offset.
The closure explanation is correct, and the original "should differ with
depth" concern was wrong to expect scaling under this model set.

### net_00575 — **robustness for `success` is structural; for O[1]/O[4] it is tested, not global**

This review's own parser independently found `net_00575` as the **only**
undriven internal net read by logic (matching the committed record), and
re-derived its forward cone:

```text
combinational forward cone: cells = 10
output ports reached: ['\O[1]', '\O[4]']
flop D inputs reached: []
```

The cone reaches **no flip-flop D input**. That makes one half of the
robustness claim *structural, for all inputs*: `net_00575` cannot influence
any state bit, therefore cannot influence `success`, ever. The remaining
exposure is purely combinational perturbation of `O[1]`/`O[4]`; for those,
the committed evidence (both polarities forced across four trace families,
no sampled output changed) is tested robustness, not global irrelevance —
the lead 5 wording ("does not prove global irrelevance for every possible
input") states this honestly. Verdict: the record is accurate; this review
strengthens it by showing the `success`-side is not merely tested but
structurally closed.

### SUBMISSION.md strengthened statements — one overstatement found

Checked each strengthened statement against what the evidence proves:

| Statement (SUBMISSION.md) | Finding |
|---|---|
| "all-zero input emits `EMPTY SKY`, all-one emits `BIG BANG`, and ordinary invalid inputs emit `TRY AGAIN`" | Supported by 169/169 tested failing words (this review); "ordinary" reads as a fair hedge, but see suggested wording below |
| "layer 200/0 encodes `PER ARENAM AD ASTRA` … built from the 36 `INTERNAL_*` placements" | Confirmed (gdstk, ITU convention, cell provenance re-checked) |
| "met2 carries an ~18 µm three-ring maze/record glyph connected to nothing" | Confirmed and now proven electrically (zero via1/via2 landings, zero met2 abutments, whole-die survey) |
| "recovers the 11 irregular Star Battle regions … makes the accepted grid independently unique" | Confirmed (identical partition, 98/98 two-hot boundary checks, 1 solution by independent CNF, DP count 31,197,434 → 1) |
| "The traces differ **only in timing, by a constant offset of exactly one UNIT_DELAY quantum**" | **Overstated.** `evidence/puzzle-replay.md` records deltas `[-4000, 1000]`: the first `x`-to-defined settle lands 4 ns *early* (pre-`rst_n`, functionally inert), and only the transitions after it are the constant +1 ns. Two sentences later the draft itself says the run is a literal FAIL "characterised separately" — the "only … constant" sentence contradicts the record it cites |

Suggested wording changes (SUBMISSION.md is a draft, not append-only
evidence; alternatively apply at transcription):

1. Timing sentence → "The traces differ only in timing: apart from one
   functionally inert pre-reset x-settling transition (4 ns early), every
   transition is offset by exactly one `UNIT_DELAY` quantum (+1 ns, the
   sky130 primitive timescale)."
2. "ordinary invalid inputs emit `TRY AGAIN`" → "every other failing input we
   tested emits `TRY AGAIN` (169 words across eight families, including
   near-misses one bit from the answer)". Same change in the Easter-egg
   field draft ("other failing inputs emit `TRY AGAIN`").
3. The Easter-egg field draft in `evidence/easter-eggs.md` contains a typo to
   fix at transcription: "all-zeros **in emits** `EMPTY SKY`" → "all-zeros
   input emits".

## Limitations — what could still escape this review

- **Extraction fidelity is inherited, not re-proven.** Claims 6 and 9 test
  the *extracted netlist*; if extraction dropped cold logic (the risk
  quantified in `evidence/independent-review.md`), a hidden message or a
  differently shaped region rule in dropped logic would escape both this
  review and the originals. Claim 1's standing caveat ("corroborated, not
  proven") covers this and is already stated in the submission.
- **`TRY AGAIN` universality is sampled** (169 failing words). A per-cycle
  BMC over all failing inputs would close it; not run.
- **Simulator monoculture**: this review and the committed evidence both use
  Icarus (different testbenches, same engine). A common-mode Icarus/PDK-model
  bug would escape. The cycle-model-vs-Icarus agreement on claim 9 traces
  partially mitigates.
- **pysat is shared** between the committed scripts and this review
  (different encodings and different solver backends, but one Python
  binding). The DP count and the two-solver agreement mitigate; a bug would
  have to survive naive-vs-seqcounter, Glucose-vs-CaDiCaL, and DP-vs-SAT
  simultaneously.
- **Geometry semantics assumed, not DRC-verified**: "met2 connects only via
  via1/via2" is sky130 layer semantics; no LVS run was performed. The zeros
  are zeros of overlap on the flattened geometry, snapped to the 1 nm grid.
- The puzzle files were verified against the working copies (hashes above),
  not re-fetched from `janestreet/asic-puzzle-2026` during this review.

## Recommendation

**SEND WITH WORDING CHANGES** — the three wording items above (the
"constant offset" sentence, the `TRY AGAIN` qualifier, the typo). Every
technical claim in the addendum survived independent attack: claims 6, 7, 8,
9 confirmed (6 with a stated sampling qualification), both anomaly closures
confirmed — one strengthened to structural — and no new defect found
anywhere. Nothing else blocks submission.
