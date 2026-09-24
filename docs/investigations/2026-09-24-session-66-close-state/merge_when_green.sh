#!/usr/bin/env bash
# merge_when_green.sh <pr-number> [max-minutes]
# Polls the PR's checks; merges with a merge commit once every check passes.
# Never enables auto-merge. Prints the state on every poll.
set -u
PR="$1"; MAXMIN="${2:-90}"
cd "C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof" || exit 2
deadline=$(( $(date +%s) + MAXMIN*60 ))
while :; do
  state=$(gh pr view "$PR" --json state,mergeStateStatus -q '.state+" "+.mergeStateStatus' 2>/dev/null)
  case "$state" in
    MERGED*) echo "PR #$PR already MERGED"; exit 0;;
    CLOSED*) echo "PR #$PR is CLOSED"; exit 3;;
  esac
  checks=$(gh pr checks "$PR" 2>/dev/null)
  total=$(printf '%s\n' "$checks" | grep -cE '^\S' || true)
  passed=$(printf '%s\n' "$checks" | grep -cE $'\tpass\t' || true)
  failed=$(printf '%s\n' "$checks" | grep -cE $'\t(fail|error|cancelled)\t' || true)
  echo "$(date +%H:%M:%S) PR #$PR state=[$state] checks total=$total passed=$passed failed=$failed"
  if [ "$failed" -gt 0 ]; then
    echo "FAILED CHECKS:"; printf '%s\n' "$checks" | grep -E $'\t(fail|error|cancelled)\t'; exit 4
  fi
  if [ "$total" -ge 5 ] && [ "$passed" -eq "$total" ]; then
    for attempt in 1 2 3 4 5; do
      if gh pr merge "$PR" --merge 2>&1; then :; fi
      sleep 20
      st=$(gh pr view "$PR" --json state -q .state 2>/dev/null)
      if [ "$st" = "MERGED" ]; then echo "PR #$PR MERGED"; git fetch origin -q; echo "origin/main now $(git rev-parse --short origin/main)"; exit 0; fi
      echo "merge attempt $attempt: state=$st, retrying"
    done
    echo "could not merge PR #$PR after 5 attempts"; exit 5
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then echo "timeout waiting for PR #$PR"; exit 6; fi
  sleep 90
done
