# tools/

Extraction, recognition, and simulation harness for this repo (see
`spec/puzzle.md` for the staged plan this implements against).

## In-stream labels, no PDK required (stages 2–3)

`spec/puzzle.md` originally assumed cell inventory was easy and pin geometry
needed a PDK ("every cell's pins resolved from the PDK, none guessed").
Reconnaissance for issue #1 found that assumption backwards: **pin
geometry is fully recoverable from the GDS stream itself.** Reading
`warmup/04_final.gds` and `puzzle.gds` with KLayout's Python API
(`klayout.db`), every pin — on every `sky130_fd_sc_hd__*` standard cell, and
on the chip's own top-level ports — carries a GDS text label on a known
layer, sitting inside the drawn shape that *is* that pin:

| Layer | Purpose | Where the text lives |
|---|---|---|
| `67/5` li1.label | signal pin names (`A`, `B`, `X`, `Y`, `A1`/`A2`/`A3`/`B1`, `B1_N`, `D`, `Q`, `CLK`, `RESET_B`, `S`, …) | inside each standard-cell definition |
| `68/5` met1.label | `VPWR`, `VGND` | inside each standard-cell definition |
| `64/5` nwell.label | `VPB` (n-well bias) | inside each standard-cell definition |
| `64/59` | `VNB` (substrate bias) — same GDS layer *number* as nwell, but the shape this label actually marks lives on the p-well layer, 122, not 64 (see `gds_layers.PIN_TARGET_LAYER`) | inside each standard-cell definition |
| `70/5` met3.label | top-level (chip) signal port names | drawn directly in the top cell |
| `71/5`, `72/5` met4/met5.label | top-level `VPWR`, `VGND` | drawn directly in the top cell |

So the PDK is a **cross-check, not a dependency**, for both stage 2 (cell
inventory) and stage 3 (pin geometry) of `spec/puzzle.md`. `tools/inventory`
and `tools/pins` need no PDK install to run to completion; `tools/pins
--pdk-crosscheck` uses one opportunistically, if resolvable, purely to
report disagreement — it is off by default and never required for a green
run.

### `tools/inventory` — top-cell instance census

    tools/inventory <path.gds> [--format json|markdown]

Walks the top cell's placed instances and classifies each by cell name:

- **`via`** — `VIA_*` routing cells (the place-and-route tool's via arrays).
- **`fill`** — `sky130_fd_sc_hd__tapvpwrvgnd_*` / `..__decap_*`: no signal
  connectivity, present for physical design rules only.
- **`sequential`** — the library's flip-flop/latch cell families (`dfxtp`,
  `dfrtp`, `dfstp`, …; see `gds_layers.SEQUENTIAL_FAMILIES`).
- **`logic`** — every other `sky130_fd_sc_hd__*` cell.
- **`other`** — anything matching neither a `VIA_*` nor a
  `sky130_fd_sc_hd__*` name. This is a deliberate, reported bucket, not a
  silent default: `puzzle.gds` places 36 instances of two cells named
  `INTERNAL_3` / `INTERNAL_7` (single unlabelled shapes on an otherwise
  unused layer, sized to the standard-cell row height) that are neither —
  see `evidence/inventory-puzzle.json`. Folding them into `via` or `logic`
  on a guess would have made the corrected counts below wrong twice over,
  so they are reported by name instead.

Also reports the top-level port names read off `70/5`/`71/5`/`72/5` (see the
table above), for both streams:

- `warmup/04_final.gds`: `A B S clk en rst_n`
- `puzzle.gds`: `I O[0] O[1] O[2] O[3] O[4] O[5] O[6] O[7] clk enable rst_n success`
  — exactly the variable set `example_inputs.vcd` declares.

Committed evidence: `evidence/inventory-warmup.json`,
`evidence/inventory-puzzle.json`. Running `tools/inventory puzzle/puzzle.gds`
against the stream disagreed with this repo's earlier README table on the
via/logic split (36 `INTERNAL_*` instances are neither, and `VIA_*` by literal
prefix match is 8,221, not 8,214) — the corrected, stream-derived numbers are
what `README.md`'s reconnaissance table now states; see that table for the
full corrected breakdown.

### `tools/pins` — per-cell pin abstracts

    tools/pins <path.gds> [-o DIR] [--keep-going] [--pdk-crosscheck]

