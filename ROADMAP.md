# Roadmap

`sky130-asic-puzzle` points [`klayout-tools`](https://github.com/2AMLogic/klayout-tools)
(`klt`) at a sky130 standard-cell layout that another flow produced, with published ground
truth, so the toolkit is tested on something it did not build itself.

Status as of 2026-11-15, `main` @ `ddcc198`.

## Where it stands

The puzzle itself is closed out; the repository's remaining job is the regression it
gives the toolkit (`CLAUDE.md` §4).

**The solve (done, not reopened).** All eight stages of `spec/puzzle.md` are complete
(#1 to #5, #9, #14 to #16 closed). The answer was submitted on 2026-08-10 (`SUBMISSION.md`,
`evidence/puzzle-solve.md`, `evidence/puzzle-answer.md`) and confirmed by Jane Street's
results post of 2026-10-02; the reconciliation is the 2026-10-02 addendum in
`evidence/easter-eggs.md`, and the lessons are in `NOTES-FOR-NEXT-TIME.md`.

**The regression (live in CI, `.github/workflows/ci.yml`).**

| Check | Evidence | State |
|---|---|---|
| Warm-up `04_final.gds` to gate-level netlist with `tools/extract`, equivalent to the published `01_netlist.v` | `scripts/warmup-regression.sh`, `evidence/warmup-regression.md` | in CI |
| Same layout through `klt extract --abstract-cells`, equivalent to `01_netlist.v`, with a mutation check | `evidence/klt-extract.md` Run 2; `--require-klt` (#63, PR #64) | in CI, `klayout-tools==0.9.1` pinned |
| `puzzle.gds` through both extractors, equivalent to `evidence/puzzle-extracted.v`, exactly one floating net | `scripts/puzzle-regression.sh`, `evidence/klt-extract.md` Run 3 (#68, PR #69) | in CI |
| No upstream puzzle file tracked (`CLAUDE.md` §3) | `scripts/check-embargo.sh` | in CI |
| `klt lvs` of the warm-up against `01_netlist.v` (signal-only) | `evidence/warmup-klt-lvs.md` Run 1 and Run 2, `evidence/warmup-klt-lvs-01.json` | **match** in both, run by hand on 2026-10-17 and 2026-11-14, not in CI |
| `klt lvs` of the warm-up against `02_netlist_with_power_rails.v` | same file, `evidence/warmup-klt-lvs-02.json` | **mismatch** in both runs, tool-side; 243 mismatches (242 errors) on `klt 0.9.2.dev1022` against Run 1's 159 — open upstream as klayout-tools#5632 |
| `klt lvs` of `puzzle.gds` against this repo's own `evidence/puzzle-extracted.v` | `evidence/puzzle-klt-lvs.md` Run 1 | recorded 2026-11-14, not in CI; the compare refused the reference's port spelling (klayout-tools#5693, open) — the isolating probe, differing in spelling alone, **match** |

**The warm-up `klt lvs` re-run on the fixed build (done, #74, PR #81).** Run 2 of
`evidence/warmup-klt-lvs.md` (2026-11-14, `klt 0.9.2.dev1022+g2a9c52b27ce7`, klayout
0.30.13) re-ran both references on a build carrying the fixes for klayout-tools #3748 and
#3749. `01` still matches; `02` still mismatches, and mismatches harder (243 against Run
1's 159), because `--abstract-cell-lef` restores the `VNB` pin but leaves it bound to the
deck's synthesized `vsubs` global, which no abstracted cell ties to the ground rail. The
two fixes are in practice mutually exclusive — filed as klayout-tools#5632 — and the
nested-clone `--check` failure found in the same run is klayout-tools#5631. Run 2 also
retracts two Run 1 attributions (`evidence/upstream.md:15-16`): the #3748 fix was
message-only, since `reference.pdk` already existed and no `export PDK=sky130A` workaround
is involved, and the `02` mismatch is not the dropped `VNB` pin.

**The 2026-11-13 "Now" list is done.** #75 (PR #103) updated the README's capability-gap
section: it now states the gap as closed upstream and keeps the original wording as
history. #76 (PR #90) recorded the puzzle-scale `klt lvs` run
(`evidence/puzzle-klt-lvs.md`, 2026-11-14, `klt 0.9.2.dev1025`, PDK `sky130A`): the
extraction succeeded — 1,618 abstracted instances over 69 cell types, agreeing with the
reference's own instance count — but the compare refused the committed reference, whose
bit-blasted escaped port names trip the reference reader (klayout-tools#5693). The
isolating probe, differing in port spelling alone, returned **match** with
`power_connectivity: match` and zero errors, so the self-consistency check the item asked
for landed, one reference spelling short of a clean run. #77 (PR #99) checked Jane
Street's 15 featured writeups against our record one by one: the dated amendment is in
`evidence/easter-eggs.md` and the README sentence now points to it.

**Upstream findings.** Ten toolkit gaps have been filed from this repo
(`evidence/upstream.md:10-19`): klayout-tools #619, #620, #673, #674, #675, #3748, #3749,
#5631, #5632 and #5693. The first seven read as closed on the upstream tracker today;
**#5631, #5632 and #5693 are open** — the two `klt lvs` findings from #74 and the
port-name reader defect the puzzle-scale run filed for #76 — so the `02` comparison, the
cheap `--check` re-verification and a clean re-run of the puzzle compare are blocked
upstream rather than here. Four have been re-verified against a `klt` that contains the
fix: #619 and #620 by `evidence/klt-extract.md`, #3748 and #3749 by Run 2 above. The
remaining three — #673, #674 and #675 — are closed upstream but unconfirmed from this
side, which is the main thing left to do (scoped under "Next").

**Tracker.** The open issues bearing on this roadmap are #78, a Hermit dead-code proposal
parked on an operator decision, and #30, an automated merge-hold digest that is not work.
The five issues this roadmap had curated — #75, #76 and #77, plus the Hermit refactors
#83 and #85 — are all closed, as are their pull requests. Seven pull requests are open as
this is written (this one; the sharing refactors #101, #104, #107 and #111; the
puzzle-lvs fail-soft fix #109; the docs-maintenance update #110), all in normal review
flow. `WORK_PLAN.md` is machine-generated and lags these filings.

## Now

Nothing is queued. The three items this section carried on 2026-11-13 are done and
recorded under "Where it stands" (#75 as PR #103, #76 as PR #90, #77 as PR #99); the
fourth item the list opened with was #74, merged as PR #81 the same day. No new item has
been curated yet — the two open issues (#78, #30) are parked, not work. New items are
filed as issues, curated with a point estimate, and then listed here.

## Next

- **Put the LVS result under CI.** Run 2 already answered the question this item used to
  open with, and the answer was no: cheap `klt lvs --check
  evidence/warmup-klt-lvs-01.json` does **not** exit 0 on a runner, and not for want of a
  PDK — `puzzle/` is a nested clone, so the envelope records the reference path relative to
  the inner repo while `--check` resolves it against this one (klayout-tools#5631, open;
  `evidence/warmup-klt-lvs.md:17-34`). The open question is therefore which way around it:
  wait for #5631, re-record the envelopes with the reference outside `puzzle/` (the shape
  Run 2's probe showed re-runs clean, exit 0 / `status: match`), or gate a full
  PDK-bearing run on a self-hosted runner. Done when CI runs a `klt lvs` check, or
  `evidence/warmup-klt-lvs.md` records which option was taken and why.
- **Pin the `02` power-rail comparison as an expected mismatch, not an expected match.**
  The earlier framing assumed Run 1's mismatch was the dropped `VNB` pin and would clear on
  a fixed build. Run 2 refuted that, and upstream has already **rejected** modelling tap
  continuity in abstract extraction (klayout-tools#4363's `_GROUND_SUBSTRATE_CAVEAT`,
  `evidence/warmup-klt-lvs.md:256`), so `match` is not reachable from this side while
  klayout-tools#5632 is open. Done when `scripts/warmup-klt-lvs.sh` exits nonzero if `01`
  stops matching **or** `02`'s recorded counts move, replacing today's "exit 0 means the
  runs completed" contract. Promotion to an expected match is reconsidered only if #5632
  is fixed.
- **Confirm klayout-tools #673, #674 and #675 from this side.** Each was found during the
  physical-layout inspection and worked around with a local script under `evidence/`.
  Done when `evidence/upstream.md` has a row per issue recording the `klt` command that now
  does the job on `puzzle.gds`, the version used, and whether its result agrees with the
  local script's. Sized as one PR per issue once the first shows the pattern.
- **Bump the `klt` pin to 0.9.2.** The trigger has fired: v0.9.2 was tagged 2026-11-14 and
  is the newest published release, while CI still pins `klayout-tools==0.9.1`
  (`.github/workflows/ci.yml:71`). Done when CI is green on the new pin and
  `evidence/klt-extract.md` has a run entry for it; a regression on these layouts is an
  upstream issue, not a local fix (`CLAUDE.md` §2).

## Later

- **A second third-party layout.** One design from one flow is a narrow sample. Question
  first: is there another published layout with ground truth at every stage and a licence
  or fetch arrangement that satisfies `CLAUDE.md` §3?
- **Retire `tools/extract` as the reference extractor.** It exists because `klt` could not
  do cell-level extraction. Question first: does keeping an independent second extractor
  still catch anything the published warm-up netlist does not, now that both agree?
- **Reuse the Easter-egg checklist.** `NOTES-FOR-NEXT-TIME.md` turns the misses into a
  procedure. Question first: does it belong here as a script over a fetched file set, or in
  the next puzzle's own repository?

## Blocked and waiting

#78 (Hermit: dead code in `tools/sim/solve.py`) is parked on an operator decision; nothing
else is. Nothing waits on an upstream release, but the `02` comparison, the cheap
`--check` re-verification and a clean re-run of the puzzle compare cannot be resolved from
this side while klayout-tools#5632, #5631 and #5693 are open.

## Not planned

- **No evidence ladder.** `spec/puzzle.md` is explicit that this is not a design canary and
  claims no tier.
- **No resubmission and no supplement email.** The draft in `SUBMISSION.md` was never sent
  and should not be sent as written (README, "What the other solutions taught us").
- **No vendoring of the puzzle files** and no fragments of them in documentation
  (`CLAUDE.md` §3).
- **No local workaround for a `klt` defect.** Gaps go upstream (`CLAUDE.md` §2).
- **The next Jane Street entry** is built in
  [`2AMLogic/sg13cmos5l-protocol-emulator`](https://github.com/2AMLogic/sg13cmos5l-protocol-emulator),
  not here.
