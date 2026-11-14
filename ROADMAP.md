# Roadmap

`sky130-asic-puzzle` points [`klayout-tools`](https://github.com/2AMLogic/klayout-tools)
(`klt`) at a sky130 standard-cell layout that another flow produced, with published ground
truth, so the toolkit is tested on something it did not build itself.

Status as of 2026-11-13, `main` @ `1a768ae`.

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
| `klt lvs` of the warm-up against `01_netlist.v` (signal-only) | `evidence/warmup-klt-lvs.md` Run 1, `evidence/warmup-klt-lvs-01.json` | **match**, run once by hand on 2026-10-17, not in CI |
| `klt lvs` of the warm-up against `02_netlist_with_power_rails.v` | same file, `evidence/warmup-klt-lvs-02.json` | **mismatch**, tool-side, recorded with `klt 0.7.1.dev1743` |

**Upstream findings.** Seven toolkit gaps were filed from this repo
(`evidence/upstream.md`): klayout-tools #619, #620, #673, #674, #675, #3748 and #3749. All
seven read as closed on the upstream tracker today. Only #619 and #620 have been
re-verified here against a `klt` that contains the fix (`evidence/klt-extract.md`). The
other five are closed upstream but unconfirmed from this side, which is the main thing left
to do.

**Tracker.** No open pull requests. The one open issue, #30, is an automated merge-hold
digest, not work. The machine-generated `WORK_PLAN.md` lists nothing ready, so before this roadmap the repository
had no dispatchable work.

## Now

Each of these can start today and fits one pull request. None has an issue yet.

1. **Re-run the warm-up `klt lvs` on a `klt` that contains the fixes for klayout-tools
   #3748 and #3749.** The recorded mismatch against `02_netlist_with_power_rails.v` was
   attributed to the dropped `VNB` pin (#3749), and the run needed `export PDK=sky130A`
   because `klt lvs` could not select the PDK variant (#3748).
   Done when: `evidence/warmup-klt-lvs.md` has an appended Run 2 naming the `klt` version
   and commit, the `02` verdict and its `power_connectivity` status, and whether the `PDK`
   export is still needed; `scripts/warmup-klt-lvs.sh` and both envelopes are updated to
   match; and a remaining mismatch on a build that contains the fix is filed upstream,
   toolkit-first, and added to `evidence/upstream.md`.
   Needs: a sky130 PDK on the machine that runs it (the script hard-fails without one).

2. **Bring the README's "capability gap" section up to date.** It still says `klt extract`
   is device-level only and presents #619 and #620 as open gaps, while CI now runs
   `klt extract --abstract-cells` on both layouts. It also cites `sky130-modexp#8` as an
   open seam (that issue is closed) and describes `scripts/` as "fetch + embargo check".
   Done when: the section states the gap as closed with links to `evidence/klt-extract.md`
   and `evidence/upstream.md`, the `scripts/` line lists the regression scripts, and the
   original wording is kept as history in the same way the lifted embargo section is.

3. **Run `klt lvs` on `puzzle.gds` against `evidence/puzzle-extracted.v`.** This is scope
   item 3 of #47, recorded as "Not done" in `evidence/warmup-klt-lvs.md`. It is
   self-consistency, not ground truth, but it is the only place `klt lvs` meets a
   third-party layout of this size (728 signal cells).
   Done when: a recorded run is appended to an evidence file with the command, `klt`
   version, verdict and counts, the envelope is committed with reference-side names handled
   as the warm-up envelopes are, and any tool-side finding is filed upstream.
   Needs: a sky130 PDK, as item 1.

4. **Check the featured writeups against our record.** The README says of the 15 writeups
   in Jane Street's results post: "We have not checked these writeups against our record
   yet."
   Done when: `evidence/easter-eggs.md` has a dated addendum listing, per writeup, anything
   that contradicts or adds to our record, each point reproduced here before it is written
   down (`CLAUDE.md` §5), unreachable links are named as such, and the README sentence is
   replaced by a pointer to the addendum.

## Next

- **Put the LVS result under CI.** Unblocked by Now 1. First question to answer in that
  run: does `klt lvs --check evidence/warmup-klt-lvs-01.json` pass on a runner with no PDK
  and only the fetched puzzle files? If yes, add it as a CI step; if it needs a PDK, record
  that and stop. Done when CI runs the check or `evidence/warmup-klt-lvs.md` says why not.
- **Promote the `02` power-rail comparison to an expected match.** Unblocked by Now 1
  reporting `match`. Done when `scripts/warmup-klt-lvs.sh` exits nonzero if either
  reference fails to match, replacing today's "exit 0 means the runs completed" contract.
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

Nothing is parked on an operator decision or an upstream release. Now 1 and Now 3 need a
sky130 PDK on the worker; Run 1 found one under `~/.ciel` on a dispatch worker, so this is
an environment requirement and not a block.

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
