#!/usr/bin/env bash
# Session 75, U3b ship sequence (run by the orchestrator AFTER the final adversary verdict
# and AFTER PR #341 has merged). Steps: commit through the hook -> rebase onto origin/main
# -> post-rebase gates (FULL jest, tsc, the backend set) -> push -> PR -> the CLAUDE.md lines
# with the real PR number -> second commit -> push. Never checkout/stash/reset. Stops on the
# first failure. Usage: bash u3b_ship.sh <step>   where step in: commit rebase gates push pr claudemd
set -euo pipefail
SP="/c/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad"
WT=/c/Users/SynAckITPC/Documents/AI/sc-s74-ct
APP="$WT/SmartCompareApp"
PY=/c/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe
BRANCH=feature/s75-u3b-consent-v2
BE_FILES="tests/test_u3b_sharing_branch_removed.py tests/test_auth_ai_sharing_toggle.py tests/test_llm_provider_base_url.py tests/test_backend_cleanup.py tests/test_m18_openai_tpm_sizing.py tests/test_auth_preference_toggles_w314.py tests/test_s71_u13_compare_auth_required.py tests/test_openai_breaker.py tests/test_u3c_store_false_pin.py tests/test_model_config.py tests/test_model_config_enforced.py"
step="${1:?step}"
echo "== $(date +%H:%M:%S) step=$step =="
case "$step" in
  commit)
    [ -e "$WT/.qa-mutation.lock" ] && { echo "LOCK PRESENT"; exit 3; }
    git -C "$WT" add -A
    git -C "$WT" status --short
    git -C "$WT" commit -q -F "$SP/notes/commit_u3b.txt"
    git -C "$WT" log --oneline -1
    ;;
  rebase)
    git -C "$WT" fetch -q origin
    echo "main=$(git -C "$WT" rev-parse --short origin/main) branch=$(git -C "$WT" branch --show-current)"
    [ "$(git -C "$WT" branch --show-current)" = "$BRANCH" ] || { echo "WRONG BRANCH"; exit 3; }
    git -C "$WT" status --short | grep -q . && { echo "DIRTY TREE: commit first"; exit 3; }
    if ! git -C "$WT" rebase origin/main; then git -C "$WT" rebase --abort; echo "REBASE CONFLICT (aborted)"; exit 4; fi
    git -C "$WT" log --oneline -3
    ;;
  gates)
    ( cd "$APP" && ls node_modules/@babel/core node_modules/.bin/jest* >/dev/null && node node_modules/jest/bin/jest.js --version && node node_modules/typescript/bin/tsc --version )
    ( cd "$APP" && timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit ) && echo "tsc rc=0"
    ( cd "$APP" && timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci 2>&1 | tail -8 ) > "$SP/u3b/ship_full_jest.log"; tail -6 "$SP/u3b/ship_full_jest.log"
    grep -q "Tests:.* failed" "$SP/u3b/ship_full_jest.log" && { echo "FULL JEST RED"; exit 5; }
    git -C "$WT" status --short | grep -q "\.snap" && { echo "SNAPSHOT CHANGED"; exit 5; }
    ( cd "$WT" && PYTHONIOENCODING=utf-8 "$PY" "$SP/harness/pyt.py" --bound 1200 --tag u3b-ship-be --log "$SP/u3b/ship_be.log" --cwd "$WT" --tail 4 -- $BE_FILES -q ) | tail -5
    ;;
  push)
    git -C "$WT" push -u origin "$BRANCH" 2>&1 | tail -2
    ;;
  pr)
    ( cd "$WT" && PYTHONIOENCODING=utf-8 "$PY" "$SP/harness/pr_rest.py" create "$BRANCH" "U3b: AI consent v2 under D3 = C (the disclosure sentence, the dead Profile toggle removed, the private-key branch deleted)" "$SP/notes/pr_u3b_body.md" ) | tail -3
    ;;
  claudemd)
    PR="${2:?pr number}"
    git -C "$WT" show HEAD:CLAUDE.md | "$PY" "$SP/harness/claude_md_u3b_lines.py" --check "$PR"
    "$PY" "$SP/harness/claude_md_u3b_lines.py" "$WT/CLAUDE.md" "$PR" < "$WT/CLAUDE.md"
    git -C "$WT" diff --stat -- CLAUDE.md; git -C "$WT" diff --stat --ignore-cr-at-eol -- CLAUDE.md | tail -1
    sed "s/<PR>/$PR/g" "$SP/notes/commit_u3b_claude_md.txt" > "$SP/notes/commit_u3b_claude_md.filled.txt"
    git -C "$WT" add CLAUDE.md && git -C "$WT" commit -q -F "$SP/notes/commit_u3b_claude_md.filled.txt" && git -C "$WT" log --oneline -1
    git -C "$WT" push -q origin "$BRANCH" 2>&1 | tail -1; echo "pushed"
    ;;
  *) echo "unknown step"; exit 2;;
esac
echo "== $(date +%H:%M:%S) step=$step done =="
