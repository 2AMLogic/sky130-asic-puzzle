#!/usr/bin/env bash
# Invalid arguments must leave both committed reports intact, even on a fresh checkout.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/scripts" "$scratch/evidence"
cp scripts/warmup-klt-lvs.sh "$scratch/scripts/"
reports=(evidence/warmup-klt-lvs-{01,02}.json)
cp "${reports[@]}" "$scratch/evidence/"

# Deliberately omit the PDK preamble and puzzle files. Argument errors must
# reach the caller before the script needs either prerequisite.
reject() {
  local rc=0 report
  bash "$scratch/scripts/warmup-klt-lvs.sh" "$@" 2>"$scratch/stderr" || rc=$?
  if [[ $rc != 2 ]] || ! grep -q '^Usage:' "$scratch/stderr"; then
    printf 'Expected usage error for [%s], got exit %s\n' "$*" "$rc" >&2
    cat "$scratch/stderr" >&2
    return 1
  fi
  for report in "${reports[@]}"; do
    cmp "$report" "$scratch/$report"
  done
}

reject --check
reject --check-only extra
reject ''
