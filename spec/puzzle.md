# What "solved" means here

Unlike the design canaries, this repo has no ratified spec to build against and no T1–T4
evidence tier to climb — the subject is someone else's finished chip. Success is defined by
the puzzle itself, and by what the exercise teaches the toolkit.

## Two deliverables, ranked

**1. The regression fixture (primary, not embargoed by anything).**

Jane Street publishes the warm-up at every stage of the flow. That makes an objective test:

```
warmup/04_final.gds  --extract-->  gate-level netlist  ==?  warmup/01_netlist.v
```

Ground truth is published, so pass/fail needs no judgement. This is worth more to
`klayout-tools` than the puzzle answer is, because it is a test that can live in CI forever
and catch regressions on a layout the toolkit did not produce.

**2. The puzzle answer (secondary, the fun part).**

Recover the netlist of `puzzle.gds`, determine the function, find inputs that drive `success`
high, then simulate the output-generator region to produce the answer string. Submissions
close **2026-09-04**.

## The staged plan

Each stage has a check that does not depend on the next stage being right.

| # | Stage | Done when |
|---|---|---|
| 1 | **Fetch + verify** upstream files | `scripts/fetch-puzzle.sh` passes its size and GDSII-magic checks |
| 2 | **Cell inventory** — instances, types, placement | `tools/inventory` counts reproduce the README table from the stream itself |
| 3 | **Pin geometry** for the 69 `sky130_fd_sc_hd` cells used | `tools/pins` resolves every cell's pins from the GDS stream's own label layers, none guessed (a PDK is an optional `--pdk-crosscheck`, never a dependency — see `tools/README.md`) |
| 4 | **Connectivity extraction** → gate-level Verilog | `tools/compare <extracted> puzzle/warmup/01_netlist.v` exits 0 — a 1:1 correspondence of every signal instance and net, seeded from the port names and independently re-verified (fill matched by count) |
| 5 | **Simulation** of the recovered netlist | warm-up reproduces `A + B == 496` behaviour |
| 6 | **Apply to `puzzle.gds`** | recovered netlist simulates against `example_inputs.vcd` and matches |
| 7 | **Solve** for `success` | 92-bit state; bounded model checking / SAT |
| 8 | **Answer** | output generator simulated with the solved inputs |

Stage 4 is the real work and the real product gap. Stages 1–3 are reconnaissance, and 2–3
are done: `tools/inventory` and `tools/pins` (see `tools/README.md`) reproduce the counts
below and every cell's pin geometry directly from the stream, no PDK required.

Stage 4's *judge* is already in place even though stage 4 is not: `tools/compare` decides
netlist equivalence up to instance and net renaming, seeded from the top-level port names,
and `./scripts/warmup-regression.sh` is the CI entry point that runs it. It self-tests
against a renamed copy of `01_netlist.v` and against three deliberate mutations, so it is
known to reject as well as accept before any extractor is pointed at it — see
[`evidence/warmup-regression.md`](../evidence/warmup-regression.md).

Stage 6 has run: the extraction flow was pointed at `puzzle.gds` and replayed against
`example_inputs.vcd`. The literal result is `RESULT FAIL` (strict exact-timestamp
comparison) but with zero value-content mismatches across the full trace — see
[`evidence/puzzle-replay.md`](../evidence/puzzle-replay.md) for the full record, including
the go/no-go decision to proceed to stage 7 with the timing discrepancy flagged as an open,
low-severity risk rather than a blocking one.

## What is known before solving

From the stream, without any reverse engineering (`tools/inventory`,
`evidence/inventory-puzzle.json`):

- 9,875 placed instances; 8,221 are `VIA_*` routing cells, 880 are tap/decap fill, 36 are
  unclassified `INTERNAL_*` bookkeeping cells (neither via nor library), leaving **738 logic
  and sequential cells**.
- **92 flip-flops**: 84 `dfrtp_2` (reset), 4 `dfstp_2` (set), 4 `dfxtp_2` (plain).
- 69 distinct `sky130_fd_sc_hd` cells, **names and drive strengths intact**, and (per
  `tools/pins`) every one of their pins' geometry too — see `tools/README.md`.
- Top cell `puzzle`, 200.0 × 352.7 µm, 14,638 polygons.
- Top-level ports: `I O[0] O[1] O[2] O[3] O[4] O[5] O[6] O[7] clk enable rst_n success` —
  matches `example_inputs.vcd`'s declared variables.

The 92-bit state is what sets stage 7's difficulty. The warm-up's 16 flip-flops implemented
two shift registers feeding a comparator against a constant; the same shape at this size is
a reasonable prior, and it is only a prior.

## Deliberate non-goals

- **Not a design canary.** Nothing here is taped out, and no tier is claimed. If a tier label
  ever appears in this repo it is a mistake.
- **Not a fork of the puzzle.** Upstream files stay upstream; see `CLAUDE.md` §3.
- **Not a `klt` workaround shop.** Gaps go upstream as issues (`CLAUDE.md` §2). A local
  shim that hides a toolkit defect defeats the purpose of the canary.
