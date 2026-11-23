# Roadmap

`sky130-asic-puzzle` points [`klayout-tools`](https://github.com/2AMLogic/klayout-tools)
(`klt`) at a sky130 standard-cell layout that another flow produced, with published ground
truth, so the toolkit is tested on something it did not build itself.

Status as of 2026-11-15, `main` @ `f89a3d7`.

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
| Same layout through `klt extract --abstract-cells`, equivalent to `01_netlist.v`, with a mutation check | `evidence/klt-extract.md` Run 2 and Run 4; `--require-klt` (#63, PR #64) | in CI, `klayout-tools==0.9.2` pinned |
| `puzzle.gds` through both extractors, equivalent to `evidence/puzzle-extracted.v`, exactly one floating net | `scripts/puzzle-regression.sh`, `evidence/klt-extract.md` Run 3 (#68, PR #69) | in CI |
| No upstream puzzle file tracked (`CLAUDE.md` §3) | `scripts/check-embargo.sh` | in CI |
| `klt lvs` of the warm-up against `01_netlist.v` (signal-only) | `evidence/warmup-klt-lvs.md` Run 1 and Run 2, `evidence/warmup-klt-lvs-01.json` | **match** in both, run by hand on 2026-10-17 and 2026-11-14 (re-confirmed 2026-11-20 on `klt 0.9.3.dev2572`), not in CI; pinned as the expected verdict (#158) |
| `klt lvs` of the warm-up against `02_netlist_with_power_rails.v` | same file, `evidence/warmup-klt-lvs-02.json` | **mismatch** in both runs, tool-side; 243 mismatches (242 errors) on `klt 0.9.2.dev1022` against Run 1's 159 — open upstream as klayout-tools#5632; pinned as the expected verdict in `evidence/warmup-klt-lvs-expected.json`, and `scripts/warmup-klt-lvs.sh` exits nonzero if it moves (#158) |
| `klt lvs` of `puzzle.gds` against this repo's own `evidence/puzzle-extracted.v` | `evidence/puzzle-klt-lvs.md` Run 1 and Run 2, `evidence/puzzle-klt-lvs-01.json` | recorded 2026-11-14 and 2026-11-23, not in CI; the klayout-tools#5693 reader fix (PR #7452, `6ca7e00` — no release carries it yet, so the Run 2 baseline used a throwaway build of that commit) let the compare run for the first time and it **mismatches**, tool-side: #7561's pad-route join shorts four driven nets into `VGND` (31 mismatches). Pinned as the expected verdict in `evidence/puzzle-klt-lvs-expected.json`, and `scripts/puzzle-klt-lvs.sh` exits nonzero if it moves (#165) |

**The warm-up `klt lvs` re-run on the fixed build (done, #74, PR #81).** Run 2 of
`evidence/warmup-klt-lvs.md` (2026-11-14, `klt 0.9.2.dev1022+g2a9c52b27ce7`, klayout
0.30.13) re-ran both references on a build carrying the fixes for klayout-tools #3748 and
#3749. `01` still matches; `02` still mismatches, and mismatches harder (243 against Run
1's 159), because `--abstract-cell-lef` restores the `VNB` pin but leaves it bound to the
deck's synthesized `vsubs` global, which no abstracted cell ties to the ground rail. The
two fixes are in practice mutually exclusive — filed as klayout-tools#5632 — and the
nested-clone `--check` failure found in the same run is klayout-tools#5631 (since fixed upstream; Run 3). Run 2 also
retracts two Run 1 attributions (`evidence/upstream.md:15-16`): the #3748 fix was
message-only, since `reference.pdk` already existed and no `export PDK=sky130A` workaround
is involved, and the `02` mismatch is not the dropped `VNB` pin.

**The pinned LVS verdict gate (done, #158).** `evidence/warmup-klt-lvs-expected.json`
pins Run 2's verdicts — `01` `match`; `02` the tool-side `mismatch` at 243/242
(klayout-tools#5632) — and `scripts/warmup-klt-lvs.sh` now exits nonzero when
either moves, replacing the old "exit 0 means the runs completed" contract:
the PDK-free `tools/lvs-verdict` compares both envelopes after both references
run, names any moved value and its direction, and reports `02` turning `match`
as a stale pin to promote rather than a pass. Its own self-test
(`tools/test-lvs-verdict`, canned envelopes, the four cases of #158) is a named
CI step. The pin was re-confirmed unchanged on `klt 0.9.3.dev2572` / klayout
0.30.12 before landing, and that confirming run also showed cheap
`klt lvs --check` exiting 0 on the refreshed envelopes — the #5631 path
anchoring no longer reproduces on a post-0.9.2 build (`evidence/warmup-klt-lvs.md`, pinned-expectation
section).

**The warm-up envelopes are under CI (#159).** `scripts/warmup-klt-lvs.sh --check-only` re-extracts
the layout netlist and runs `klt lvs --check` on the committed envelopes in CI; it passes on the
pinned 0.9.2 and fails on hash drift (`evidence/warmup-klt-lvs.md`, Run 3). Re-recording the
envelopes still needs a klt past 0.9.2: 0.9.2 itself drops the `puzzle/` segment (#5631).

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

**Upstream findings.** Eleven toolkit gaps have been filed from this repo
(`evidence/upstream.md:10-20`): klayout-tools #619, #620, #673, #674, #675, #3748, #3749,
#5631, #5632, #5693 and #7561. Ten read as closed on the upstream tracker today
(#5693 closed 2026-11-23 by PR #7452, #5632 closed the same day); **#7561 is open** —
the pad-route join that shorts anonymous nets into a named rail, found by the puzzle
verdict's first baseline run (#165) — so a matching puzzle compare is blocked upstream
rather than here. Nine of the ten have been
re-verified against a `klt` that contains the fix: #619 and #620 by `evidence/klt-extract.md`,
#3748 and #3749 by Run 2 above, #5631 by Run 3 (fixed on `0.9.3.dev2572`; **not** in the
published 0.9.2, so re-recording the envelopes waits for the next release), #5693 by
the puzzle Run 2 baseline on a throwaway build of the #7452 merge (`evidence/puzzle-klt-lvs.md`,
Run 2 — the read succeeded; the mismatch it revealed is #7561), and #673, #674 and #675
by the dated verification rows in `evidence/upstream.md`, run 2026-11-21 under #160
(`klt 0.9.3.dev2575+g6bd18bbc8637`) — each agrees with its local evidence script.
#5632 closed too recently to have been re-run from this side: re-checking the `02`
comparison against a `klt` that carries its fix is the remaining open step.

**Tracker.** Three issues are open as of 2026-11-23 (re-read from the API at 21:32Z):
#205 (the `## Now` section's inventory is stale), #211 (this paragraph's stale status
clauses, being fixed here) and #30, the automated merge-hold digest, which is not work.
Labels move quickly and are not restated here; read them from the API. #203 (the
earlier refresh, PR #204) and #192 (concurrent Guide passes open duplicate docs PRs, and
the Judge's docs fast-path reads a `gh` field 2.102.0 lacks) have both closed as
completed. #178 (derive Icarus
simulation success from the vvp exit code) has closed with its pull request, PR #179,
merged. Everything the earlier inventory carried has closed too: the curated pair #106
(PR #115) and #112 (PR #120), the approval hold #100, the triage hold #118, the fresh
filings #119, #121 and #122, and the operator-parked #78 — all eight checked closed via
the GitHub API 2026-11-23. Open pull requests are not counted here, since any new PR
would make a count wrong without a line changing. `WORK_PLAN.md` is machine-generated
and lags these filings.

## Now

The queue is not empty, but nothing in it is idle-dispatchable as this is written: no
open issue carries `loom:issue`. #106 and #112 are curated and in flight behind PRs
#115 and #120; #100 is curated (points:2) and awaiting approval; #119, #121 and #122
await curation; #118 is blocked on a triage decision; #78 and #30 are parked or blocked
as described under "Tracker" and "Blocked and waiting". The three items this section
carried on 2026-11-13 are done and recorded under "Where it stands" (#75 as PR #103,
#76 as PR #90, #77 as PR #99); the fourth item the list opened with was #74, merged as
PR #81 the same day. New items are filed as issues, curated with a point estimate, and
then listed here.

## Next

Nothing is scoped here: the open items are the upstream waits under "Blocked and
waiting", and the earlier #159 and #160 work has landed.

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

#78 (Hermit: dead code in `tools/sim/solve.py`) is parked on an operator decision; #118
is blocked on a triage decision (whether `sim-selftests.sh` should now gate
`selftest_solve`, whose "blocked on #98" skip is stale); #30 is the automated
merge-hold digest, not work. Nothing else here waits on a person. The `02`
comparison cannot be re-checked until a released klt carries the #5632 fix, and a
matching puzzle compare cannot be resolved while klayout-tools#7561 is open; re-recording the warm-up envelopes waits
for the first klayout-tools release after 0.9.2 (#5631's fix), and no released klt
yet carries the #5693 reader fix either — the puzzle Run 2 baseline had to build
`6ca7e00` throwaway (#165).

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
