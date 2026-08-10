# Easter egg hunt — brief for a squad room

## Why this exists

Jane Street's submission form has an optional short-answer field labelled **"Easter Eggs"**.
An author who asks the question expects there to be something to find. **Nobody in this repo
has looked** — `grep -ri easter` returns nothing.

This is optional and does not block submission. It is also free signal with **~3 weeks** to
the 2026-09-04 close, and the highest-value work left in this repo now that stages 1–8 are
closed and the independent review is in.

## Hard constraint, read first

This repo is **private until 2026-09-04** because Jane Street asks solvers not to post
spoilers or a writeup before submissions close. That is a commitment to a third party.

- **Nothing from this repo leaves it.** No public issue, PR, gist, or summary elsewhere.
- **Do not flip visibility.** Operator-only.
- Tool gaps found while hunting go to `klayout-tools` **described generically** — the gap,
  never the puzzle content (`CLAUDE.md` §2).
- Evidence is **append-only**. Add new files under `evidence/`; do not rewrite existing ones.

## What is already known

Read these before starting; they answer most first questions.

| File | What it gives you |
|---|---|
| `evidence/puzzle-solve.md` | the 121-bit input, the structural analysis, the state graph |
| `evidence/puzzle-answer.md` | the message `(* TWO STARS *)` and how it was decoded |
| `evidence/independent-review.md` | the coverage measurement and the refutation of claim 4 |
| `evidence/inventory-puzzle.json` | every placed instance with its cell type and **placement coordinates** |

Facts worth having in hand:

- Top cell `puzzle`, **200.0 × 352.7 µm**, 14,638 polygons, 9,875 placed instances.
- 738 logic/sequential cells; 8,221 `VIA_*`, 880 tap/decap fill, 36 `INTERNAL_*`.
- 92 flops: 84 `dfrtp_2` (reset), **4 `dfstp_2` (set)**, 4 `dfxtp_2` (plain, unresettable).
- The accepted word is one of **31,197,434** grids satisfying the stated placement rules — so
  the circuit enforces **additional constraints nobody has isolated**.
- **`net_00575`** is read by two gates (`a31oi_2_172770_89520`, `a311o_2_177370_89520`) and
  driven by nothing.

---

## Five independent leads — parallelise these

### Lead 1 — Look at the layout as a picture, not a circuit (strongest, untouched)

**Every tool in this repo treats the GDS as connectivity.** Nobody has rendered it. Classic
silicon easter eggs are *physical*: artwork in a metal layer, text in a fill region, a logo,
a signature. This is the single most likely place something is hiding and the cheapest to
check.

- Render `puzzle.gds` per layer and look at it. Metal layers, text layers, anything not
  carrying signal.
- Are there polygons on layers the extraction ignores? `klt extract`'s `ignored_layers`
  report already names met2–met5 and via2–via4 (see `2AMLogic/klayout-tools#666`) — that is
  a connectivity gap, but it also means **nobody has inspected those layers' geometry at
  all**.
- Look for structure in fill: 880 tap/decap cells and 36 `INTERNAL_*` bookkeeping cells.
  Fill is normally uniform. Is it?
- Placement coordinates are in `evidence/inventory-puzzle.json`. Plot them. Cells spelling
  text or forming an image would show up immediately.

### Lead 2 — The 120 cold cells in the `O[7:0]` cone

The review found **152 of 728 functional cells never toggle** under the recorded trace — 120
of them in the transitive cone of `O[7:0]`, 89 in the cone of `success`. Logic that drives
the output and never runs is a strong candidate for a second message.

- Reproduce the cold set: `.sim-work/independent-review/analyze.py` (venv at
  `.sim-work/review-venv`) already computes it. Get the **list**, not just the count — the
  review committed only the counts.
- Do the cold cells form a **connected subcircuit**, or are they scattered? A connected
  cluster in the `O` cone is an alternate output path.
- Use the existing BMC machinery (`tools/sim/bmc.py`, `solve.py`) with a different goal:
  instead of "`success` is high", ask **"cell X toggles"** or "`O[7:0]` takes a value never
  seen". If an input exists that lights up the cold cluster, decode what it emits with
  `tools/sim/answer.py`.

### Lead 3 — Other accepting inputs, and other messages

The review qualified uniqueness: it is the only **121-bit active word**, but longer windows
admit sequences differing in unused suffix bits.

- At longer bounds, do any *materially different* inputs assert `success`?
- Does any of them produce a **different message** on `O[7:0]`? Same decode path as stage 8.
- What does the chip emit when `success` is **not** asserted — is `O` silent, or does it say
  something on a failing input?

### Lead 4 — The constraints nobody has isolated

Claim 4 was refuted: the stated rules admit 31,197,434 grids and the circuit accepts one. So
there are further constraints, and **what they are is unknown**.

- Isolate them. Enumerate grids satisfying the known rules and test them against the cycle
  model to find which additional predicate cuts 31M to 1.
- This is writeup material regardless of whether it is an easter egg — right now the
  submission says "consistent with checking some of them", which is honest but thin.
- If the extra constraint is something cute (a shape, a word, a date), that *is* the egg.

### Lead 5 — The odd details already noticed and never explained

Each was recorded honestly and left open. Any could be deliberate.

- **`net_00575`** — read by two gates, driven by nothing. Trace it to the layout. Is it an
  extraction miss, or intentionally floating?
- **The 4 `dfstp_2` set flops** — why set rather than reset, when 84 others are reset? And
  the 4 unresettable `dfxtp_2` — why are they unresettable?
- **The timing offset that does not scale with combinational depth** — every transition is
  `+1000ps` regardless of gate depth (`evidence/puzzle-replay.md`). Unexplained.

---

## Deliverable

A new file `evidence/easter-eggs.md` recording:

1. **What was searched**, per lead, with the commands run and their literal output.
2. **What was found** — or a clear statement that a lead was searched and produced nothing.
   A negative result with its method stated is a real finding here; silence is not.
3. **Anything to put in the form's Easter Eggs field**, drafted.

Update `SUBMISSION.md`'s Easter Eggs row when there is something to say.

## Working notes

- Reproduce from a clean checkout: `./scripts/fetch-puzzle.sh`, plus `pip install python-sat`
  for anything using the solver.
- `CLAUDE.md` §5 applies: state what was executed, never a result recharacterised as passing.
- Prefer measuring to remembering — the cell-truth-table approach in
  `tools/sim/celltable.py` is the house style, and it exists because a remembered gate
  function is an invisible error.
- **Lead 1 needs no solver and no deep tooling.** If the room is splitting work, start it
  first and in parallel with everything else.
