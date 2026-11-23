#!/usr/bin/env bash
# Self-test for the shared extraction mutation check
# (scripts/lib/extraction-mutation-check.sh, issue #194).
#
# Exercises all three comparator outcomes against both committed extracted
# Verilog references (no PDK, no klt, no puzzle/ files required):
#   - copy of reference                     -> comparator exit 0 -> FAIL
#   - one instance dropped by tools/rename  -> comparator exit 1 -> PASS
#   - missing mutated-side file             -> comparator exit 2 -> FAIL + diagnostic
# plus mutation-generation failure (even when a stale mutated file exists on
# disk) and argument validation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/lib/extraction-mutation-check.sh
source "$ROOT/scripts/lib/extraction-mutation-check.sh"

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

fail=0
pass() { printf '  ok    %s\n' "$1"; }
err() { printf '  FAIL  %s\n' "$1" >&2; fail=1; }

# Stub rename tools for exercising the full check_extraction_mutation path when
# the mutated output is an unmodified copy or was not written at all.
stub_copy="$scratch/stub-rename-copy.sh"
cat >"$stub_copy" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
src=""
dst=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-rename) shift ;;
    --mutate) shift 2 ;;
    -o|--output) dst="$2"; shift 2 ;;
    *) src="$1"; shift ;;
  esac
done
cp "$src" "$dst"
EOF
chmod +x "$stub_copy"

stub_noop="$scratch/stub-rename-noop.sh"
cat >"$stub_noop" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_noop"

run_with_rename_tool() {
  local MUTATION_RENAME_TOOL="$1"
  shift
  check_extraction_mutation "$@"
}

run_case() {
  local label="$1"
  shift
  local out_file="$scratch/stdout"
  local err_file="$scratch/stderr"
  local rc=0
  "$@" >"$out_file" 2>"$err_file" || rc=$?
  CASE_RC="$rc"
  CASE_OUT="$(cat "$out_file")"
  CASE_ERR="$(cat "$err_file")"
  CASE_LABEL="$label"
}

check_reference() {
  local name="$1"
  local ref="$2"
  local dir="$scratch/$name"
  mkdir -p "$dir"

  # 1. Copy of reference -> comparator exit 0 -> must FAIL.
  cp "$ref" "$dir/copy.v"
  run_case "$name: direct compare on copy of reference fails" \
    check_mutated_netlist_rejected "$dir/copy.v" "$ref"
  if [ "$CASE_RC" -ne 0 ] && grep -q 'comparator accepted' <<<"$CASE_ERR"; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stderr=$CASE_ERR)"
  fi

  run_case "$name: shared helper fails when mutated output equals reference" \
    run_with_rename_tool "$stub_copy" "$ref" "$dir/stub-copy.v" "$ref"
  if [ "$CASE_RC" -ne 0 ] \
      && grep -q 'comparator accepted' <<<"$CASE_ERR" \
      && ! grep -q '(ok)' <<<"$CASE_OUT"; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stdout=$CASE_OUT, stderr=$CASE_ERR)"
  fi

  # 2. One instance removed by tools/rename -> comparator exit 1 -> must PASS.
  run_case "$name: shared helper passes when tools/rename drops an instance" \
    check_extraction_mutation "$ref" "$dir/mutated.v" "$ref"
  if [ "$CASE_RC" -eq 0 ] \
      && [ -s "$dir/mutated.v" ] \
      && grep -q 'tools/rename: mutation drop-instance: deleted instance' <<<"$CASE_ERR" \
      && grep -q '(ok)' <<<"$CASE_OUT"; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stdout=$CASE_OUT, stderr=$CASE_ERR)"
  fi

  run_case "$name: direct compare on drop-instance netlist passes" \
    check_mutated_netlist_rejected "$dir/mutated.v" "$ref"
  if [ "$CASE_RC" -eq 0 ]; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stderr=$CASE_ERR)"
  fi

  # 3. Missing mutated-side file -> comparator exit 2 -> must FAIL with diagnostic.
  run_case "$name: direct compare on missing file fails with diagnostic" \
    check_mutated_netlist_rejected "$dir/missing.v" "$ref"
  if [ "$CASE_RC" -eq 2 ] \
      && grep -q 'exited 2' <<<"$CASE_ERR" \
      && grep -q 'tools/compare:' <<<"$CASE_ERR" \
      && grep -q 'No such file or directory' <<<"$CASE_ERR"; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stderr=$CASE_ERR)"
  fi

  run_case "$name: shared helper fails with diagnostic when mutated file is missing" \
    run_with_rename_tool "$stub_noop" "$ref" "$dir/unwritten.v" "$ref"
  if [ "$CASE_RC" -eq 2 ] \
      && grep -q 'exited 2' <<<"$CASE_ERR" \
      && grep -q 'tools/compare:' <<<"$CASE_ERR" \
      && grep -q 'No such file or directory' <<<"$CASE_ERR" \
      && ! grep -q '(ok)' <<<"$CASE_OUT"; then
    pass "$CASE_LABEL"
  else
    err "$CASE_LABEL (rc=$CASE_RC, stdout=$CASE_OUT, stderr=$CASE_ERR)"
  fi
}

