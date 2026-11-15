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

_None._

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#75**: README: the "capability gap" section still describes klt extract as device-level only
- **#89**: Share the warm-up shift-load protocol: the recorder testbench re-emits 30 of its 34 lines from build_shift_load_testbench
- **#91**: Share the tools/sim CLI preamble: a 15-line block triplicated, a 19-line block doubled, and no CLI catches IcarusNotFoundError

## In Progress

Issues currently being built (`loom:building`).

- **#76**: Run klt lvs on puzzle.gds against evidence/puzzle-extracted.v (scope item 3 of #47)
- **#77**: Check the 15 featured writeups against our record and append the result to evidence/easter-eggs.md
- **#93**: One source of truth for driven/supply pin names: tools/floating-nets re-rolls both, and its copy disagrees with the gds_extract.py constant it cites

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#95**: refactor(tools): share one driven/supply pin definition, widening it to HI/LO

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#90**: feat(puzzle-lvs): run klt lvs on puzzle.gds, file the port-name reader defect

## Proposed

Issues carrying `loom:curated`.

- **#75**: README: the "capability gap" section still describes klt extract as device-level only *(curated)*
- **#76**: Run klt lvs on puzzle.gds against evidence/puzzle-extracted.v (scope item 3 of #47) *(curated)*
- **#77**: Check the 15 featured writeups against our record and append the result to evidence/easter-eggs.md *(curated)*

## Proposed (Architect / Hermit)

- **#78**: Remove dead code in tools/sim/solve.py: unreferenced concrete_trace() and the unused free_lits accumulation *(hermit)*
- **#94**: Share the GDS-open preamble: tools/extract, tools/inventory and tools/pins each re-roll the same 20-line klayout-resolve-and-read block *(hermit)*
- **#96**: Share the klayout bootstrap in the test harnesses: tools/test-inventory, test-pins and test-extract triplicate the same try/except and the same skip-all guard *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 0 |
| Ready (`loom:issue`) | 3 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 3 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
