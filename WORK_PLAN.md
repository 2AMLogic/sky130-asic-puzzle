# Work Plan

Prioritized roadmap regenerated from current GitHub label state by the Guide
triage agent. Everything between the markers below is machine-generated and
overwritten wholesale on each update — do not hand-edit it. See
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
maintained.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#74**: Re-run the warm-up klt lvs on a klt that contains the fixes for klayout-tools #3748 and #3749

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#75**: README: the "capability gap" section still describes klt extract as device-level only

## In Progress

Issues currently being built (`loom:building`).

- **#74**: Re-run the warm-up klt lvs on a klt that contains the fixes for klayout-tools #3748 and #3749

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#73**: docs: roadmap as of 2026-11-13

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#74**: Re-run the warm-up klt lvs on a klt that contains the fixes for klayout-tools #3748 and #3749 *(curated)*
- **#75**: README: the "capability gap" section still describes klt extract as device-level only *(curated)*
- **#77**: Check the 15 featured writeups against our record and append the result to evidence/easter-eggs.md *(curated)*

## Proposed (Architect / Hermit)

- **#78**: Remove dead code in tools/sim/solve.py: unreferenced concrete_trace() and the unused free_lits accumulation *(hermit)*
- **#79**: Stop hand-maintaining three tool inventories: tools/test-extract runs in no CI path *(hermit)*
- **#80**: Finish the tools/testutil.py consolidation: triplicated summary block and test-klt-extract's re-rolled tracker *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 1 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 0 |
| Curated | 3 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
