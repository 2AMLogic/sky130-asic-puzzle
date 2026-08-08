#!/usr/bin/env bash
# Guard the boundary this repo commits to: private until 2026-09-04.
#
# This checks the things a script CAN check. It cannot read prose and decide
# whether a sentence is a spoiler. See CLAUDE.md §1 — if you are unsure whether
# something may leave this repo, it may not.
set -uo pipefail

EMBARGO_UNTIL="2026-09-04"
fail=0
today=$(date -u +%Y-%m-%d)

echo "Embargo check — today $today, embargo lifts $EMBARGO_UNTIL"
echo

if [[ "$today" > "$EMBARGO_UNTIL" || "$today" == "$EMBARGO_UNTIL" ]]; then
  echo "Embargo has LIFTED. Publishing is invited; see CLAUDE.md §1."
  echo "Re-check by hand that going public is what you intend."
  exit 0
fi

# 1. This repo must still be private.
slug=$(git config --get remote.origin.url 2>/dev/null \
       | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
if [ -z "$slug" ]; then
  echo "  SKIP  no origin remote — cannot check visibility"
else
  vis=$(gh repo view "$slug" --json visibility --jq '.visibility' 2>/dev/null || echo "UNKNOWN")
  case "$vis" in
    PRIVATE) echo "  ok    $slug is PRIVATE" ;;
    UNKNOWN) echo "  SKIP  could not read visibility for $slug (auth?)" ;;
    *)       echo "  FAIL  $slug is $vis — must be PRIVATE until $EMBARGO_UNTIL"; fail=1 ;;
  esac
fi

# 2. No remote here may point at a public repo — that is the copy-out path.
while read -r name url; do
  [ -z "${url:-}" ] && continue
  s=$(printf '%s' "$url" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
  case "$s" in
    */*) ;;
    *) continue ;;
  esac
  v=$(gh repo view "$s" --json visibility --jq '.visibility' 2>/dev/null || echo "UNKNOWN")
  if [ "$v" = "PUBLIC" ]; then
    echo "  FAIL  remote '$name' -> $s is PUBLIC; pushing there leaks the subject"; fail=1
  fi
done < <(git remote -v | awk '$3=="(push)" {print $1, $2}')

# 3. The upstream puzzle files must not be tracked (no license, and they are
#    the subject itself).
tracked=$(git ls-files | grep -E '^puzzle/|(^|/)puzzle\.gds$|(^|/)example_inputs\.vcd$' || true)
if [ -n "$tracked" ]; then
  echo "  FAIL  upstream puzzle files are tracked:"
  printf '        %s\n' $tracked
  fail=1
else
  echo "  ok    no upstream puzzle files tracked"
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "EMBARGO CHECK FAILED" >&2
  exit 1
fi
echo "Embargo check passed. Prose is still your judgement, not this script's."
