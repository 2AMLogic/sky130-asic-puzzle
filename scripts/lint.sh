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

# 2. Shell scripts parse.
while IFS= read -r f; do
  if bash -n "$f" 2>"$ERR"; then
    note "ok" "$f parses"
  else
    note "FAIL" "$f does not parse:"; sed 's/^/           /' "$ERR"; fail=1
  fi
done < <(find scripts -maxdepth 1 -type f -name '*.sh' | sort)

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
# them deliberately.
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
  if shellcheck -S warning scripts/*.sh; then
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
# skipped, not failed — growing one is not a lint requirement.
while IFS= read -r f; do
  grep -q -- '-h|--help' "$f" || continue
  if "$f" --help 2>/dev/null | grep -qvE '^#|^$'; then
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
