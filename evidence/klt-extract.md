# `klt extract --abstract-cells` — recorded run

Per `CLAUDE.md` §5: what was executed, append-only. Re-run with
`./scripts/fetch-puzzle.sh` then `./scripts/warmup-regression.sh --no-fetch`
(warm-up) or `tools/klt-extract puzzle/puzzle.gds -o build/puzzle-klt.v` and
`tools/compare build/puzzle-klt.v evidence/puzzle-extracted.v` (puzzle).
Upstream identifiers are not reproduced here (`CLAUDE.md` §3).

## Run 1 — 2026-10-17

- Toolkit: `klt 0.7.1.dev1743+g7ee09483b748` (klayout-tools commit
  `7ee09483b748`), on Linux 7.0.0 (aws), single local `klt extract` per layout.
- Command: `klt extract <gds> --deck sky130 --abstract-cells 'sky130_fd_sc_hd__*'`,
  converted by `tools/klt-extract` (no `--abstract-cell-lef` needed: every cell
  type resolved its pins from in-cell labels).

### Warm-up: `04_final.gds` vs published `01_netlist.v`

`tools/compare` reports **EQUIVALENT**: 6 ports matched by name, 79 signal
cells matched 1:1, 84 nets matched, 151 fill cells matched by count
(58 decap, 93 tap), independent re-check of the mapping passed. Also gated by
`scripts/warmup-regression.sh` step 5, including a mutation check (an instance
removed from the converted netlist is rejected).

### Puzzle: `puzzle.gds` vs `evidence/puzzle-extracted.v` (`tools/extract`)

No published ground truth exists, so the claim is agreement between two
independent extractors. `tools/compare` reports **EQUIVALENT**: 13 ports
matched by name, 728 signal cells matched 1:1, 739 nets matched, 890 fill
cells matched by count (204 decap, 10 diode, 676 tap). The 728 logic and
sequential instances plus the 10 diodes give the 738 count in #46.

The confirmed floating input is reproduced: in each netlist exactly one net,
not a port, feeds cell inputs and is driven by no cell output — the net
`net_00575` in `evidence/puzzle-extracted.v` and the anonymous net `$840` in
the `klt` netlist, each feeding the `A1` pins of one `a31oi_2` and one
`a311o_2`.

### Advisories and differences

- No disagreement with ground truth or with `tools/extract`; nothing filed
  upstream. `klt` printed informational advisories (substrate net `vsubs`
  dropped from abstracted pin lists, VPB/VPWR tied on 74 warm-up instances,
  dead metal, layers outside the deck) that do not affect the comparison.
- `klt`'s anonymous net numbering is not stable across versions (its own
  docs say so); the comparison is topological, so this does not matter here.
- Live CI verification not performed: CI installs only the `klayout` wheel, so
  step 5 is SKIPPED there. Out of scope per #46.
