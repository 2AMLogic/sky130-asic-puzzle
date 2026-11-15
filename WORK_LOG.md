# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage agent. Entries are appended, never rewritten in place — see
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
updated.

### 2026-11-14

- **PR #88**: refactor(regressions): call tools/rename for the drop-instance mutation check
- **PR #87**: refactor: share the self-test summary line via testutil.summarize()/report_checks()
- **PR #86**: refactor: drop tools/compare --emit-json-netlist write side-channel
- **PR #84**: ci: run tools/test-extract in the puzzle regression, find-enumerate lint's exec check
- **PR #81**: warmup-lvs: pass --abstract-cell-lef, name the PDK in the request, record Run 2
- **Issue #85** (closed): Remove tools/compare --emit-json-netlist: a dead, undocumented flag superseded by tools/extract --json
- **Issue #83** (closed): Stop re-rolling drop-instance in shell: both regression scripts inline a mutation tools/rename already implements
- **Issue #80** (closed): Finish the tools/testutil.py consolidation: triplicated summary block and test-klt-extract's re-rolled tracker
- **Issue #79** (closed): Stop hand-maintaining three tool inventories: tools/test-extract runs in no CI path
- **Issue #74** (closed): Re-run the warm-up klt lvs on a klt that contains the fixes for klayout-tools #3748 and #3749

### 2026-11-12

- **PR #71**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-07

- **PR #69**: test: add puzzle.gds extraction regression to CI
- **Issue #68** (closed): Add a puzzle.gds extraction regression to CI: tools/extract and klt vs puzzle-extracted.v
- **PR #66**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #64**: ci: install pinned klt and add --require-klt to the warm-up regression
- **Issue #63** (closed): CI: install a pinned klt so warm-up regression step 5 (klt extract cross-check) runs

### 2026-11-03

- **PR #61**: chore: reinstall squad 0.19.24 (from 0.2.x)

### 2026-10-31

- **PR #59**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-21

- **PR #56**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-17

- **PR #54**: refactor: drop stale extract skip path and --require-extract from warmup regression
- **Issue #53** (closed): Remove stale tools/extract skip path and --require-extract flag from warmup-regression
- **PR #51**: refactor: reduce check-embargo.sh to the tracked-puzzle-files guard
- **PR #49**: feat: run klt lvs on the warm-up layout against its published netlists
- **PR #48**: feat: cross-check extraction with klt extract --abstract-cells
- **Issue #50** (closed): Trim check-embargo.sh: privacy checks are unreachable since the embargo lifted
- **Issue #47** (closed): Run klt lvs on the warm-up GDS against its published gate-level netlist (third-party layout, ground truth)
- **Issue #46** (closed): Close the loop: extract the warm-up and puzzle GDS with klt extract --abstract-cells and compare with tools/extract

### 2026-10-16

- **PR #44**: Bump Repo Skills 0.24.1 -> 0.24.3

### 2026-10-15

- **PR #42**: Bump Repo Skills 0.19.5 -> 0.24.1

### 2026-10-13

- **PR #41**: chore(loom): drop onIdle [auditor] — follow the fleet idle-role setting

### 2026-10-08

- **Issue #26** (closed): Guard trigger: force-op:protected on git reset/checkout inside PR worktree

### 2026-10-02

- **PR #37**: docs: reconcile against Jane Street's ASIC puzzle results post

### 2026-09-29

- **PR #35**: refactor: share test-* record()/check()/_box()/_label() helpers via tools/testutil.py
- **Issue #33** (closed): Remove duplicated record/check/_box/_label helpers across tools/test-* scripts

### 2026-09-28

- **PR #32**: chore: gitignore Repo Skills guard-hook logs
- **Issue #31** (closed): gitignore: add .claude/skills/repo/logs/ so guard-hook logs don't block fleet resync (2am#1184)

### 2026-09-26

- **PR #29**: docs: annotate lifted privacy constraint in pre-submission briefs
- **Issue #27** (closed): docs: stale "Private until 2026-09-04" strings survive the public flip

### 2026-08-11

- **PR #25**: fix: install ruff in CI and clear the 25 pre-existing violations
- **PR #23**: docs: correct EASTER-EGG-HUNT.md claims about inventory-puzzle.json contents
- **Issue #24** (closed): CI's Lint step never installs ruff, so 25 ruff violations on main go undetected
- **Issue #22** (closed): EASTER-EGG-HUNT.md promises placement coordinates in inventory-puzzle.json; the file has only counts

### 2026-08-10

- **PR #21**: feat: decode the output generator's message for the solved input (stage 8)
- **PR #20**: feat: solve a gate-level netlist for an output via bounded model checking
- **PR #19**: docs: record stage-6 go/no-go decision on puzzle replay timing mismatch
- **PR #18**: feat: verify extracted netlists via simulation (cross-check + puzzle replay)
- **PR #17**: feat: require tools/extract in CI's warm-up regression gate
- **PR #13**: fix: run tools/test-inventory and tools/test-pins in the warm-up regression
- **PR #11**: feat: add cell-level connectivity extraction (GDS to gate-level Verilog)
- **Issue #16** (closed): Stage 8: produce the answer — simulate the output generator with the solved inputs
- **Issue #15** (closed): Stage 7: solve for success across the 92-bit state (bounded model checking / SAT)
- **Issue #14** (closed): Stage 6: apply the recovered flow to puzzle.gds and match example_inputs.vcd
- **Issue #12** (closed): CI never runs tools/test-inventory or tools/test-pins
- **Issue #9** (closed): Wire the end-to-end warm-up gate (extract -> compare) once cell-level extraction lands
- **Issue #5** (closed): Simulation harness: replay example_inputs.vcd against a recovered netlist
- **Issue #2** (closed): Cell-level connectivity extraction: gate-level Verilog from a placed-and-routed sky130 GDS

### 2026-08-08

- **PR #10**: feat: add tools/inventory and tools/pins, resolved from the GDS stream
- **PR #8**: feat: add netlist equivalence comparator and wire the warm-up regression into CI
- **PR #7**: feat: add VCD replay + directed simulation harness for the warm-up netlist
- **PR #6**: docs: file the two klt extraction gaps upstream (CLAUDE.md §2)
- **Issue #4** (closed): File the two klt extraction gaps upstream, toolkit-first (CLAUDE.md §2)
- **Issue #3** (closed): The warm-up regression: netlist equivalence up to renaming, wired into CI
- **Issue #1** (closed): Extraction harness: cell inventory and pin abstracts, resolved from the stream rather than the PDK
