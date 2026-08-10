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

### How submission actually works

Read off Jane Street's post on 2026-08-10, because the deadline and the deliverable were
recorded here from the start but the *mechanism* was not — and a deliverable with no
recorded route to the recipient is how a finished solve gets missed.

- **No registration, sign-up, or entry step.** Nothing has to happen before the answer is
  ready. There is no earlier deadline hiding behind the 2026-09-04 one.
- **Submission is a Google Form**, linked from the post:
  `https://docs.google.com/forms/d/e/1FAIpQLScNCnfZ1wC4HbARwynUZ25EKZyqJIzXM_5H5aHom-QeAhE6FA/viewform`
- **What it wants:** the answer string **plus a brief description of how you did it** —
  *"submit your answer … along with a brief description of how you did it."* The writeup is
  part of the submission, not an optional extra, so stage 8 produces two artifacts rather
  than one.
- **Questions:** `asic-puzzle@janestreet.com`.
- **After submissions close**, publishing is welcomed and there is an action attached to it:
  *"If you do publish your solution (on a personal blog or repository) after submissions are
  closed, email us and we may include the link in our follow-up post!"* — so flipping this
  repo public on 2026-09-04 has a follow-up step, not just a visibility change.
- **Recognition:** *"We'll feature the most interesting writeups and techniques in a
  follow-up post, and send swag for our favorite solutions."* Note "techniques" — the
  toolkit story this repo exists to produce (deliverable 1) is the kind of thing being asked
  for, which makes the two deliverables less separate than the ranking above implies.

Verified against the source post rather than inferred; re-check before submitting in case
the terms change.

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

## Prior art

**Nohl, Evans, Starbug & Plötz, ["Reverse-Engineering a Cryptographic RFID
Tag"](https://www.usenix.org/legacy/events/sec08/tech/full_papers/nohl/nohl.pdf), USENIX
Security 2008** — the Mifare Classic / Crypto-1 recovery. The classic of this genre, and
worth citing in the stage-8 writeup for what it shares and what it does not.

*Shared:* the core method. Recover the sequential structure first, separate the **feedback**
path from the **output/filter** path, then name the taps — and read the function off that
skeleton rather than off the gate soup. `tools/sim/structure.py` arrived at the same
approach independently: collapse the combinational logic, report the state graph, find the
strongly-connected components and the shift chains, then read the taps.

*Not shared:* their hard part was **imaging** — recovering a netlist from die photographs,
recognising standard cells by appearance. Jane Street ships GDS with cell names and drive
strengths intact, so that entire stage is a gift here, and the difficulty moves downstream
to connectivity extraction (stage 4) instead.

*Also not shared:* Crypto-1 is a cipher — a 48-bit LFSR with a nonlinear filter reading a
subset of its taps. This design is **not cryptographic**. The tell is in the same skeleton:
its feedback groups are 2-flop saturating counters rather than one long register with XOR
taps, and 29 `xnor2_2` across 636 combinational gates is far too few for LFSR feedback at
this scale. What looks from a distance like absorb-mix-compare is really
count-per-row/column-and-check-adjacency (see `evidence/puzzle-solve.md` §5).

Recorded because "serial input + feedback + wide comparison" reads as a keystream generator
to an experienced eye, and it is worth having written down both why that reading is
reasonable and what distinguishes this from it.

## Deliberate non-goals

- **Not a design canary.** Nothing here is taped out, and no tier is claimed. If a tier label
  ever appears in this repo it is a mistake.
- **Not a fork of the puzzle.** Upstream files stay upstream; see `CLAUDE.md` §3.
- **Not a `klt` workaround shop.** Gaps go upstream as issues (`CLAUDE.md` §2). A local
  shim that hides a toolkit defect defeats the purpose of the canary.
