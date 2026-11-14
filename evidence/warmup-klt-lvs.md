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

> **2026-11-14 (Run 2): both sentences above have stopped being true of the
> committed envelopes, for two separate reasons.** The `--rerun` limitation is
> gone — Run 2's envelopes carry a `reference_conversion` block echoing
> `form`/`library`/`pdk`, and a probe with the reference outside `puzzle/`
> re-runs clean (exit 0, `status: match`), so klayout-tools#2250 no longer
> applies. But cheap `--check` no longer exits 0 either: `puzzle/` is a git
> clone, and the klt that writes the envelope records a reference path relative
> to *that* nested repo while `--check` resolves it against this one
> (klayout-tools#5631). Both are detailed in Run 2 below; Run 1's text above is
> left as recorded.

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

## Run 2 — 2026-11-14

Why: both tool-side findings Run 1 filed were closed upstream
(klayout-tools#3748 by PR #3759, #3749 by PR #3763). This re-runs the same
check on a build that contains both, to see what actually changed on a
third-party layout with published ground truth.

Environment: Linux (AWS dispatch worker), `klt 0.9.2.dev1022+g2a9c52b27ce7`,
klayout 0.30.13, PDK `sky130A` (open_pdks `f6eeac7dad08…`, found under
`~/.ciel`). klayout-tools commit `2a9c52b27ce7` (from the version string).
Run 1 was `klt 0.7.1.dev1743+g7ee09483b748` / klayout 0.30.12. klt warns on
every invocation that 0.30.13 is not the klayout it was tested against
(0.30.12) and that counts may differ from a 0.30.12 report; the verdicts
below are unaffected by that, since the no-flag control reproduces Run 1's
numbers exactly (see "What the flag changed").

Two things in `scripts/warmup-klt-lvs.sh` changed for this run, both because
Run 1's findings turned out to be incompletely stated:

1. **`--abstract-cell-lef` is now passed** to `klt extract`, resolved from
   `klt pdk find --pdk "$PDK" --format json`'s `libs_ref` asset. PR #3763's fix
   for #3749 is opt-in: `_merge_lef_pins` returns early for any cell absent
   from the `--abstract-cell-lef` macro table, so without the flag the fix is
   inert and this run would have re-recorded Run 1's result on a build that
   contains it.
2. **The PDK variant is named in the request** (`reference.pdk`) instead of
   exported as `$PDK`. `reference.pdk`/`reference.pdk_root` are request fields
   that already existed at Run 1 — upstream's fix for #3748 was message-only
   ("No JSON field or resolution behavior changed"); it made the error name
   `request.reference.pdk`/`$PDK` rather than adding a selector. Run 1's note
   that `klt lvs` has "no request field for the PDK variant" was wrong, and
   `evidence/upstream.md`'s row for #3748 has been corrected.

Commands (as scripted, `scripts/warmup-klt-lvs.sh`):

```
klt extract puzzle/warmup/04_final.gds --deck sky130 --pdk sky130A --top adder_demo \
  --abstract-cells 'sky130_fd_sc_hd__*' \
  --abstract-cell-lef <libs_ref>/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef \
  --def-pins puzzle/warmup/03_post_place_and_route.def \
  -o build/warmup-klt-lvs.spice --format json
klt lvs - --format json   # request on stdin, once per reference below
  # {"layout": {"netlist": "build/warmup-klt-lvs.spice", "top": "adder_demo"},
  #  "reference": {"netlist": "puzzle/warmup/<ref>.v", "top": "adder_demo",
  #                "form": "gate-level-verilog", "library": "sky130_fd_sc_hd",
  #                "pdk": "sky130A"}}
```

The whole run was executed with `env -u PDK -u PDK_ROOT`, so the `$PDK`
export Run 1 relied on was demonstrably not in play.

Extraction: 121 nets, 8 pins (unchanged, all promoted from the DEF's PINS
section), 230 abstracted instances over 18 cell types, 0 extracted devices.
17 of the 18 cell types record a `lef_path` — the exception is
`sky130_fd_sc_hd__tapvpwrvgnd_1`, whose two pins the in-cell labels already
supplied, so nothing was merged into it. The net count is one higher than Run
1's 120; the extra net is `vsubs`, and that one net is the whole story below.

| Reference | `status` | `power_connectivity.status` | `body_verification.status` | mismatches | Envelope |
|---|---|---|---|---|---|
| `01_netlist.v` (signal-only) | **match** | `match` | `unchecked` | 2 warnings, 0 errors | `warmup-klt-lvs-01.json` |
| `02_netlist_with_power_rails.v` (PG pins) | **mismatch** | `unchecked` | `unchecked` | 243 (242 errors) | `warmup-klt-lvs-02.json` |

Verdict shape is unchanged from Run 1. `01` still matches; `02` still does
not — and now mismatches *harder* (243 vs Run 1's 159).

### Black-box pin lists: the #3749 fix did engage

Run 1's black boxes carried no `VNB`. Run 2's do, for every std cell that
declares one in the PDK LEF. From `build/warmup-klt-lvs.spice`:

```
.SUBCKT sky130_fd_sc_hd__xor2_2 A B VGND VNB VPB VPWR X          (7 pins)
.SUBCKT sky130_fd_sc_hd__dfrtp_2 CLK D Q RESET_B VGND VNB VPB VPWR
.SUBCKT sky130_fd_sc_hd__tapvpwrvgnd_1 VGND VPWR                 (unchanged)
```

Control, same build, same GDS, flag omitted (`build/baseline-noflag.spice`):

```
.SUBCKT sky130_fd_sc_hd__xor2_2 A B VGND VPB VPWR X              (6 pins)
.SUBCKT sky130_fd_sc_hd__dfrtp_2 CLK D Q RESET_B VGND VPB VPWR
```

So the pin list is attributable to `--abstract-cell-lef` and nothing else.
This matches PR #3763's own reported shape for `inv_1` (6 pins, was 5).

**The tie warning PR #3763 describes is not what this layout emits.** There is
a tie warning — 74 instances, "resolved two or more of their separately
declared pins onto the same net" — but every grouping it names is
`pins VPB, VPWR -> net 'VPWR'`, not `VGND, VNB`. It appears *identically in
the no-flag control*, so it is not a consequence of the merge. No warning
mentions `VNB` at all.

### `02_netlist_with_power_rails.v` — still mismatch, and why

The merged `VNB` pin does not land on the ground rail. It lands on the deck's
synthesized substrate global `vsubs`:

```
.SUBCKT sky130_fd_sc_hd__a21bo_2 A1 A2 B1_N VGND VNB VPB VPWR X
Xsky130_fd_sc_hd__a21bo_2_0 \$50 \$32 \$55 VGND vsubs VPWR VPWR \$123
                                           ^^^^ ^^^^^
                                           VGND  VNB
```

`VPB` resolves onto the real `VPWR` net; `VNB` resolves onto `vsubs`. Nothing
in the netlist connects `vsubs` to `VGND` — the one cell that physically makes
that tie, `sky130_fd_sc_hd__tapvpwrvgnd_1`, is itself a black box whose PDK LEF
declares only `VGND` and `VPWR`. The `02` reference ties each instance's body
pins to the rails, so the two sides disagree on every instance:

| | Run 1 (no flag) | Run 2 (flag) |
|---|---|---|
| `topology` errors | 122 | **205** |
| `net.unmatched` | 34 | **35** |
| `hints.rejected` | 2 | 2 |
| total mismatches | 159 | 243 |

The extra `net.unmatched` is `VSUBS` — "layout net has no reference
counterpart". `power_connectivity` is still `unchecked` for the same reason as
Run 1 (no power/ground pin universe derivable from the reference library's
pin-order data), and `body_verification` is still `unchecked` because a
pre-extracted netlist carries no deck.

**Filed upstream as klayout-tools#5632.** This is the "the merge happened and
the compare still fails" case, not "the merge did not happen" — the pin list
above establishes which. The finding is that the two fixes are in practice
mutually exclusive: passing `--abstract-cell-lef` restores the pin #3749
dropped and makes the gate-level compare strictly worse, omitting it gives up
the fix, and neither reaches `match`. Upstream has already **rejected**
modelling tap continuity in abstract extraction (#4363's
`_GROUND_SUBSTRATE_CAVEAT`), which is defensible — but the topology compare
then has no way to express the same exclusion. Options tried before filing,
none of which applies:

- `options.ignore_mos_bulk` (added for #5125) disconnects the `B` terminal of
  MOS *devices*; this netlist has `device_count: 0`, so it is a no-op.
- `hints.same_nets: [["vsubs", "VGND"]]` makes it worse — 429 mismatches, the
  35 `net.unmatched` becoming 35 `net.split`, `topology` 205 → 391,
  `hints_applied: null`. Same shape #5125 reported for the device case.
- `reference.device_bulk` only adds a terminal to the reference side.

Run 1 attributed the `02` mismatch to the dropped `VNB` pin. Run 2 shows that
was the proximate cause but not the whole one: restoring the pin does not
restore the match, because the pin has no path to the rail.

### What the flag changed, and what it did not

Re-running `02` against the no-flag extraction on this same build gives
**159 mismatches (158 errors), `topology` 122, `net.unmatched` 34** — Run 1's
numbers exactly. So Run 1's result reproduces on klt 0.9.2, and the entire
159 → 243 delta is attributable to `--abstract-cell-lef`. `01` is `match`
either way.

### `01_netlist.v` — match, unchanged

Still `match` with 2 informational warnings (`topology.power_only_pruned`,
`topology.top_level_pins_anchored` over 6 signal pins). `power_connectivity`
is `match` over 230 instances with 0 findings, derived from 18 masters,
corroborated — the same as Run 1. The extra `vsubs` net does not disturb it:
the signal-only reference declares no body pins, so nothing is asserted about
them.

### `klt lvs --check` on the committed envelopes — now fails, new finding

**Cheap `--check` does not exit 0 on either envelope**, which Run 1's preamble
says it should. It exits 3, `status: drifted`:

```
  [OK]       environment.layout_sha256
  [DRIFTED]  environment.reference_sha256
      actual: None (input not found: <repo>/warmup/01_netlist.v)
```

The recorded reference path lost its `puzzle/` segment. Run 1's envelope
recorded `puzzle/warmup/01_netlist.v`; Run 2's records `warmup/01_netlist.v`.
Cause: `puzzle/` is a git clone (`scripts/fetch-puzzle.sh`), and klt's
`env_provenance.repo_root_for()` anchors an input's `{path, scope}` on *the
input's own* nearest enclosing repo — which for `puzzle/warmup/*.v` is
`puzzle/`, not this repo. `--check` then resolves that path against the repo
the *report* lives in. The two roots disagree, so the round-trip cannot close.

Isolated with a synthetic reproducer needing no PDK — an outer git repo, a
nested git repo inside it, one trivial SPICE netlist in each — and **filed
upstream as klayout-tools#5631**. Removing the nested `.git` makes both the
recorded path and `--check` correct, which pins the cause to the nesting and
nothing else. There is no workaround from the request side: `repo_root_for`
takes `abspath` before walking up, so relative, `./`-prefixed and absolute
request paths all anchor the same way, and `--check --layout PATH` overrides
only the layout side — there is no `--reference` counterpart.

This is a repo-side regression in verifiability that no change here can fix
without either papering over the tool bug or changing how `puzzle/` is
fetched; it is left red and reported, per `CLAUDE.md` §2.

### `--check --rerun` — klayout-tools#2250 no longer applies

On the committed envelopes `--rerun` exits 1 with
`reference netlist not found`, i.e. it fails on #5631's path problem before
reaching the replay, so it says nothing about #2250 either way.

Probed separately with the reference copied to `build/` (inside this repo, so
outside the nested clone) and otherwise the identical request: **`--check`
exits 0 and `--check --rerun` exits 0 with `status: match`.** Run 2's
envelopes carry the `reference_conversion` block Run 1's lack —
`{"form": "gate-level-verilog", "library": "sky130_fd_sc_hd", "pdk":
"sky130A", "pdk_root": null, "pin_order_files": null}` — so the reference form
is no longer lost on reconstruction, and the #2250 limitation Run 1 recorded
is genuinely gone. Once #5631 is fixed, full-mode re-verification of these
envelopes should work.

### Does `klt lvs --check` need a PDK?

Two separate halves, both worth stating:

- **The command needs no PDK.** Cheap `--check` re-hashes recorded inputs; it
  resolves no PDK and runs no compare engine. It completes and prints a
  verdict with `PDK` unset and `PDK_ROOT=/nonexistent`. (`--check --rerun`
  does need one, since it re-runs the compare and re-reads the library's
  pin-order data.)
- **But two of its recorded inputs are not committed here.** The envelopes
  name `build/warmup-klt-lvs.spice` (gitignored — derived from an unlicensed
  upstream GDS, `CLAUDE.md` §3) and `puzzle/warmup/*.v` (gitignored, fetched).
  So a fresh clone cannot verify them at all: it needs
  `./scripts/fetch-puzzle.sh` **and** a fresh extraction, and the extraction
  is the step that needs the PDK. A CI step built on `--check` would have to
  provision both, and today would additionally hit #5631.

### PDK selector

`$PDK` is no longer exported. The variant is named in the request
(`reference.pdk: "sky130A"`), and `klt extract` takes `--pdk` as it always
did; `$PDK` survives in the script only as the default for both. Verified by
running the whole pipeline under `env -u PDK -u PDK_ROOT`. `klt lvs` still has
no `--pdk` CLI flag, which is correct and not a gap — the request field is the
documented selector, and upstream's #3748 fix was to say so in the error text.

### Upstream findings (filed toolkit-first, synthetic reproducers)

- [2AMLogic/klayout-tools#5631](https://github.com/2AMLogic/klayout-tools/issues/5631):
  an input inside a nested git repo records an inner-repo-relative path that
  `klt lvs --check` resolves against the outer repo, so the report can never be
  re-verified. Reproducer: two nested `git init`s and a trivial SPICE netlist.
- [2AMLogic/klayout-tools#5632](https://github.com/2AMLogic/klayout-tools/issues/5632):
  the substrate pin `--abstract-cell-lef` merges lands on the isolated `vsubs`
  global, so a PG-pin gate-level reference cannot match — in the topology
  compare, which #4363's `power_connectivity` work did not cover. Reproducer:
  one inverter and one tap cell from the PDK's own GDS, ~20 lines of
  `klayout.db`.

Neither references this repository, the puzzle, or any file under `puzzle/`.
