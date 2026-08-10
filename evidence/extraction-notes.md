# Extraction notes (issue #2)

What was actually executed, on what input, with what result — per `CLAUDE.md` §5
("claims are evidence-backed... state what was actually executed"). Every command
below was re-run to produce this document; none of it is inferred from reading the
code.

Environment: `python3 --version` -> `Python 3.12.3`; `klayout` Python package
`0.30.10` (already importable in the running interpreter — `klt` itself was also
present, `klt 0.2.0`, but was not needed: `klayout_env.ensure_klayout()`'s fast
path resolved without re-exec'ing). Repo commit at the time of this run:
`2604330` (`main`, pre-#2).

## Tool

`tools/extract <gds> [-o out.v] [--json out.json] [--top NAME] [--stats]` — see
`tools/gds_extract.py` for the algorithm and `tools/README.md`
("Conductor stack and via handling") for the narrative version, including the
two corrections this implementation makes to the naive black-box algorithm the
issue proposed (both found by running the extractor against `04_final.gds` and
chasing down its first false "unconnected pin", not by inspection).

## 1. Warm-up: `puzzle/warmup/04_final.gds` (not embargoed)

```
$ ./tools/extract puzzle/warmup/04_final.gds \
    -o evidence/warmup-extracted.v --json evidence/warmup-netlist.json --stats
```

stderr (the extraction report):

```
extraction: puzzle/warmup/04_final.gds  (top cell 'adder_demo')
  instances (top cell, all classes): 1099
    logic: 63
    sequential: 16
    fill: 151
    via: 869
  emitted signal instances: 79
  emitted fill instances: 151
  flip-flops: 16 {'dfrtp': 16}
  nets: 84  named ports: 6
  via bridging (drawn + VIA_* cell shapes, merged per via layer):
    mcon: bridged=1893 unmatched=0
    via: bridged=763 unmatched=0
    via2: bridged=420 unmatched=0
    via3: bridged=380 unmatched=0
    via4: bridged=13 unmatched=0
  supply pin connections (name-collapsed, not geometrically resolved): VGND=367, VPWR=367
  supply rail islands found by the geometric trace (sanity check only): VGND=1, VPWR=1
```

Cell-type histogram of `evidence/warmup-extracted.v` (fill excluded), compared
directly against the acceptance criterion's list — **identical**, 79 cells:

| Cell | Count |
|---|---|
| `dfrtp_2` | 16 |
| `mux2_1` | 16 |
| `nor2_2` | 8 |
| `and2_2` | 7 |
| `xor2_2` | 5 |
| `or2_2` | 5 |
| `a31o_2` | 5 |
| `nand2_2` | 4 |
| `xnor2_2` | 3 |
| `clkbuf_16` | 3 |
| `and4bb_2` | 2 |
| `o21bai_2` | 1 |
| `and3_2` | 1 |
| `a21o_2` | 1 |
| `a21boi_2` | 1 |
| `a21bo_2` | 1 |

Ports: `A B S clk en rst_n` — matches. Direction inferred (best-effort, see
`tools/README.md`): `A B clk en rst_n` = input, `S` = output — matches
`01_netlist.v`'s own declarations, though `tools/compare` does not check
direction at all (net names are what it matches).

```
$ ./tools/compare evidence/warmup-extracted.v puzzle/warmup/01_netlist.v
EQUIVALENT
  A: evidence/warmup-extracted.v  (module adder_demo)
  B: puzzle/warmup/01_netlist.v  (module adder_demo)

  ports            6 matched by name: A B S clk en rst_n
  signal cells    79 matched 1:1 (A has 79, B has 79)
  nets            84 matched (A has 84, B has 84)
  fill cells     151 matched by count (B has 151) [decap_3: 58, tapvpwrvgnd_1: 93]
  verification  independent re-check of the full mapping passed
```

Also verified: `./scripts/warmup-regression.sh --no-fetch --require-extract`
passes end to end locally (stage 1, the comparator self-test/mutation suite;
stage 2, this same extract-then-compare gate). `--require-extract` is not yet
the default in `.github/workflows/ci.yml` — landing that, plus recording it
here, is issue #9's job (blocked on this issue, now unblocked); nothing in
this repo's CI config was changed to add that flag as part of #2, only to keep
CI *able to run the extractor at all* (see `## CI wiring` below).

`iverilog -E evidence/warmup-extracted.v -o /dev/null` — exits 0, no errors
(Icarus Verilog 12.0).

## 2. Puzzle: `puzzle/puzzle.gds` (embargoed — this section's *output* stays inside
this repo; see `CLAUDE.md` §1)

```
$ ./tools/extract puzzle/puzzle.gds \
    -o evidence/puzzle-extracted.v --json evidence/puzzle-netlist.json --stats
```

stderr (the extraction report):

```
extraction: puzzle/puzzle.gds  (top cell 'puzzle')
  instances (top cell, all classes): 9875
    logic: 646
    sequential: 92
    fill: 880
    via: 8221
    other: 36
    excluded 'other' cell names: INTERNAL_3, INTERNAL_7
  emitted signal instances: 738
  emitted fill instances: 880
  flip-flops: 92 {'dfrtp': 84, 'dfstp': 4, 'dfxtp': 4}
  nets: 739  named ports: 13
  via bridging (drawn + VIA_* cell shapes, merged per via layer):
    mcon: bridged=13682 unmatched=0
    via: bridged=6869 unmatched=0
    via2: bridged=3423 unmatched=0
    via3: bridged=3159 unmatched=0
    via4: bridged=108 unmatched=0
  supply pin connections (name-collapsed, not geometrically resolved): VGND=2560, VPWR=2560
  supply rail islands found by the geometric trace (sanity check only): VGND=1, VPWR=1
```

Wall time: ~8s on the machine this ran on (9,875 top-cell instances,
14,638 polygons per `evidence/inventory-puzzle.json`).

**738 logic+sequential instances** — matches `README.md`'s corrected,
stream-derived figure and `evidence/inventory-puzzle.json`, *not* the
issue body's literal "~781" (explicitly documented there as a stale
pre-correction estimate, superseded once the 36 `INTERNAL_*` instances were
accounted for — re-verified here against the current tree rather than taken
on the issue's word, per this repo's "re-verify date-stamped facts" convention).

