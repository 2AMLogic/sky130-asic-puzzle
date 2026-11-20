# Work Plan

Prioritized roadmap regenerated from current GitHub label state by the Guide
triage agent. Everything between the markers below is machine-generated and
overwritten wholesale on each update — do not hand-edit it. See
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
maintained.

<!-- guide:plan-body:start -->
_Generated: 2026-11-20T20:12:42Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#157**: Bump the CI klt pin from 0.9.1 to 0.9.2 and record the run in evidence/klt-extract.md

## Important

`loom:important`; taken before unlabelled work.

- **#158**: warmup-klt-lvs.sh: fail when the 01 match regresses or the 02 mismatch counts move, instead of exiting 0 whenever the runs complete

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

- **#157**: Bump the CI klt pin from 0.9.1 to 0.9.2 and record the run in evidence/klt-extract.md
- **#158**: warmup-klt-lvs.sh: fail when the 01 match regresses or the 02 mismatch counts move, instead of exiting 0 whenever the runs complete

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#157**: Bump the CI klt pin from 0.9.1 to 0.9.2 and record the run in evidence/klt-extract.md *(curated)*
- **#158**: warmup-klt-lvs.sh: fail when the 01 match regresses or the 02 mismatch counts move, instead of exiting 0 whenever the runs complete *(curated)*
- **#159**: Put the warm-up klt lvs result under CI now that klayout-tools#5631 is closed: re-verify --check on the nested puzzle/ clone and gate it *(curated)*

## Proposed (Architect / Hermit)

- **#78**: Remove dead code in tools/sim/solve.py: unreferenced concrete_trace() and the unused free_lits accumulation *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 1 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 2 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 3 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
