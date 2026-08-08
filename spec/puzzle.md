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
| 2 | **Cell inventory** — instances, types, placement | counts reproduce the README table from the stream itself |
| 3 | **Pin geometry** for the 69 `sky130_fd_sc_hd` cells used | every cell's pins resolved from the PDK, none guessed |
| 4 | **Connectivity extraction** → gate-level Verilog | warm-up output matches `01_netlist.v` up to net renaming |
| 5 | **Simulation** of the recovered netlist | warm-up reproduces `A + B == 496` behaviour |
| 6 | **Apply to `puzzle.gds`** | recovered netlist simulates against `example_inputs.vcd` and matches |
| 7 | **Solve** for `success` | 92-bit state; bounded model checking / SAT |
| 8 | **Answer** | output generator simulated with the solved inputs |

Stage 4 is the real work and the real product gap. Stages 1–3 are reconnaissance that is
already partly done (see `README.md`).

## What is known before solving

From the stream, without any reverse engineering:

- 9,875 placed instances; 8,214 are via cells, 880 are tap/decap fill, leaving **~781 logic
  and sequential cells**.
- **92 flip-flops**: 84 `dfrtp_2` (reset), 4 `dfstp_2` (set), 4 `dfxtp_2` (plain).
- 69 distinct `sky130_fd_sc_hd` cells, **names and drive strengths intact**.
- Top cell `puzzle`, 200.0 × 352.7 µm, 14,638 polygons.

The 92-bit state is what sets stage 7's difficulty. The warm-up's 16 flip-flops implemented
two shift registers feeding a comparator against a constant; the same shape at this size is
a reasonable prior, and it is only a prior.

## Deliberate non-goals

- **Not a design canary.** Nothing here is taped out, and no tier is claimed. If a tier label
  ever appears in this repo it is a mistake.
- **Not a fork of the puzzle.** Upstream files stay upstream; see `CLAUDE.md` §3.
- **Not a `klt` workaround shop.** Gaps go upstream as issues (`CLAUDE.md` §2). A local
  shim that hides a toolkit defect defeats the purpose of the canary.
