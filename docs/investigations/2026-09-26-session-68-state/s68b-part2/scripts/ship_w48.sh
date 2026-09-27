#!/usr/bin/env bash
# Ship checks for W4-8 after the rebase onto main: unit files x4 states, the CI-order set x4 states
# (ONE process per state), the netguard ratchet, ruff + py_compile + json.load. Every pytest run goes
# through the bounded runner. This worktree predates the conftest guard unless the rebase brought it
# in (it does: main >= 4cff9bc1 wires tests/_netguard.py), so the runner decides the plugin itself.
set -u
NSP="C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
WT="C:/Users/SynAckITPC/Documents/AI/sc-w4-8"
OUT="$NSP/ship_w48"
mkdir -p "$OUT"
cd "$WT" || exit 2
UNIT="tests/test_category_token_fix.py tests/test_content_blocklist_arabic_parity.py tests/test_blocklist_collision_audit.py"
{ cat .qa-s68/ci_order_set.txt; for f in $UNIT; do echo "$f"; done; } | tr -d '\r' | sed 's#^\./##' | sort -u > "$OUT/ci_set.txt"
CI=$(tr '\n' ' ' < "$OUT/ci_set.txt")
echo "[ship] CI-order set: $(wc -l < "$OUT/ci_set.txt") files"
DESEL=""
if [ -f tests/.pre_impl_failures.txt ]; then
  DESEL=$(grep '::' tests/.pre_impl_failures.txt | grep -v '^[[:space:]]*#' | tr -d '\r' | sed 's/^[[:space:]]*//; s/^/--deselect=/' | tr '\n' ' ')
fi
FLAGS="-u ENABLE_CATEGORY_TOKEN_FIX -u ENABLE_BLOCKLIST_PRECISION_V2"
run_state () {
  local name="$1"; shift
  echo "[ship] === state $name: $* ==="
  env $FLAGS "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 600 --tag "ship-w48-unit-$name" --log "$OUT/unit_$name.log" --cwd "$WT" -- $UNIT -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
  env $FLAGS QAREN_NETGUARD_REPORT="$OUT/netguard_$name.json" "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 1500 --tag "ship-w48-ci-$name" --log "$OUT/ci_$name.log" --cwd "$WT" -- $CI $DESEL -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
  if [ -f "$OUT/netguard_$name.json" ]; then "$PY" scripts/netguard_ratchet.py "$OUT/netguard_$name.json" tests/.network_attempt_baseline.txt 2>&1 | grep -v shrink | tail -n 2; else echo "[ship] no netguard report for $name (plugin run)"; fi
}
run_state unset
run_state A ENABLE_CATEGORY_TOKEN_FIX=true
run_state B ENABLE_BLOCKLIST_PRECISION_V2=true
run_state both ENABLE_CATEGORY_TOKEN_FIX=true ENABLE_BLOCKLIST_PRECISION_V2=true
echo "[ship] === ruff + py_compile + json.load ==="
"$PY" -m ruff check --select E9,F63,F7,F82 app/services/extraction_service.py app/services/content_safety_service.py $UNIT 2>&1 | tail -n 2
for f in app/services/extraction_service.py app/services/content_safety_service.py; do "$PY" -m py_compile "$f" || echo "[ship] py_compile FAILED $f"; done
"$PY" -c "import json,sys; d=json.load(open('app/data/content_blocklist.json',encoding='utf-8')); print('[ship] json ok version', d.get('version'), 'v2 keys', sorted(d.get('v2',{}).keys()))"
echo "[ship] === diff gate ==="
BASE=$(git merge-base HEAD origin/main)
echo "[ship] merge-base $BASE"
git diff --stat "$BASE" HEAD -- app/ | tail -n 4
echo "[ship] ALL DONE"
