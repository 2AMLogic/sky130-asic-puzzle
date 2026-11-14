# Roadmap

`sky130-asic-puzzle` points [`klayout-tools`](https://github.com/2AMLogic/klayout-tools)
(`klt`) at a sky130 standard-cell layout that another flow produced, with published ground
truth, so the toolkit is tested on something it did not build itself.

Status as of 2026-11-14, `main` @ `80c19dd`.

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

**Upstream findings.** Nine toolkit gaps have been filed from this repo
(`evidence/upstream.md:10-18`): klayout-tools #619, #620, #673, #674, #675, #3748, #3749,
#5631 and #5632. The first seven read as closed on the upstream tracker today; **#5631 and
#5632 are open**, both filed from here for #74, and both are `klt lvs` findings — so the
`02` comparison and cheap `--check` re-verification are blocked upstream rather than here.
Four have been re-verified against a `klt` that contains the fix: #619 and #620 by
`evidence/klt-extract.md`, #3748 and #3749 by Run 2 above. The remaining three — #673, #674
and #675 — are closed upstream but unconfirmed from this side, which is the main thing left
to do (scoped under "Next").

**Tracker.** Open issues: #75, #76 and #77 are this roadmap's own Now items, filed and
curated with point estimates; #78 is a Hermit dead-code proposal parked on an operator
decision; #30 is an automated merge-hold digest, not work. Four pull requests are open at
this snapshot (#73, #82, #86, #87), all in normal review flow. `WORK_PLAN.md` is
machine-generated and lags these filings.

## Now

Each of these can start today and fits one pull request. All three are filed and curated:
#75, #76 and #77. The 2026-11-13 list opened with a fourth item — re-running the warm-up
`klt lvs` on a build carrying the #3748/#3749 fixes — which was filed as #74 and merged as
PR #81; it is recorded under "Where it stands" above, not here.

1. **Bring the README's "capability gap" section up to date** (#75). It still says
   `klt extract` is device-level only and presents #619 and #620 as open gaps, while CI runs
   `klt extract --abstract-cells` on both layouts. It also cites `sky130-modexp#8` as an
   open seam (that issue is closed) and describes `scripts/` as "fetch + embargo check".
   Done when: the section states the gap as closed with links to `evidence/klt-extract.md`
   and `evidence/upstream.md`, the `scripts/` line lists the regression scripts, and the
   original wording is kept as history in the same way the lifted embargo section is.

2. **Run `klt lvs` on `puzzle.gds` against `evidence/puzzle-extracted.v`** (#76). This is
   scope item 3 of #47, recorded as "Not done" in `evidence/warmup-klt-lvs.md`. It is
   self-consistency, not ground truth, but it is the only place `klt lvs` meets a
   third-party layout of this size (728 signal cells).
   Done when: a recorded run is appended to an evidence file with the command, `klt`
   version, verdict and counts, the envelope is committed with reference-side names handled
   as the warm-up envelopes are, and any tool-side finding is filed upstream.
   Needs: a sky130 PDK on the machine that runs it (the script hard-fails without one).

3. **Check the featured writeups against our record** (#77). The README says of the 15
   writeups in Jane Street's results post: "We have not checked these writeups against our
   record yet."
   Done when: `evidence/easter-eggs.md` has a dated addendum listing, per writeup, anything
   that contradicts or adds to our record, each point reproduced here before it is written
   down (`CLAUDE.md` §5), unreachable links are named as such, and the README sentence is
   replaced by a pointer to the addendum.

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
- **Bump the `klt` pin when a release follows 0.9.1.** 0.9.1 is the newest published
  release today, so there is nothing to bump yet. Done when CI is green on the new pin
  and `evidence/klt-extract.md` has a run entry for it; a regression on these layouts is
  an upstream issue, not a local fix (`CLAUDE.md` §2).

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
else is. Nothing waits on an upstream release, but the `02` comparison and cheap `--check`
cannot be resolved from this side while klayout-tools#5632 and #5631 are open. Now 2 needs
a sky130 PDK on the worker; Run 1 and Run 2 both found one under `~/.ciel` on a dispatch
worker, so this is an environment requirement and not a block.

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