For every distinct `sky130_fd_sc_hd__*` cell *definition* the stream uses,
builds a pin abstract — pin name → (layer, polygons in that cell's own local
coordinates, **not** the top-level placement) — by associating each pin-name
label with the drawn shape it lands inside on the corresponding `.pin`
(KLayout purpose datatype 16) layer. See `tools/gds_pins.py`'s module
docstring for the exact algorithm, including why a label's own GDS layer
*number* is not always the layer its pin shape lives on (the `VNB` case
above) and why a pin can have more than one occurrence without every
occurrence needing its own distinct shape (observed on
`sky130_fd_sc_hd__and2b_2`: a second, redundant label along the same net).

**Resolution is total-or-loud**: a pin with zero occurrences landing inside a
`.pin` shape is a hard error naming the cell and the pin (exit 1) — never a
silently empty or skipped pin. `tools/test-pins` proves this is enforced,
not just documented, with a deliberately corrupted synthetic cell.

Cell coordinates, not top-level coordinates: applying the placement's
instance transform to get a top-level polygon is stage 4's job (issue #2),
and keeping the two separate is what makes a cell's pin abstract cacheable
across every instance of that cell.

`--pdk-crosscheck` (optional, off by default) compares the derived pin
*names* per cell against a resolvable sky130 PDK's own behavioural Verilog
(`tools/pdk_crosscheck.py`, reusing `tools/sim/pdk.py`'s resolver). Run for
real against `puzzle.gds` on a machine with `sky130A` installed, it agrees
for 68 of 69 cells and finds one genuine, structural disagreement:
`sky130_fd_sc_hd__tapvpwrvgnd_1`'s library-declared `VPB`/`VNB` ports have no
corresponding label anywhere in the GDS definition for that cell — the tap
cell's well connection is not independently labelled the way every other
cell's is. That is a real property of the stream, not a bug in either the
resolver or the library.

Committed evidence: `evidence/pins-sky130_fd_sc_hd.json` (all 69 cells used
by `puzzle.gds`, zero unresolved pins, `--pdk-crosscheck` off — the default,
green-run form; local PDK install paths are not reproducible across
machines, so they are not baked into committed evidence).

### `tools/gds_layers.py`, `tools/klayout_env.py`

Shared knowledge: `gds_layers.py` holds the layer numbers, cell-name
classification, and pin-label-to-target-layer table above (all derived
empirically, cited inline with which check backs each claim);
`klayout_env.py` resolves an importable `klayout` Python module (preferring
whatever's already importable, then `$KLAYOUT_PYTHON`, then the interpreter
behind `klt` on `PATH` — `klayout-tools` already depends on it, so that
interpreter reliably has it without asking a contributor to `pip install`
anything extra) and re-execs into it if needed. Both `tools/inventory` and
`tools/pins` call `klayout_env.ensure_klayout()` before importing
`klayout.db`, so either command works from a plain `python3` with no
`klayout` package of its own, as long as `klt` is on `PATH`.

## `tools/extract` — cell-level connectivity extraction (stage 4)

    tools/extract <path.gds> [-o out.v] [--json out.json] [--top NAME] [--stats]

Reads a placed-and-routed sky130 GDS stream directly (no PDK, and — unlike
`klt extract` — no device-level SPICE step) and emits a **gate-level**
Verilog + JSON netlist (`verilog_netlist.SCHEMA`) by tracing physical
connectivity through the routing stack. `-o` writes structural Verilog
(stdout if omitted); `--json` additionally writes the canonical JSON form;
`--stats` prints the extraction report (below) to stderr even when both
outputs are files. Backed by `tools/gds_extract.py`; issue #1's cell
inventory (`gds_layers.classify`) and pin abstracts
(`gds_pins.resolve_cell_pin_shapes`) are the two building blocks this reuses
rather than re-deriving.

### Conductor stack and via handling

The routing stack this reads, bottom to top, and what bridges each
consecutive pair:

| Conductor (drawn, datatype 20) | GDS layer | Via above it (datatype 44) | GDS layer |
|---|---|---|---|
| `li1` | 67 | `mcon` | 67 |
| `met1` | 68 | `via` | 68 |
| `met2` | 69 | `via2` | 69 |
| `met3` | 70 | `via3` | 70 |
| `met4` | 71 | `via4` | 71 |
| `met5` | 72 | — | — |

(Confirmed empirically, not assumed: every `VIA_*` cell definition in both
`warmup/04_final.gds` and `puzzle.gds` draws shapes on *exactly* the
conductor-layer pair its own via-cut layer number predicts — e.g.
`VIA_M2M3_PR` draws on 69/20, 70/20 and 69/44, and nothing else.)

Two independent geometry sources feed each conductor/via layer, both
required:

- **Drawn directly in the top cell** — the P&R tool's own routing shapes
  (`met1`-`met5` carry these; `li1` never does — see below).
- **Drawn inside a `VIA_*` cell definition, transformed by its placement.**
  `VIA_*` instances are the P&R tool's via arrays/singles; their own cell
  definitions draw the *conductor* pads on both sides of the via as well as
  the cut itself (e.g. `VIA_L1M1_PR_MR` draws 67/20, 68/20 **and** 67/44). On
  both designs this repo works with, `li1` conductor geometry at the top
  level comes *exclusively* from `VIA_*` cells — the top cell itself draws
  zero `li1` shapes directly, since `li1` is confined to standard-cell rows.

Same-layer connectivity is a `klayout.db.Region.merged()` over all shapes on
that layer (from both sources above): touching/overlapping shapes on one
layer become one physical "island". Vertical connectivity unions an island on
layer N with an island on layer N+1 wherever a via-layer shape (drawn or
`VIA_*`-cell-contributed, same two sources) touches both. This is a plain
union-find, not `klayout.db.LayoutToNetlist` — the latter's device/circuit
model is built for polygon-to-transistor recognition; this problem only
needs polygon-to-polygon connectivity, so a direct implementation is both
simpler and easier to audit than fitting a black-box-cell shape into an LVS
engine designed for something else.

**Standard cells are black boxes for *naming*, not for *conductivity*.**
Only a cell's declared pins (`gds_pins`) ever become a net *connection* in
the output — nothing about a cell's unlabelled internal geometry is ever
exposed as a signal name. But restricting the conductor *pool* itself to only
`VIA_*`-instance geometry produced false "unconnected pin" errors on real,
connected pins in `warmup/04_final.gds` — traced to two real physical
mechanisms a purely pin-and-via model misses:

1. **A `.pin`-purpose marker is not always a pin's full net extent inside the
   cell.** A high-drive-strength cell (parallel transistor legs, e.g.
   `clkbuf_16`) can expose several separate `.pin` tabs for the same pin,
   tied together by one much larger underlying `li1` "draw"-purpose shape —
   and a via may legally land anywhere on that larger shape, not only inside
   a narrow tab. `gds_extract._expand_pin_shapes` expands each pin's
   marker(s) to the full **cell-local** merged island they sit on (a
   same-layer merge scoped to one cell definition) before transforming to
   top-level coordinates.
2. **Some nets are distributed by direct `li1` abutment between adjacent
   standard-cell instances, with no `VIA_*` cell anywhere nearby.** Confirmed
   directly on `warmup/04_final.gds`: `sky130_fd_sc_hd__dfrtp_2`'s
   `RESET_B` pin (wired `.RESET_B(rst_n)` on all 16 instances in
   `warmup/01_netlist.v`) has no `VIA_*` cell within 1.67 µm of its own pin
   shape — the reset signal reaches it via a neighbouring instance's own
   `li1` geometry touching the pin directly. `gds_extract._gather_regions`
   therefore includes **every** placed instance's own drawn shapes (standard
   cells and fill cells too, not only `VIA_*`) in the global conductor pool.

