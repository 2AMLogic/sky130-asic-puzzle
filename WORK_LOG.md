# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage agent. Entries are appended, never rewritten in place — see
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
updated.

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
