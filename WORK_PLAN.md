# Work Plan

Prioritized roadmap regenerated from current GitHub label state by the Guide
triage agent. Everything between the markers below is machine-generated and
overwritten wholesale on each update — do not hand-edit it. See
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
maintained.

<!-- guide:plan-body:start -->
_Generated: 2026-11-23T03:58:00Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result
- **#172**: Share the sequence-testbench CYCLE stdout parser: CYCLE_RE and sample loop are duplicated in solve.py and selftest_answer.py
- **#174**: Remove the obsolete extraction blocker from VCD replay help and docstrings
- **#178**: Derive Icarus simulation success from the vvp exit code
- **#182**: Remove redundant backtracking guesses after a netlist signature mismatch
- **#186**: CI gates the warm-up envelopes' input hashes but not their recorded verdicts

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#176**: refactor(sim): share the CYCLE stdout parser in testbench.parse_sequence_samples
- **#179**: fix: derive Icarus sim success from vvp exit code
- **#189**: fix: drop tools/compare fallback to signature-incompatible backtracking guesses

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#175**: docs: retire the stale #2 blocker from the VCD replay docstrings
- **#188**: ci: assert committed warm-up LVS envelope verdicts ahead of puzzle fetch

## Proposed

Issues carrying `loom:curated`.

- **#160**: Confirm klayout-tools #673, #674 and #675 from this side: run the klt command that replaces each local evidence script on puzzle.gds and record the result *(curated)*
- **#182**: Remove redundant backtracking guesses after a netlist signature mismatch *(curated)*
- **#186**: CI gates the warm-up envelopes' input hashes but not their recorded verdicts *(curated)*

## Proposed (Architect / Hermit)

- **#78**: Remove dead code in tools/sim/solve.py: unreferenced concrete_trace() and the unused free_lits accumulation *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 0 |
| Important | 1 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 6 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 2 |
| Curated | 3 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
