# Submission record — Jane Street ASIC puzzle

**Form:** https://docs.google.com/forms/d/e/1FAIpQLScNCnfZ1wC4HbARwynUZ25EKZyqJIzXM_5H5aHom-QeAhE6FA/viewform
**Closes:** 2026-09-04 · **Questions:** asic-puzzle@janestreet.com
**Header text:** *"Cracked the chip? Submit your answer below, along with a writeup of how you
did it."*

**Submitted:** 2026-08-10 at approximately 17:03 PDT. Robb Walters reported the Google
Form submission complete. The Chrome debugging page was no longer available afterward, so
this records the operator report rather than an independently captured confirmation page.
The field contents below are the reviewed text staged immediately before submission.

---

## Pre-submission decisions

**1. The form does not state that responses can be edited after submission.**
Google Forms only allows editing when the creator enables it, and this one does not say so.
Treat submission as final. That is the argument for completing `REVIEW-REQUEST.md` first —
the review is cheap (25 days remain, nothing is gated on it) and its whole value is catching
something before the one irreversible step.

**2. The writeup field offers "an optional link to a longer document" — and we cannot use it
yet.** This repo goes public on 2026-09-04, which *is* the submission deadline. Any link to
it included at submission time would point at a private repo. Options, in preference order:

- Submit the self-contained writeup below with no link, then email `asic-puzzle@janestreet.com`
  after 2026-09-04 with the repo URL — which is exactly the follow-up Jane Street invites
  ("If you do publish your solution … after submissions are closed, email us and we may
  include the link in our follow-up post!").
- Or publish the evidence trail elsewhere on 2026-09-04 and email that.

Either way the writeup below must stand alone.

**3. The Easter eggs have been investigated and found — the message set is now enumerated,
not sampled.** The chip's complete output behavior is proven by BMC over all failing inputs
(`evidence/easter-egg-try-again-universality.py`): all-zeros emits `EMPTY SKY`, all-ones
emits `BIG BANG`, a word satisfying every row/column/region count that violates only the
adjacency rule emits a fifth, previously unknown diagnostic — **`TWO"NOT TOUCH`**, the `"` a
ditto mark for STARS — and every other failing word emits `TRY AGAIN` (exactly two failure
streams exist; exhaustive enumeration, all 16 power-up combinations). Physical GDS layer
200/0 encodes `PER ARENAM AD ASTRA` ("through sand, to the stars") in Morse code below the
die, built from the 36 `INTERNAL_*` placements, and met2 carries an ~18 µm three-ring
maze/record glyph connected to nothing. Structural differential analysis also recovers the
11 irregular Star Battle regions omitted from the initial semantic description; adding
exactly two stars per recovered region makes the accepted grid independently unique. Full
commands, literal output, and reproducible scripts are in `evidence/easter-eggs.md`.

---

## Fields the operator must supply

The form requires identity details no agent should invent:

| Field | Required | Value |
|---|---|---|
| Full Name | yes | *(operator)* |
| Email | yes | *(operator)* |
| Academic or professional status | yes | High school student / University student / PhD Candidate / Professional / **Other** — 2AM Logic is a company, so "Professional" or "Other" |
| Affiliation | yes | *(operator — "2AM Logic"?)* |
| Country | yes | *(operator — used for the mailing address for swag)* |
| Agree to publishing your name and solution if selected? | yes | *(operator decision)* |
| Interested in exploring careers at Jane Street? | optional | *(operator — LinkedIn or personal page)* |
| Comments | optional | *(operator)* |
| Easter Eggs | optional | Use the draft in `evidence/easter-eggs.md` ("Deliverable" section): `EMPTY SKY` / `BIG BANG` / `TRY AGAIN` / `TWO"NOT TOUCH` failure messages (the complete set, proven by exhaustive BMC — the fifth fires iff only the adjacency rule is violated), the Morse `PER ARENAM AD ASTRA` strip on layer 200/0, the met2 three-ring maze/record glyph, and the 11 recovered Star Battle regions that make the answer unique. |

---

## The answer

```
(* TWO STARS *)
```

15 printable ASCII bytes, emitted one byte per clock cycle on `O[7:0]` after `success`
asserts. Recorded in `evidence/puzzle-answer.md`.

---

## Writeup (draft — paste into the "Writeup" field)

We recovered the netlist mechanically and solved it with a SAT solver; no step relied on
guessing what the circuit was.

**Extraction.** `puzzle.gds` ships with `sky130_fd_sc_hd` cell names and drive strengths
intact, so the work was connectivity rather than cell recognition. We built a cell-level
extractor that resolves each instance's pin geometry from the GDS stream's own label layers
and traces nets through the routing stack. We validated it against the published warm-up,
where ground truth exists: extracted netlist versus `01_netlist.v`, compared up to instance
and net renaming, seeded from the top-level port names. That comparator self-tests against a
renamed copy and against three deliberate mutations, so it was known to reject before it was
ever trusted to accept.

**Checking the extraction on the real chip.** There is no ground-truth netlist for
`puzzle.gds`, so the only oracle is `example_inputs.vcd`. Replaying it against our extracted
netlist reproduces every recorded output transition's value exactly — 22 transitions on
`O[7:0]` and 2 on `success`, zero value mismatches. The traces differ only in timing: apart
from one functionally inert pre-reset `x`-settling transition 4 ns early, every transition is
offset by exactly one `UNIT_DELAY` quantum (+1 ns, the sky130 primitive timescale), consistent
with a gate-level simulation compared against a near-zero-delay reference. We
report that run as a literal FAIL under our exact-timestamp comparator rather than loosening
the comparison, and characterise the offset separately.

We want to be precise about what that establishes, because it is less than it looks. That
trace has low internal coverage: across its 312 rising edges, **152 of 728 functional cells
never toggle** — including 120 in the transitive cone of `O[7:0]` and 89 in the cone of
`success`. An extraction error in cold logic would not have been caught by this replay. Our
extraction is reproducible and agrees with the warm-up's published ground truth; on the
puzzle itself it is corroborated, not proven.

**Structure before solving.** We collapsed the combinational logic and looked at the state
graph — an edge from flop X to flop Y when X's output is in the fan-in cone of Y's D pin.
The warm-up decomposes into two independent 8-stage shift registers feeding one comparator.
The puzzle does not decompose at all: all 92 flops sit in one connected component, with
feedback groups of 9, 8 and 4 flops plus 23 two-flop pairs, a 12-stage shift register fed
by `I`, and two sinks reading 57 of the 92 flops. That ruled out inverting it by construction and told us to use a
solver.

**Solving.** We measured the truth table of all 63 combinational cell types by simulating
the real sky130 behavioural models, rather than writing them from memory, and built a cycle
model from that. Bounded model checking over the full 92-flop state (no state reduction, no
assumed structure) found a 121-bit input sequence on `I` that drives `success` high. We
replayed that sequence through Icarus against the extracted netlist itself — not just the SAT
encoding — and it asserts `success`. Re-solving with that solution blocked returns UNSAT, so
it is the only **121-bit active word** that works: longer windows admit further sequences that
differ only in unused suffix bits, so the uniqueness is at that bound rather than absolute.
The four unresettable flops were left as free variables throughout, and the answer holds under
all 16 power-up combinations.

**What the chip is doing.** One-hot differential traces make the counter roles legible: 11
two-flop counters receive one complete column each, another 11 receive disjoint irregular
regions that partition the 11×11 raster, and one two-flop counter is reused across rows. An
8-flop group counts the total population of `I`, while a 12-stage shift register reads offsets
1 and 11±1 — the neighbours of the current cell in raster order. The accepted word has
exactly two marks per row, column, and region, with no two marks adjacent even diagonally.

Those conditions alone do not pin the answer down: enumerated independently — 11×11, two
marks per row, two per column, minimum Chebyshev distance 2 — they admit **31,197,434**
valid grids, while the circuit accepts exactly **one** word at our bound. The missing
predicate turned out to be recoverable from the circuit itself: the region counters above
are exactly it — the puzzle is a standard **two-star Star Battle** whose region map was
withheld. As an independent check
we encoded only the recovered rules (two marks per row, column, and recovered region; no
touching) as a fresh CNF with no reference to the gate-level circuit: it has exactly one
solution, and it is the accepted word.

**Answer.** Extending the simulation past the goal cycle and watching `O[7:0]` yields 15
printable ASCII bytes: `(* TWO STARS *)`. We decoded both candidate bit orders and selected
on printability, with the decoder unit-tested against a synthetic known-answer fixture first,
and checked that the observation window was long enough that the message was not truncated —
a short window returns 9 bytes mid-word, which we reproduced deliberately rather than
assumed.

Tools: our own extractor and cycle model (built for this), Icarus Verilog with the real
sky130 behavioural models, and CaDiCaL via python-sat. Every claim above is backed by a
recorded command and its literal output.

---

## After submitting

- [x] Submit the reviewed answer, writeup, and Easter Eggs response (operator-reported
      complete 2026-08-10).
- [ ] 2026-09-04: flip this repo public (operator-only).
- [ ] Email `asic-puzzle@janestreet.com` with the repo link — the follow-up post invitation.
- [ ] Return `fleet_priority` to the canary band (44 is free); `repos.yml` warns that leaving
      it at 5 starves the orchestrator for a finished contest.
