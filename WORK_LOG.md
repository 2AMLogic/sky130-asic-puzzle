# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide
triage agent. Entries are appended, never rewritten in place — see
`.loom/roles/guide.md`'s Document Maintenance phase for how this file is
updated.

## Archives

- [2026-08](work_log/WORK_LOG_2026-08.md)

### 2026-11-23

- **PR #200**: fix: report branch-budget exhaustion in tools/compare as INCONCLUSIVE, exit 3
- **PR #198**: test: make the automorphism fixture actually require a backtracking guess
- **PR #176**: refactor(sim): share the CYCLE stdout parser in testbench.parse_sequence_samples
- **Issue #199** (closed): tools/compare: budget exhaustion is reported as 'no correspondence exists', indistinguishable from a proof of non-equivalence
- **Issue #196** (closed): Simplify the backtracking fixture so it actually requires a guess
- **Issue #172** (closed): Share the sequence-testbench CYCLE stdout parser: CYCLE_RE and sample loop are duplicated in solve.py and selftest_answer.py
- **PR #195**: fix: require comparator exit 1 in shared extraction mutation check
- **PR #193**: refactor: remove five never-called helpers from tools/
- **PR #189**: fix: drop tools/compare fallback to signature-incompatible backtracking guesses
- **Issue #194** (closed): Share the extraction mutation check and require comparator exit 1
- **Issue #182** (closed): Remove redundant backtracking guesses after a netlist signature mismatch
- **Issue #78** (closed): Remove dead code in tools/sim/solve.py: unreferenced concrete_trace() and the unused free_lits accumulation
- **PR #173**: refactor: remove version forwarding from klt-extract
- **PR #168**: refactor: share GDS label-to-polygon matching between pin resolvers
- **PR #167**: ci: gate warm-up LVS envelopes with klt lvs --check and record Run 3
- **Issue #171** (closed): Remove tools/klt-extract --version and klt_version(): dead, undocumented, and broken by required -o
- **Issue #164** (closed): Share GDS label-to-polygon matching between the pin reporter and extractor
- **Issue #159** (closed): Put the warm-up klt lvs result under CI now that klayout-tools#5631 is closed: re-verify --check on the nested puzzle/ clone and gate it

### 2026-11-22

- **PR #181**: refactor: remove dead _UnionFind.groups and duplicate label pass in gds_extract
- **Issue #180** (closed): Simplify tools/gds_extract.py: remove dead _UnionFind.groups()/pre-registration and duplicate top-label pass

### 2026-11-20

- **PR #163**: fix: fail warmup-klt-lvs.sh when a pinned LVS verdict moves
- **PR #162**: Bump CI klayout-tools pin to 0.9.2 and record Run 4
- **Issue #158** (closed): warmup-klt-lvs.sh: fail when the 01 match regresses or the 02 mismatch counts move, instead of exiting 0 whenever the runs complete
- **Issue #157** (closed): Bump the CI klt pin from 0.9.1 to 0.9.2 and record the run in evidence/klt-extract.md

### 2026-11-19

- **PR #155**: chore: refresh Squad block and skill so unattended roles do not stop

### 2026-11-18

- **Issue #141** (closed): create-pr.sh accepts a literal `@path` as --body, silently publishing the path string instead of the PR body

### 2026-11-17

- **PR #151**: chore: ship $schema in opencode.json so OpenCode stops dirtying the checkout

### 2026-11-16

- **PR #149**: docs(lint): say '--help arm' in the section-5 skip message and comment
- **Issue #146** (closed): lint section 5: skip message and line-108 prose still say "-h|--help arm" after #144 narrowed the gate to --help
- **PR #145**: lint: require section-5 help arm to name --help
- **PR #142**: lint: report section-5 skips and widen the anchored help-arm match
- **PR #139**: refactor: share the CLI GDS-open-failure probe via testutil.check_cli_open_failures
- **Issue #144** (closed): lint.sh section 5: a bare `-h)`-only arm gates in but is tested with `--help`, yielding a vacuous `ok`
- **Issue #140** (closed): lint.sh section 5: a reformatted -h|--help case arm silently drops a script from the help-output gate
- **Issue #137** (closed): Share the CLI open-failure probe: _check_open_failure/test_cli_open_failures is triplicated across test-pins, test-inventory and test-extract
- **PR #138**: fix: attribute selftest_celltable's provenance print to the install each commit belongs to
- **PR #136**: fix: derive scripts' --help output by pattern, not hard-coded line range
- **Issue #133** (closed): selftest_celltable's "baseline recorded from:" line names source.version (ciel f6eeac7d), but the cells map was first parsed from the volare c6d73a35 path printed beside it
- **Issue #132** (closed): sim-selftests.sh --help prints 11 lines of shell code after the header
- **Issue #122** (closed): selftest_celltable's golden 69-cell check is pinned to an absolute volare path, so it skips everywhere but the recording host

### 2026-11-15

