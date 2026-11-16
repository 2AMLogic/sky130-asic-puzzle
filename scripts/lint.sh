#!/usr/bin/env bash
# Static checks that need no third-party tooling: every Python tool must compile,
# every shell script must parse, and every tool/script must be executable.
#
# ShellCheck and ruff are used when they happen to be installed, and skipped
# (reported, not silently) when they are not — CI should not depend on a linter
# that a contributor's machine may lack.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

fail=0
note() { printf '  %-8s %s\n' "$1" "$2"; }

# Scratch file for compiler/parser stderr (issue #121): a fixed /tmp path let two
# concurrent lint runs print each other's error text under the wrong filename.
ERR="$(mktemp)"
trap 'rm -f "$ERR"' EXIT

echo "Lint"
echo "------------------------------------------------------------"

# 1. Python tools compile.
py_files=()
while IFS= read -r f; do py_files+=("$f"); done < <(
  find tools -type f \( -name '*.py' -o -perm -u+x \) 2>/dev/null | sort
)
for f in "${py_files[@]:-}"; do
  [ -z "${f:-}" ] && continue
  head -n1 "$f" | grep -q 'python3' || [[ "$f" == *.py ]] || continue
  if python3 -m py_compile "$f" 2>"$ERR"; then
    note "ok" "$f compiles"
  else
    note "FAIL" "$f does not compile:"; sed 's/^/           /' "$ERR"; fail=1
  fi
done

# 2. Shell scripts parse. Recursive over scripts/ (unlike enumeration 3 below):
# scripts/lib/ carries sourced helpers (e.g. klt-lvs-preamble.sh, #131) that are
# never executed directly but must parse, or every caller dies at source time.
while IFS= read -r f; do
  if bash -n "$f" 2>"$ERR"; then
    note "ok" "$f parses"
  else
    note "FAIL" "$f does not parse:"; sed 's/^/           /' "$ERR"; fail=1
  fi
done < <(find scripts -type f -name '*.sh' | sort)

# 3. Everything meant to be run is executable.
#
# Enumerated with find rather than hand-listed (issue #79): a hardcoded list is
# the only one of this script's three enumerations that can silently fall behind
# the directory, and it had — tools/floating-nets was missing from it while
# scripts/puzzle-regression.sh invoked it directly, so a lost +x bit would have
# passed lint and failed later as a confusing exec error.
#
# The set is "a top-level entry point": every tools/ file that is not a Python
# module (*.py, imported) or documentation (*.md), plus every scripts/*.sh.
# tools/sim/ and tools/vcd/ are import-only packages, so -maxdepth 1 excludes
# them deliberately. On scripts/ the same non-recursion is also deliberate, for
# a different reason (#131): sourced helpers under scripts/lib/ carry no +x by
# design, so the executable check must keep applying to entry points only.
while IFS= read -r f; do
  [ -n "${f:-}" ] || continue
  [ -e "$f" ] || continue
  if [ -x "$f" ]; then
    note "ok" "$f is executable"
  else
    note "FAIL" "$f is not executable (chmod +x)"; fail=1
  fi
done < <(
  { find tools -maxdepth 1 -type f ! -name '*.py' ! -name '*.md'; \
    find scripts -maxdepth 1 -type f -name '*.sh'; } 2>/dev/null | sort
)

# 4. Optional linters.
if command -v shellcheck >/dev/null 2>&1; then
  # scripts/lib/ included (enumeration 2's rationale, #131): the sourced helper
  # is lint-owned even though nothing executes it directly.
  if shellcheck -S warning scripts/*.sh scripts/lib/*.sh; then
    note "ok" "shellcheck clean"
  else
    note "FAIL" "shellcheck reported problems"; fail=1
  fi
else
  note "skip" "shellcheck not installed"
fi

if command -v ruff >/dev/null 2>&1; then
  if ruff check --line-length 100 tools; then
    note "ok" "ruff clean"
  else
    note "FAIL" "ruff reported problems"; fail=1
  fi
else
  note "skip" "ruff not installed"
fi

# 5. --help prints only the header comment block.
#
# A script that reads its own header as its help text must stop where the
# header stops (issue #132): a hard-coded end line drifts every time the
# header is edited, and had drifted both ways — sim-selftests.sh printed
# shell code after the header, warmup-regression.sh truncated it mid-sentence.
# This catches an overshoot mechanically; it cannot catch an undershoot (a
# truncated header is still all comment lines), which stays an acceptance
# test on the script's last help line. Scripts without a -h|--help arm are
# skipped, not failed — growing one is not a lint requirement — and the
# skip is reported, per the header contract at the top of this file: a
# script dropping out of this gate must appear as a changed line, not a
# vanished one (issue #140).
# The gate matches a real case arm, not the bare '-h|--help' substring: the
# substring occurs in this file's own text, and lint.sh takes no arguments,
# so `lint.sh --help` re-ran the whole lint and this loop recursed until the
# CI job timeout killed the run. The match stays anchored at a line start
# but tolerates spacing and operand order within the arm: -h|--help), -h |
# --help), --help|-h), and bare -h) or --help) all gate; an arm naming no
# help flag (-v|--verbose)) still does not. The invariant that must not
# regress is that the pattern matches no line of this file itself, including
# the line carrying it — re-check after any edit to the pattern or to any
# line that could start with a help flag. `timeout` bounds any future
# hanging help arm the same way, to a FAIL instead of a dead job. Help
# output is captured
# into a variable and tested from it via a here-string, so no stage of the
# check is a pipe: `grep -q` short-circuits on the first non-comment line,
# and a piped producer would take SIGPIPE (141) once the spill outgrew the
# pipe buffer — under `set -o pipefail` that status, not grep's verdict,
# decided the `if` and reported `ok` on large spills. With no pipe in the
# chain, the verdict is grep's at any output size.
arm_re='^[[:space:]]*(-h|--help)([[:space:]]*\|[[:space:]]*(-h|--help))?[[:space:]]*\)'
while IFS= read -r f; do
  if ! grep -qE "$arm_re" "$f"; then
    note "skip" "$f has no -h|--help arm"
    continue
  fi
  rc=0
  out="$(timeout 10 "$f" --help 2>/dev/null)" || rc=$?
  if [ "$rc" -eq 124 ]; then
    note "FAIL" "$f --help timed out (help arm hung?)"; fail=1
  elif [ "$rc" -ne 0 ]; then
    note "FAIL" "$f --help exited $rc (help arm must exit 0)"; fail=1
  elif grep -qvE '^#|^$' <<<"$out"; then
    note "FAIL" "$f --help spills non-comment lines"; fail=1
  else
    note "ok" "$f --help is header-only"
  fi
done < <(find scripts -maxdepth 1 -type f -name '*.sh' | sort)

rm -rf tools/__pycache__ 2>/dev/null || true

echo "------------------------------------------------------------"
if [ "$fail" -ne 0 ]; then
  echo "LINT FAILED" >&2
  exit 1
fi
echo "Lint passed."
