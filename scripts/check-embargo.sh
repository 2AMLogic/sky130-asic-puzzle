#!/usr/bin/env bash
# Guard the one boundary that still binds: the upstream puzzle files must never
# be committed here (CLAUDE.md §3 — janestreet/asic-puzzle-2026 carries no
# license). The embargo itself lifted 2026-09-04 (CLAUDE.md §1).
set -uo pipefail

# The upstream puzzle files must not be tracked (no license, and they are
# the subject itself).
tracked=$(git ls-files | grep -E '^puzzle/|(^|/)puzzle\.gds$|(^|/)example_inputs\.vcd$' || true)
if [ -n "$tracked" ]; then
  echo "  FAIL  upstream puzzle files are tracked:"
  printf '        %s\n' $tracked
  echo "PUZZLE FILE CHECK FAILED" >&2
  exit 1
fi
echo "  ok    no upstream puzzle files tracked"
