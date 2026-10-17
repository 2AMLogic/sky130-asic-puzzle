# Warm-up `klt lvs` — recorded run (append-only)

`CLAUDE.md` §4 and §5: the published warm-up layout and its own synthesized
gate-level netlist come from a flow that is not `klt`'s, so this is the one
canary check where `klt lvs` meets a third-party layout with published ground
truth. This is what was actually executed. Re-run it with
`./scripts/warmup-klt-lvs.sh` (needs `puzzle/`, fetched by
`./scripts/fetch-puzzle.sh`, and a sky130 PDK), then re-verify the committed
envelopes from the repo root with
`klt lvs --check evidence/warmup-klt-lvs-01.json` (and `-02`).

The upstream files are not vendored (`CLAUDE.md` §3). The envelopes record
verdicts, counts, layout-side names and hashes; the script elides the
reference-side net and instance names (`net_correspondence`, and
`mismatches[].instance.reference`), as `evidence/warmup-regression.md` does.

Verified with the cheap `klt lvs --check` (exit 0 for both envelopes, run from
the repo root). Full mode (`--check --rerun`) was tried and fails by design for
these reports: it reconstructs the request without `reference.form`, so the
Verilog reference is re-read as plain-element SPICE (the tool says so in its
error). That is documented upstream behaviour (klayout-tools#2250), not a new
finding.

## Run 1 — 2026-10-17

Environment: Linux (AWS dispatch worker), `klt 0.7.1.dev1743+g7ee09483b748`,
klayout 0.30.12, PDK `sky130A` (open_pdks `f6eeac7dad08…`, found under
`~/.ciel`; `klt pdk find --pdk sky130A` resolves it, the bare name `sky130`
does not). klayout-tools commit: `7ee09483b748` (from the version string; a
dev build, `deck.released: false`).

Commands (as scripted, `scripts/warmup-klt-lvs.sh`):

```
klt extract puzzle/warmup/04_final.gds --deck sky130 --pdk sky130A --top adder_demo \
  --abstract-cells 'sky130_fd_sc_hd__*' --def-pins puzzle/warmup/03_post_place_and_route.def \
  -o build/warmup-klt-lvs.spice --format json
PDK=sky130A klt lvs - --format json   # request on stdin, once per reference below
  # {"layout": {"netlist": "build/warmup-klt-lvs.spice", "top": "adder_demo"},
  #  "reference": {"netlist": "puzzle/warmup/<ref>.v", "top": "adder_demo",
  #                "form": "gate-level-verilog", "library": "sky130_fd_sc_hd"}}
```

Extraction: 120 nets, 8 pins (`A B S VGND VPWR clk en rst_n`, all 8 promoted
from the DEF's PINS section by `--def-pins`; no unmatched), 230 abstracted
instances over 18 cell types, 0 extracted devices (everything is a black box,
as intended). `--def-net-names` was not used: it needs DEF net-name properties
on the GDS shapes, which a GDS from another flow does not carry, and
`--def-net-connections` requires `--spef`. Internal nets therefore come out as
anonymous `$N`; `klt lvs` is topological so this does not matter.

| Reference | `status` | `power_connectivity.status` | `body_verification.status` | mismatches | Envelope |
|---|---|---|---|---|---|
| `01_netlist.v` (signal-only) | **match** | `match` | `unchecked` | 2 warnings, 0 errors | `warmup-klt-lvs-01.json` |
| `02_netlist_with_power_rails.v` (PG pins) | **mismatch** | `unchecked` | `unchecked` | 159 (158 errors) | `warmup-klt-lvs-02.json` |

### `01_netlist.v` — match

The extracted layout is LVS-equivalent to the published netlist. The two
warnings are informational: `topology.power_only_pruned` (the tap cell is a
power-only master and is removed from both sides before comparing) and
`topology.top_level_pins_anchored` (the 6 signal pins `A B CLK EN RST_N S`
were matched by name).

`power_connectivity` is `match`, which is **not** what the issue text
predicted (`unchecked`, since the reference is signal-only). It derived the
power pins `VGND`/`VPWR` from the reference library's pin-order data
("declared by every instantiated master", 18 masters, corroborated) and found
no findings over 230 instances. That is a statement about the layout's
power wiring as seen through the black boxes' power pins, not about transistor
bodies. `body_verification` is `unchecked` because a pre-extracted netlist
carries no deck, so nothing is established about device bodies (`klt lvs`
says so itself).

### `02_netlist_with_power_rails.v` — mismatch, tool-side

The same layout against the PG-pin form of the same netlist does **not**
match: 122 `topology` errors, 34 `net.unmatched`, and 2 `hints.rejected` (the
`VGND`/`VPWR` name anchors the comparer could not confirm). `power_connectivity`
is `unchecked` with reason "no power/ground pin universe could be derived from
the reference library's own pin-order data".

Cause, as far as it was established: `klt extract --abstract-cells` drops the
substrate pin `VNB` from every std-cell black box (the extraction warns, per
cell type, that the port "resolves only through the deck's synthesized global
net 'vsubs'"), so each abstracted subcircuit carries one pin fewer than the
library cell, while the `02` reference connects all of
`VGND/VNB/VPB/VPWR`. Passing `--abstract-cell-lef` with the PDK's
`sky130_fd_sc_hd.lef` (the warning's own suggested remedy) left the emitted
pin list unchanged and the verdict identical (run once, scratch directory, not
committed). This is the likely cause, not a controlled isolation: a one-instance
synthetic fixture built from the PDK's own `inv_1` reproduces the same
`mismatch` / `unchecked` shape, but it also has no top-level pins, so it
cannot separate the two effects. Filed generically, see below.

The mismatch is the tool's, not the layout's: `01` is the same netlist minus
the PG connections and matches.

### Upstream findings (filed toolkit-first, synthetic reproducers)

- [2AMLogic/klayout-tools#3748](https://github.com/2AMLogic/klayout-tools/issues/3748):
  `klt lvs` cannot select the PDK variant. With `gf180mcuA` and `sky130A` both
  installed it resolved `gf180mcuA` for a `sky130_fd_sc_hd` library and failed;
  `export PDK=sky130A` is the only workaround found.
- [2AMLogic/klayout-tools#3749](https://github.com/2AMLogic/klayout-tools/issues/3749):
  `--abstract-cells` omits `VNB` from std-cell black boxes, so a power-rail
  gate-level reference cannot match.

### Not done

Scope item 3 (optional: `puzzle.gds` against `evidence/puzzle-extracted.v`) was
not run. It is self-consistency, not ground truth, and the warm-up result is
the deliverable here.