**Exactly 92 flip-flops**, split **84 `dfrtp_2` / 4 `dfstp_2` / 4 `dfxtp_2`** —
matches the acceptance criterion exactly.

**Ports**: `I O[0] O[1] O[2] O[3] O[4] O[5] O[6] O[7] clk enable rst_n success`
(13 total) — matches. Inferred direction: `I clk enable rst_n` = input,
`O[0..7] success` = output — matches the expected shape of the design (an
8-bit output bus plus a `success` flag) though, again, direction is
best-effort and not checked by anything downstream.

No `VPWR`/`VGND`/`VPB`/`VNB` connection is emitted on any instance (see
"Supply pins" below) — verified directly: `evidence/puzzle-netlist.json`
contains zero occurrences of those four pin names as connection *keys*
(`tools/test-extract`'s puzzle smoke test asserts this).

There is no published ground truth for `puzzle.gds`, so there is no
`tools/compare` run to report here — structural equivalence-checking against
a synthesized netlist is a later stage (`spec/puzzle.md` stage 6+), not this
issue's job. What this issue's own acceptance criteria ask for (histogram
counts, port names/count, total-or-loud pin resolution, no spurious supply
shorts) is what is reported above and was verified by the run itself, not
inferred.

`iverilog -E evidence/puzzle-extracted.v -o /dev/null` — exits 0, no errors.

## Supply pins (VPWR/VGND/VPB/VNB): design decision and sanity check

`VPWR`/`VPB` pins collapse to a single net name `"VPWR"`; `VGND`/`VNB` collapse
to `"VGND"` — by **pin name**, never by geometry (`gds_extract.SUPPLY_PIN_NET`).
Two independent reasons converge on this:

- `VPB`/`VNB` (n-well / substrate bias) resolve to shapes on the nwell/pwell
  layers (64/122), entirely outside the `li1`-`met5` conductor stack this
  extractor traces — there is no top-level routing model to resolve them
  against geometrically.
- `VPWR`/`VGND` *do* have real top-level routing (met1 rails, met4/met5 mesh),
  but neither `warmup/01_netlist.v` nor this repo's own simulation harness
  (`tools/sim/icarus.py`, compiled without `USE_POWER_PINS`) expects a gate
  instance to name these pins at all. Emitted instances therefore never carry
  these four connections.

This is a deliberate simplification, not a gap in the geometric trace: the
same union-find machinery used for signal nets is *also* run across the full
`li1`-`met5` stack (this is where `via bridging` above comes from) purely to
sanity-check the supply network, independent of the name-based collapse:

- **No spurious supply shorts.** If any physically-connected net were found
  carrying *both* a supply-rail label (`VPWR`/`VGND`, read from met4/met5 text)
  and a non-supply top-level port label, or both `VPWR` and `VGND` labels at
  once, extraction raises `ExtractionError` naming the conflicting labels
  (`gds_extract.extract`, the `root_labels`/`root_name` pass) — this is a hard
  failure, not a warning, and neither run above triggered it.
- **Supply rail islands found**: exactly **1** `VPWR` island and exactly **1**
  `VGND` island in *both* designs — the rails are each one physically
  continuous mesh, as expected, with no unexpected fragmentation.
- **Connection counts vs. fill-cell count**: warm-up reports `VGND=367,
  VPWR=367` name-collapsed connections against **151** fill instances (58
  `decap_3` + 93 `tapvpwrvgnd_1`, each contributing exactly one `VPWR` + one
  `VGND`, i.e. 151 of each at minimum) plus 79 signal cells each contributing
  `VPWR`+`VPB`→`VPWR` and `VGND`+`VNB`→`VGND` (2 of each, i.e. up to 158 more) —
  151 + 158 = 309 is a lower bound assuming every signal cell pin resolves
  (some pin sets are smaller, e.g. the mux2_1/dfrtp_2 families' supply pin
  counts vary slightly by cell), consistent with the observed 367. Puzzle:
  `VGND=2560, VPWR=2560` against **880** fill instances (204 `decap_3` + 676
  `tapvpwrvgnd_1`) plus 738 signal cells — same shape, no red flags (every
  count is comfortably above the fill-only floor, and both supply nets carry
  the same count, as expected for a design where every non-fill cell has
  both a power and a ground pin).

## Two corrections to the naive algorithm (found by running it, not by inspection)

The issue's proposed algorithm treats standard cells as pure black boxes: only
`VIA_*` cell instances and the top cell's own drawn shapes are "conductors";
a standard cell contributes only its declared pin polygons. Implemented
literally, this produced two classes of false "unconnected pin" errors on the
very first `04_final.gds` run — 21 pins (`sky130_fd_sc_hd__dfrtp_2`'s
`RESET_B`, 16 instances; `sky130_fd_sc_hd__xor2_2`'s `B`, 5 instances) — for
pins `warmup/01_netlist.v` shows are genuinely wired (`.RESET_B(rst_n)` on
every flop, `.B(a_reg[1])` etc.). Root cause, chased down instance by
instance with the GDS geometry directly (not guessed):

1. **A pin's `.pin`-purpose marker is not always its full net extent inside
   the cell.** A pin can expose several separate `.pin` tabs (e.g. a
   high-drive cell with parallel legs) tied together by a much larger
   underlying `li1` "draw"-purpose shape inside the same cell definition, and
   a via can legally land anywhere on that larger shape, not only inside the
   narrow tab. Fix: `gds_extract._expand_pin_shapes` expands each pin's
   marker(s) to the full cell-local merged `li1` (or other target-layer)
   island they sit on, before transforming to top-level coordinates.
2. **Some nets are distributed by direct `li1` abutment between adjacent
   standard-cell instances, with no `VIA_*` cell anywhere near the pin.**
   Confirmed directly: the closest `VIA_L1M1_PR_MR` (mcon) to one `dfrtp_2`
   instance's `RESET_B` pin is 1.67 µm away — no via touches that pin at all.
   Re-running the *same* connectivity trace over the full flattened `li1`
   geometry (every non-`other` instance's own drawn shapes, not only
   `VIA_*`'s) found the missing link: a neighbouring instance's own `li1`
   shape directly overlaps the flop's `RESET_B` marker. Fix:
   `gds_extract._gather_regions` includes every placed instance's own drawn
   conductor/via-layer shapes in the global pool (not only `VIA_*` cells'),
   while still only ever *naming* a net from a standard cell's declared pins
   (never from unlabelled internal geometry) — cells stay black boxes for
   *emission*, not for *conductivity*.

Both corrections are general (not warm-up-specific patches): they changed
the algorithm's geometry-gathering step, and the same code path ran
unmodified against `puzzle.gds` with zero unresolved pins on the first try
after the fix.

These are algorithm refinements within this implementation, not `klt`
defects — `klt extract`'s own device-level extraction is a different,
already-documented gap (`2AMLogic/klayout-tools#619`/`#620`, see
`evidence/upstream.md`). Nothing new is being filed upstream for this issue's
build; see the PR description if that changes during review.

## CI wiring

`scripts/warmup-regression.sh` already ran `tools/extract`/`tools/compare`
unconditionally once `tools/extract` became executable (its only gate was
`[ -x tools/extract ]`), and `.github/workflows/ci.yml` runs that script.
Neither installed a `klayout` Python package, so landing `tools/extract`
without any CI change would have turned the previously-loud-SKIP stage into a
hard failure on every future CI run (not a regression in the extractor —
`klayout` simply would not be importable on the runner at all). Added one
step, `pip install klayout`, to `.github/workflows/ci.yml` before the lint
step, so `klayout_env.ensure_klayout()`'s fast path resolves. This is
environment plumbing to keep the existing wiring functional, not the
`--require-extract` enforcement change itself — that is issue #9's tracked
scope (turning a missing/broken extractor into a hard CI failure, and
recording the pass in `evidence/warmup-regression.md`).