- **PR #135**: fix: ignore a root puzzle symlink and catch it in the embargo guard
- **PR #131**: refactor: share the klt-lvs PDK/LEF preamble in one sourced helper
- **PR #129**: fix: resolve selftest_celltable's golden check via the PDK resolver, not the recorded baseline path
- **Issue #128** (closed): gitignore: a `puzzle` symlink is not ignored (`puzzle/` matches directories only)
- **Issue #123** (closed): Share the klt-lvs PDK/LEF preamble: warmup-klt-lvs.sh and puzzle-klt-lvs.sh duplicate ~25 lines
- **PR #130**: ci: gate selftest_solve into the sim self-tests with a pinned python-sat
- **PR #127**: test-extract, lint: give every scratch path a per-run temp file
- **PR #126**: fix(sim): solver CLIs exit 2 on an unresolvable PDK, not a traceback
- **PR #124**: ci: pin klayout, ruff and ciel installs in ci.yml
- **PR #120**: fix: isolate CLI open-failure probes in per-run temp dirs
- **Issue #121** (closed): Test hygiene: tools/test-extract's remaining fixed /tmp paths are also write-then-read-back, not write-only
- **Issue #119** (closed): ci.yml pins the open_pdks commit but installs ciel unpinned
- **Issue #118** (closed): sim-selftests.sh still skips selftest_solve 'blocked on #98' after #98 landed — decide whether to gate it
- **Issue #112** (closed): Test hygiene: the GDS-open failure-path tests use fixed /tmp paths with a create-read-delete lifecycle
- **Issue #100** (closed): run_solve/run_answer still escape PdkResolutionError as a traceback, despite docstrings promising exit 2
- **PR #116**: ci: gate the tools/sim self-tests and the shift-load protocol in CI
- **PR #115**: refactor: read celltable's supply-pin filter from verilog_netlist.POWER_PINS
- **PR #114**: fix: parse 'input wire X;' cell ports so load_design() works on current open_pdks
- **PR #111**: refactor: share the GDS-open preamble as klayout_env.open_layout
- **PR #109**: fix: fail soft on klt-lvs probe stage and check PDK before fetching puzzle
- **PR #107**: refactor: share the warm-up shift-load protocol between both testbench generators
- **PR #104**: refactor: share the klayout bootstrap and skip-all guard via tools/testutil.py
- **PR #101**: refactor: share the tools/sim CLI preamble blocks; route IcarusNotFoundError to exit 2
- **PR #73**: docs: roadmap as of 2026-11-15
- **PR #105**: test: add CLI main() return-contract selftest for the five tools/sim CLIs
- **PR #103**: README: close the capability-gap section, keep the premise as history
- **PR #95**: refactor(tools): share one driven/supply pin definition, widening it to HI/LO
- **PR #99**: docs(evidence): check the 15 featured writeups against our record
- **PR #90**: feat(puzzle-lvs): run klt lvs on puzzle.gds, file the port-name reader defect
- **Issue #117** (closed): main is red since dd2925e: selftest_cli patches run_solve.load_design, renamed to load_design_for_cli by #101
- **Issue #113** (closed): tools/sim/selftest_cli.py fails on main: patches run_solve.load_design, which the #101 preamble refactor removed
- **Issue #108** (closed): Gate the tools/sim self-tests in CI: only selftest_cli runs today, and the shift-load protocol has no semantic gate at all
- **Issue #106** (closed): tools/sim/celltable.py keeps a fourth local supply-pin set after #93 collapsed the others
- **Issue #98** (closed): tools/sim/celltable.py cannot parse 'input wire X;' cell ports, so load_design() fails against current open_pdks
- **Issue #96** (closed): Share the klayout bootstrap in the test harnesses: tools/test-inventory, test-pins and test-extract triplicate the same try/except and the same skip-all guard
- **Issue #94** (closed): Share the GDS-open preamble: tools/extract, tools/inventory and tools/pins each re-roll the same 20-line klayout-resolve-and-read block
- **Issue #92** (closed): puzzle-klt-lvs.sh: let a probe failure fall through to stage 2, and check the PDK before fetching puzzle/
- **Issue #91** (closed): Share the tools/sim CLI preamble: a 15-line block triplicated, a 19-line block doubled, and no CLI catches IcarusNotFoundError
- **Issue #89** (closed): Share the warm-up shift-load protocol: the recorder testbench re-emits 30 of its 34 lines from build_shift_load_testbench
- **Issue #102** (closed): No test exercises any tools/sim CLI main(): a return-contract regression reached review undetected
- **Issue #93** (closed): One source of truth for driven/supply pin names: tools/floating-nets re-rolls both, and its copy disagrees with the gds_extract.py constant it cites
- **Issue #75** (closed): README: the "capability gap" section still describes klt extract as device-level only
- **Issue #77** (closed): Check the 15 featured writeups against our record and append the result to evidence/easter-eggs.md
- **Issue #76** (closed): Run klt lvs on puzzle.gds against evidence/puzzle-extracted.v (scope item 3 of #47)

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
