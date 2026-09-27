#!/usr/bin/env bash
# Ship checks for W4-7 after the rebase onto main: unit files x6 states, the CI-order set x6 states
# (ONE process per state), the netguard ratchet, the R14 diff gate, ruff + py_compile. Every pytest
# run goes through the bounded runner. Usage: bash ship_w47.sh
set -u
NSP="C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
WT="C:/Users/SynAckITPC/Documents/AI/sc-w4-7"
OUT="$NSP/ship_w47"
mkdir -p "$OUT"
cd "$WT" || exit 2
UNIT="tests/test_w4_7_reliability_unchecked_absence.py tests/test_w4_7_confidence_single_computation.py tests/test_w4_7_factcheck_shopping_key.py"
{ cat .qa-s68/ci_order_set.txt; for f in $UNIT; do echo "$f"; done; } | tr -d '\r' | sed 's#^\./##' | sort -u > "$OUT/ci_set.txt"
CI=$(tr '\n' ' ' < "$OUT/ci_set.txt")
echo "[ship] CI-order set: $(wc -l < "$OUT/ci_set.txt") files"
DESEL=""
if [ -f tests/.pre_impl_failures.txt ]; then
  DESEL=$(grep '::' tests/.pre_impl_failures.txt | grep -v '^[[:space:]]*#' | tr -d '\r' | sed 's/^[[:space:]]*//; s/^/--deselect=/' | tr '\n' ' ')
fi
FLAGS="-u ENABLE_RELIABILITY_UNCHECKED_ABSENCE -u ENABLE_MISSING_DIM_RENORM -u ENABLE_CONFIDENCE_SINGLE_COMPUTATION -u ENABLE_FACTCHECK_SHOPPING_KEY"
run_state () {
  local name="$1"; shift
  echo "[ship] === state $name: $* ==="
  env $FLAGS "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 600 --tag "ship-w47-unit-$name" --log "$OUT/unit_$name.log" --cwd "$WT" -- $UNIT -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
  env $FLAGS QAREN_NETGUARD_REPORT="$OUT/netguard_$name.json" "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 1500 --tag "ship-w47-ci-$name" --log "$OUT/ci_$name.log" --cwd "$WT" -- $CI $DESEL -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
  "$PY" scripts/netguard_ratchet.py "$OUT/netguard_$name.json" tests/.network_attempt_baseline.txt 2>&1 | grep -v shrink | tail -n 2
}
run_state unset
run_state A ENABLE_RELIABILITY_UNCHECKED_ABSENCE=true ENABLE_MISSING_DIM_RENORM=true
run_state Anorenorm ENABLE_RELIABILITY_UNCHECKED_ABSENCE=true
run_state B ENABLE_CONFIDENCE_SINGLE_COMPUTATION=true
run_state C ENABLE_FACTCHECK_SHOPPING_KEY=true
run_state ALL ENABLE_RELIABILITY_UNCHECKED_ABSENCE=true ENABLE_MISSING_DIM_RENORM=true ENABLE_CONFIDENCE_SINGLE_COMPUTATION=true ENABLE_FACTCHECK_SHOPPING_KEY=true
echo "[ship] === ruff + py_compile ==="
"$PY" -m ruff check --select E9,F63,F7,F82 app/services/scoring_service.py app/services/response_builder.py app/services/structured_comparison_service.py $UNIT 2>&1 | tail -n 2
for f in app/services/scoring_service.py app/services/response_builder.py app/services/structured_comparison_service.py; do "$PY" -m py_compile "$f" || echo "[ship] py_compile FAILED $f"; done
echo "[ship] py_compile done"
echo "[ship] === R14 diff gate (price_service / fact_check_service / rating_service untouched vs the merge base) ==="
BASE=$(git merge-base HEAD origin/main)
echo "[ship] merge-base $BASE"
git diff --stat "$BASE" HEAD -- app/services/price_service.py app/services/fact_check_service.py app/services/rating_service.py | tail -n 1
echo "[ship] (empty above = gate OK)"
git diff --stat "$BASE" HEAD -- app/ | tail -n 4
echo "[ship] ALL DONE"