Both were found by running the extractor and chasing its first false
"unconnected pin" down to real GDS geometry, not by inspection — see
`evidence/extraction-notes.md` for the full trace of both.

### Supply pins (VPWR/VGND/VPB/VNB)

`VPWR`/`VPB` pins collapse to a single net `"VPWR"`; `VGND`/`VNB` collapse to
`"VGND"` — by pin **name**, never resolved geometrically, and never emitted
as a connection on any instance in the output (matching both
`warmup/01_netlist.v`, which never wires power pins, and this repo's own
simulation harness, `tools/sim/icarus.py`, compiled without
`USE_POWER_PINS`). `VPB`/`VNB` resolve to shapes on the nwell/pwell layers
(64/122) entirely outside the `li1`-`met5` stack above, so there is no
top-level routing model to resolve them against even if that were wanted.

The same union-find is still run across the full stack purely as a sanity
check, independent of the name collapse: a net found carrying both a supply
label (`VPWR`/`VGND`, read from met4/met5 text) and a non-supply top-level
port label — or both `VPWR` and `VGND` at once — is a hard `ExtractionError`
("spurious supply short"), and the extraction report
(`tools/extract --stats`) prints the number of distinct physical islands each
supply label resolves to (expected: exactly 1 each) plus the total
name-collapsed connection count per supply, for a rough cross-check against
the fill-cell count. See `evidence/extraction-notes.md` for real numbers from
both designs.

