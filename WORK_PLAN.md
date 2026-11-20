# Work Plan

Prioritized roadmap regenerated from current GitHub label state by the Guide
triage agent. Everything between the markers below is machine-generated and
overwritten wholesale on each update — do not hand-edit it. See
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
maintained.

<!-- guide:plan-body:start -->
_Generated: 2026-11-20T23:54:29Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#159**: Put the warm-up klt lvs result under CI now that klayout-tools#5631 is closed: re-verify --check on the nested puzzle/ clone and gate it

## Important

`loom:important`; taken before unlabelled work.

- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

- **#159**: Put the warm-up klt lvs result under CI now that klayout-tools#5631 is closed: re-verify --check on the nested puzzle/ clone and gate it
- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result
- **#164**: Share GDS label-to-polygon matching between the pin reporter and extractor

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

- **#159**: Put the warm-up klt lvs result under CI now that klayout-tools#5631 is closed: re-verify --check on the nested puzzle/ clone and gate it *(curated)*
- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result *(curated)*

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
| Ready (`loom:issue`, net of holds/building/merge-pending) | 3 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 2 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