echo "Extraction mutation check self-test"
echo "------------------------------------------------------------"

check_reference "warmup" "$ROOT/evidence/warmup-extracted.v"
check_reference "puzzle" "$ROOT/evidence/puzzle-extracted.v"

# 4. Mutation generation failure must fail even if a stale damaged file exists.
cp "$scratch/warmup/mutated.v" "$scratch/stale-mutated.v"
run_case "mutation failure fails even with stale damaged output on disk" \
  check_extraction_mutation "$scratch/no-such-input.v" "$scratch/stale-mutated.v" "$ROOT/evidence/warmup-extracted.v"
if [ "$CASE_RC" -ne 0 ] \
    && grep -q 'tools/rename:' <<<"$CASE_ERR" \
    && grep -q 'mutation generation' <<<"$CASE_ERR" \
    && ! grep -q '(ok)' <<<"$CASE_OUT"; then
  pass "$CASE_LABEL"
else
  err "$CASE_LABEL (rc=$CASE_RC, stdout=$CASE_OUT, stderr=$CASE_ERR)"
fi

# Netlist with no signal instances causes tools/rename to fail.
cat >"$scratch/no-signal.v" <<'EOF'
module empty (a, b);
  input a;
  output b;
  assign b = a;
endmodule
EOF
run_case "mutation failure on netlist with no signal instances surfaces diagnostic" \
  check_extraction_mutation "$scratch/no-signal.v" "$scratch/no-signal-mutated.v" "$ROOT/evidence/warmup-extracted.v"
if [ "$CASE_RC" -ne 0 ] \
    && grep -q 'no signal instances' <<<"$CASE_ERR" \
    && grep -q 'mutation generation' <<<"$CASE_ERR" \
    && ! grep -q '(ok)' <<<"$CASE_OUT"; then
  pass "$CASE_LABEL"
else
  err "$CASE_LABEL (rc=$CASE_RC, stdout=$CASE_OUT, stderr=$CASE_ERR)"
fi

# 5. Argument validation.
run_case "check_extraction_mutation rejects wrong argument count" \
  check_extraction_mutation "$ROOT/evidence/warmup-extracted.v" "$scratch/only-two.v"
if [ "$CASE_RC" -eq 2 ] && grep -q 'Usage:' <<<"$CASE_ERR"; then
  pass "$CASE_LABEL"
else
  err "$CASE_LABEL (rc=$CASE_RC, stderr=$CASE_ERR)"
fi

run_case "check_mutated_netlist_rejected rejects wrong argument count" \
  check_mutated_netlist_rejected "$ROOT/evidence/warmup-extracted.v"
if [ "$CASE_RC" -eq 2 ] && grep -q 'Usage:' <<<"$CASE_ERR"; then
  pass "$CASE_LABEL"
else
  err "$CASE_LABEL (rc=$CASE_RC, stderr=$CASE_ERR)"
fi

echo "------------------------------------------------------------"
if [ "$fail" -ne 0 ]; then
  echo "EXTRACTION MUTATION CHECK SELF-TEST FAILED" >&2
  exit 1
fi
echo "Extraction mutation check self-test passed."
