# Independent review request — before submission

**You are an independent reviewer. Your job is to try to break this result, not to confirm
it.** A confirmation you did not earn is worth nothing here; a single real defect you find is
worth the whole review. Assume the work is wrong until a check you ran yourself says
otherwise.

This repo claims to have reverse-engineered Jane Street's 2026 ASIC puzzle end to end. The
submission is **one shot** — a Google Form, closing **2026-09-04**, with no revision after
sending. That asymmetry is why this review exists.

---

## Hard constraint, read first

This repository is **private until 2026-09-04**, because Jane Street asks solvers not to post
spoilers or a writeup before submissions close. That is a commitment to a third party.

- **Do not post any content from this repo anywhere.** Not in a public issue or PR, not on
  another repo's tracker, not in a gist, not in a summary shared outside this workspace.
- **Do not make this repo public.** Visibility is operator-only.
- If you find a defect in `klayout-tools` while reviewing, describe it **generically** — the
  tool gap, never the puzzle content. See `CLAUDE.md` §2.

Your review output belongs in this repo (a new file under `evidence/`, or a comment on a new
issue **in this repo**). Nowhere else.

---

## The claims under review

Each is stated as this repo states it. Your task is to falsify each, or to say precisely what
you checked and what would still have escaped you.

| # | Claim | Recorded in |
|---|---|---|
| 1 | `tools/extract` recovers a gate-level netlist from `puzzle.gds` that is functionally faithful | `evidence/puzzle-replay.md` |
| 2 | A specific **121-bit** input sequence on `I` drives `success` high | `evidence/puzzle-solve.md` §5 |
| 3 | That sequence is **unique at the bound** — blocking it yields UNSAT | `evidence/puzzle-solve.md` §6 |
| 4 | The design is a **non-attacking placement validator** on an 11-wide raster (2 marks/row, 2/column, no two touching) | `evidence/puzzle-solve.md` §5 |
| 5 | The answer message is **`(* TWO STARS *)`**, 15 printable ASCII bytes on `O[7:0]` | `evidence/puzzle-answer.md` §3 |

---

## Where to attack — ranked by what would actually cost us the contest

### 1. Extraction fidelity, verified by a 24-transition trace (highest risk)

The **only** oracle for `puzzle.gds` is `puzzle/example_inputs.vcd`. There is no published
ground-truth netlist for the real puzzle (unlike the warm-up), so the structural comparator
cannot check it at all. That oracle is **22 transitions on `O` plus 2 on `success` = 24
total**, against a design with **92 flip-flops and 636 combinational gates**.

Zero value mismatches across 24 transitions is real evidence. It is not broad coverage.

- Which of the 738 logic/sequential cells **never toggle** during the replay? A cell the only
  oracle never exercised is a cell whose extraction is unverified. This is derivable from the
  existing simulated VCD (`.sim-work/replay/sim_out.vcd`) plus the netlist — no new tooling.
- Does any *unexercised* logic sit on the path to `success` or to `O[7:0]`? That is the
  intersection that would actually change the answer.
- If extraction dropped or mis-wired a connection in cold logic, would anything in this repo
  have caught it? If the honest answer is no, say so plainly — that is the review's most
  valuable output.

### 2. `net_00575` — read by two gates, driven by nothing

`evidence/puzzle-solve.md` §6 records an undriven net read by logic. The solve is shown to be
robust to it (free variable, and both polarities replay to `success`), which is the right
check. But **why it exists is unexplained.**

- Is it an extraction defect (a connection `tools/extract` missed), or is it genuinely
  undriven in the GDS?
- Trace it back to the layout. If extraction dropped a driver, that is a bug in the very tool
  whose output every other claim rests on — and its being harmless *here* says nothing about
  elsewhere.

### 3. The uniqueness claim, and its bound

"Unique" is claimed **at the bound** (121 active cycles). Check what that does and does not
exclude.

- Could a **longer** sequence also drive `success`? If so, is "unique" the right word in a
  submission, or does it need qualifying?
- Was the reset/idle/active window shape the right model of the device? An off-by-one in the
  scenario would make both the answer and the uniqueness proof internally consistent and
  jointly wrong.
- The 4 unresettable `dfxtp_2` flops were left free, and the answer replays under all 16
  power-up combinations. Confirm that yourself rather than accepting it.

### 4. Bit order and message boundary

`evidence/puzzle-answer.md` §2 says the byte order was **checked, not assumed** — both
candidate orders were decoded and one produced 15/35 printable versus 5/35.

- Is "more printable" a sound selection criterion, or could the other order be correct and the
  message non-ASCII?
- The message is 15 bytes; the puzzle hint mentioned "nine printable ASCII characters", and
  §4 explains the 9-byte reading as a truncation artifact of a short observation tail. Does
  that explanation hold, or is 9 the intended answer and 15 an artifact in the other
  direction?
- `(* TWO STARS *)` is coherent with claim 4 — two marks per row and column. Satisfying
  coherence is *weak* evidence; it is exactly what a plausible-but-wrong decode would also
  produce. Do not let it substitute for a check.

### 5. Two anomalies the evidence itself flags and does not explain

Both are recorded honestly and left open. Either could be a symptom.

- **The timing offset does not scale with combinational depth.** Every non-anomalous
  transition is `+1000ps`, exactly one `UNIT_DELAY` quantum — but `success` (a bare `dfrtp_2`
  Q output, zero gates) and `O[0]`/`O[7]` (driven through `and3_2` plus upstream logic) show
  the *same* offset. Under a real gate-delay model they should differ. Why don't they?
- **A CNF clause count differs by one** between `evidence/puzzle-solve.md` and
  `evidence/puzzle-answer.md` §5. Noted as minor. Is it?

---

## How to review

**Re-run rather than read.** Every claim in `evidence/` carries the command that produced it.
Execute them against a clean checkout (`./scripts/fetch-puzzle.sh`, plus `pip install
python-sat`). A claim you only read is a claim you have not checked.

**Prefer independent derivation to agreement.** Where you can compute something a second way
— decode the message with your own script, re-derive the input sequence, check the grid
constraints by hand against the raster — do that instead of confirming this repo's arithmetic.

**Report what you could not check.** The most useful sentence you can write is "X is
unverified and here is what would verify it." Silence on a gap reads as coverage.

**Do not soften a failure.** If a check fails, report the literal result. This repo's own
convention (`CLAUDE.md` §5) is to state what was executed rather than a result
recharacterised as passing — stage 6 records a literal `RESULT FAIL` alongside its
explanation, and that is the standard to hold this review to as well.

## Deliverable

A file `evidence/independent-review.md` containing:

1. **Verdict per claim** (1–5 above): confirmed / refuted / unverifiable-and-why.
2. **Commands you ran**, with their literal output.
3. **Anything you could not check**, and what would be needed.
4. **A submission recommendation**: send as-is, send with specific wording changes, or hold.

Do not edit the existing `evidence/` files — this repo's convention is append-only, and your
review is independent evidence, not a revision of theirs.
