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
  if python3 -m py_compile "$f" 2>/tmp/lint-py-err; then
    note "ok" "$f compiles"
  else
    note "FAIL" "$f does not compile:"; sed 's/^/           /' /tmp/lint-py-err; fail=1
  fi
done

# 2. Shell scripts parse.
while IFS= read -r f; do
  if bash -n "$f" 2>/tmp/lint-sh-err; then
    note "ok" "$f parses"
  else
    note "FAIL" "$f does not parse:"; sed 's/^/           /' /tmp/lint-sh-err; fail=1
  fi
done < <(find scripts -maxdepth 1 -type f -name '*.sh' | sort)

# 3. Everything meant to be run is executable.
for f in tools/compare tools/rename tools/test-compare scripts/*.sh; do
  [ -e "$f" ] || continue
  if [ -x "$f" ]; then
    note "ok" "$f is executable"
  else
    note "FAIL" "$f is not executable (chmod +x)"; fail=1
  fi
done

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

rm -rf tools/__pycache__ 2>/dev/null || true

echo "------------------------------------------------------------"
if [ "$fail" -ne 0 ]; then
  echo "LINT FAILED" >&2
  exit 1
fi
echo "Lint passed."