### Pin-transform correctness

Every standard-cell instance's pin geometry is transformed from the cell's
own local coordinates to top-level coordinates via `db.Instance.dcplx_trans`
(KLayout's own placement transform, in microns — handles the 90-degree
rotations and mirrors sky130 rows use heavily without any hand-rolled
trigonometry). Neither design this repo works with uses instance arrays or
magnification (`db.Instance.is_regular_array()` is `False` and
`cplx_trans.mag == 1.0` for all 1,099 / 9,875 top-cell instances, checked
directly), so a plain `db.Trans` always applies. As a direct check on
transform correctness (the "highest-risk detail" issue #2 calls out), every
transformed pin polygon is asserted to lie inside its own instance's
bounding box (`db.DBox`, small tolerance for floating-point rounding) before
it is used for any connectivity query — a transform bug would show up as
this assertion failing, not as a silently wrong net.

### Instance naming

Emitted instance names are `<base-cell-name>_<x>_<y>`, where `(x, y)` is the
instance's own **transformed bounding box**'s lower-left corner in dbu — not
`db.Instance.trans.disp` (the raw placement pivot point), which two
instances can legitimately share while occupying disjoint footprints (e.g. a
`r180`-rotated and an `r0` instance placed in adjacent rows, confirmed on
`warmup/04_final.gds`: two distinct `sky130_fd_sc_hd__and2_2` instances at
the identical `disp`). The transformed bbox corner is unique per instance
(no two placed instances may legally overlap) and fully deterministic.

## `tools/vcd` — minimal VCD reader/writer

`tools/vcd/reader.py` / `tools/vcd/writer.py` parse and emit the subset of
IEEE 1364 VCD this repo needs: `$timescale`, `$scope`/`$var`/`$upscope`,
and `$dumpvars`/value-change sections with scalar and vector values. It is
deliberately not a general-purpose VCD library — the format is small enough
that a dependency is optional here, not required (see the module docstrings
in `tools/vcd/model.py`). Round-trips `puzzle/example_inputs.vcd` losslessly
(same signal histories in, same signal histories out).

## `tools/sim` — simulation harness

Builds on `tools/vcd` plus [Icarus Verilog](http://iverilog.icarus.com/)
(`iverilog`/`vvp`) to simulate gate-level `sky130_fd_sc_hd` netlists —
Icarus is what `klt functional-verification` already targets alongside
Verilator, and is sufficient for this repo's 92-flop scale.

| Module | Role |
|---|---|
| `tools/sim/pdk.py` | resolves `sky130_fd_sc_hd`'s behavioural Verilog models (see below) |
| `tools/sim/icarus.py` | thin `iverilog`/`vvp` wrapper with the compile defines the models need |
| `tools/sim/testbench.py` | generates directed-test and VCD-replay Verilog testbenches |
| `tools/sim/directed.py` | the `A + B == 496` directed test (stage 5) |
| `tools/sim/replay.py` | general VCD replay + trace diff (stage 6) |
| `tools/sim/selftest_replay.py` | self-tests `replay.py` against the warm-up (see `evidence/warmup-sim.md`) |
| `tools/sim/selftest_pdk.py` | self-tests `pdk.py`'s resolution order and its no-PDK-anywhere failure path (all three sources mocked; needs no PDK) |
| `tools/sim/run_warmup_directed.py` | CLI for the directed warm-up test |
| `tools/sim/run_vcd_replay.py` | CLI for general VCD replay |

### Where the behavioural models come from, and how to install them

Simulating a `sky130_fd_sc_hd` netlist needs the standard-cell library's
behavioural Verilog (`sky130_fd_sc_hd.v` + its UDP primitives,
`primitives.v`) — genuinely external content, unlike the pin geometry the
KLayout tech stream carries. It is **not vendored** here: the sky130 PDK is
Apache-2.0, so vendoring would be permissible, but `CLAUDE.md` §3's fetch-
rather-than-vendor habit is the right default for this too, and a resolver
keeps the repo small and always current with whatever install is actually on
the machine.

`tools/sim/pdk.py::resolve_sky130_models()` resolves it, in order:

1. `klt pdk find --pdk sky130A --format json` — klayout-tools' own PDK
   resolver (its documented search order: `$PDK`/`$PDK_ROOT`, then
   well-known install roots including `~/.volare`), if `klt` is on `PATH`.
2. `$PDK_ROOT/sky130A/...` directly, if `klt` is unavailable or its
   resolution doesn't include a verilog dir.
3. `~/.volare/sky130A/...` directly, matching volare's default install
   location, as a last resort.

If none of these find both `primitives.v` and `sky130_fd_sc_hd.v`,
resolution fails with **one actionable line** and a non-zero exit — never a
silent skip or a green run against an empty model set:

```
No resolvable sky130 PDK found (looked for sky130_fd_sc_hd's behavioural
Verilog via `klt pdk find --pdk sky130A`, $PDK_ROOT, and ~/.volare). Install
one with volare: `pip install volare && volare enable
$(volare ls-remote sky130 --limit 1 -f '{version}')`, or point $PDK_ROOT at
an existing open_pdks sky130A install, then re-run.
```

That failure path is covered by a committed self-test rather than a manual
check — it pins `klt`/`$PDK_ROOT`/`~/.volare` at controlled temporary
directories so the no-PDK-anywhere case is reachable even on a machine that
*does* have a PDK installed, and includes positive controls for all three
sources so the failure assertions cannot pass vacuously:

```sh
python3 -m tools.sim.selftest_pdk
```

It needs no PDK, no `klt` and no simulator; recorded output is in
`evidence/warmup-sim.md`.

Every evidence record this harness produces states which of the three
sources resolved, plus the PDK version and the exact model file paths used
(`ResolvedModels.describe()`) — a simulation whose model provenance is
unstated is not re-runnable (CLAUDE.md §5).

### Compile-time defines

`sky130_fd_sc_hd.v` selects among functional/timing and power-pin/no-power-
pin model variants via `` `ifdef ``. `tools/sim/icarus.py` always compiles
with:

- `FUNCTIONAL` defined — picks the simulation functional model, not the
  SDF-timing-oriented one (no setup/hold checks to violate at zero-delay).
- `USE_POWER_PINS` left **undefined** — this repo's netlists (both
  `warmup/01_netlist.v` and, once it exists, an extracted netlist) don't
  wire `VPWR`/`VGND`/`VPB`/`VNB` explicitly, so the port list without those
  pins is the one that matches.
- `UNIT_DELAY=#1` — the primitive instantiations inside the models
  (`` `UNIT_DELAY dff0 (...) ``) need this macro defined to compile at all;
  `#1` avoids zero-delay races without materially affecting a cycle-level
  functional check.

### Usage

Directed warm-up test (stage 5, no VCD or extractor needed):

```sh
python3 -m tools.sim.run_warmup_directed \
    --netlist puzzle/warmup/01_netlist.v \
    --random 50
```

VCD replay (stage 6, needs an extracted netlist):

```sh
python3 -m tools.sim.run_vcd_replay \
    --netlist <extracted-netlist.v> \
    --vcd puzzle/example_inputs.vcd \
    --top <top-module> \
    --inputs clk,rst_n,enable,I \
    --outputs O,success
```

Replay-engine self-test (exercises the full VCD replay path against the
warm-up, with no dependency on an extractor):

```sh
python3 -m tools.sim.selftest_replay
```

PDK-resolver self-test (resolution order + the no-PDK-anywhere failure
path; no PDK, `klt` or simulator required):

```sh
python3 -m tools.sim.selftest_pdk
```

See `evidence/warmup-sim.md` and `evidence/puzzle-replay.md` for recorded
results and current status.
