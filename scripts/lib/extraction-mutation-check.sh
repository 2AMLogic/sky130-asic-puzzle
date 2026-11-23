# shellcheck shell=bash
# Shared drop-instance mutation check for the extraction regressions
# (scripts/warmup-regression.sh and scripts/puzzle-regression.sh, issue #194).
# Source it, never execute it:
#
#   source "$ROOT/scripts/lib/extraction-mutation-check.sh"
#   check_extraction_mutation "$EXTRACTED" "$MUTATED" "$REFERENCE"
#
# Lives under scripts/lib/ so scripts/lint.sh's `-maxdepth 1` enumeration does
# not demand the +x bit a sourced file deliberately does not carry (same
# convention as scripts/lib/klt-lvs-preamble.sh, issue #131).
#
# tools/compare defines four exit codes (tools/compare:60-63):
#   0  equivalent
#   1  not equivalent (the ONLY outcome that establishes mutation detection)
#   2  usage, I/O, or parse error
#   3  inconclusive — the branch budget ran out before the search could
#      decide (issue #199)
# Treating any nonzero exit as "rejected" turns an unreadable input or tool
# error (exit 2), or an undecided search (exit 3), into a false pass. These
# helpers require successful mutation generation, accept only comparator exit
# 1, and surface unexpected exits (exit 3 propagates through the catch-all
# below) with their diagnostics.

# Verify that tools/compare rejects <mutated> against <reference> with exit 1.
# Exits/returns 0 on comparator exit 1, 1 on comparator exit 0 (false accept),
# and the comparator's nonzero exit code on any other exit (with diagnostics).
check_mutated_netlist_rejected() {
  if [ "$#" -ne 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: check_mutated_netlist_rejected <mutated> <reference>" >&2
    return 2
  fi

  local mutated="$1"
  local reference="$2"
  local root="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local compare_tool="${MUTATION_COMPARE_TOOL:-$root/tools/compare}"

  local rc=0
  local output
  output="$("$compare_tool" "$mutated" "$reference" 2>&1)" || rc=$?

  case "$rc" in
    1)
      return 0
      ;;
    0)
      echo "FAILED — comparator accepted a netlist with an instance removed." >&2
      return 1
      ;;
    *)
      echo "FAILED — comparator exited $rc (expected 1 for mismatch) checking $mutated against $reference." >&2
      if [ -n "$output" ]; then
        printf '%s\n' "$output" >&2
      fi
      return "$rc"
      ;;
  esac
}

# Drop one signal instance from <extracted> into <mutated>, then verify that
# tools/compare rejects <mutated> against <reference> with exit 1.
check_extraction_mutation() {
  if [ "$#" -ne 3 ] || [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: check_extraction_mutation <extracted> <mutated> <reference>" >&2
    return 2
  fi

  local extracted="$1"
  local mutated="$2"
  local reference="$3"
  local root="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local rename_tool="${MUTATION_RENAME_TOOL:-$root/tools/rename}"

  local rename_rc=0
  "$rename_tool" --no-rename --mutate drop-instance "$extracted" -o "$mutated" || rename_rc=$?
  if [ "$rename_rc" -ne 0 ]; then
    echo "FAILED — mutation generation exited $rename_rc for $extracted -> $mutated." >&2
    return "$rename_rc"
  fi

  check_mutated_netlist_rejected "$mutated" "$reference" || return $?
  echo "mutation check: comparator rejects a damaged netlist (ok)"
}
