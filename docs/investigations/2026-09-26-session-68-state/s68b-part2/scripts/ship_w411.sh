#!/usr/bin/env bash
# Ship checks for W4-11 after the rebase onto main: unit files x4 states, the CI-order set x4 states
# (ONE process per state), the netguard ratchet, ruff + py_compile. Every pytest run goes through the
# bounded runner. Usage: bash ship_w411.sh
set -u
NSP="C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
WT="C:/Users/SynAckITPC/Documents/AI/sc-w4-11"
OUT="$NSP/ship_w411"
mkdir -p "$OUT"
cd "$WT" || exit 2
UNIT="tests/test_prompt_fence.py tests/test_prompt_truth.py tests/test_model_config_enforced.py tests/test_price_fallback_may_decline.py"
# the CI-order set: the gitignored list + test_wall_caps_i57 (amended pin) + the unit files, sorted like CI
{ cat .qa-s68/ci_order_set.txt; echo tests/test_wall_caps_i57.py; echo tests/test_retro_w0_4_efg.py; for f in $UNIT; do echo "$f"; done; } | tr -d '\r' | sed 's#^\./##' | sort -u > "$OUT/ci_set.txt"
CI=$(tr '\n' ' ' < "$OUT/ci_set.txt")
echo "[ship] CI-order set: $(wc -l < "$OUT/ci_set.txt") files"
run_state () {
  local name="$1"; shift
  echo "[ship] === state $name: $* ==="
  env -u ENABLE_VERDICT_PROMPT_TRUTH -u ENABLE_PRICE_FALLBACK_MAY_DECLINE "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 600 --tag "ship-w411-unit-$name" --log "$OUT/unit_$name.log" --cwd "$WT" -- $UNIT -q 2>&1 | grep -E '^\[pyt\]|passed|failed|error' | tail -n 3
  env -u ENABLE_VERDICT_PROMPT_TRUTH -u ENABLE_PRICE_FALLBACK_MAY_DECLINE QAREN_NETGUARD_REPORT="$OUT/netguard_$name.json" "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 1500 --tag "ship-w411-ci-$name" --log "$OUT/ci_$name.log" --cwd "$WT" -- $CI -q 2>&1 | grep -E '^\[pyt\]|passed|failed|error' | tail -n 3
  "$PY" scripts/netguard_ratchet.py "$OUT/netguard_$name.json" tests/.network_attempt_baseline.txt 2>&1 | tail -n 2
}
run_state unset
run_state truth ENABLE_VERDICT_PROMPT_TRUTH=true
run_state decline ENABLE_PRICE_FALLBACK_MAY_DECLINE=true
run_state both ENABLE_VERDICT_PROMPT_TRUTH=true ENABLE_PRICE_FALLBACK_MAY_DECLINE=true
echo "[ship] === ruff + py_compile ==="
"$PY" -m ruff check --select E9,F63,F7,F82 app/services/extraction_service.py app/services/image_service.py app/services/openai_service.py app/services/prompt_personalities.py app/services/url_extraction_service.py app/services/verdict_critique_service.py tests/test_prompt_fence.py tests/test_prompt_truth.py tests/test_model_config_enforced.py tests/test_price_fallback_may_decline.py tests/w4_11_prompt_digest_recorder.py tests/test_retro_w0_4_efg.py tests/test_wall_caps_i57.py 2>&1 | tail -n 3
for f in app/services/extraction_service.py app/services/image_service.py app/services/openai_service.py app/services/prompt_personalities.py app/services/url_extraction_service.py app/services/verdict_critique_service.py; do "$PY" -m py_compile "$f" || echo "[ship] py_compile FAILED $f"; done
echo "[ship] py_compile done"
echo "[ship] === digest gate (T-G1 + recorder) ==="
env -u ENABLE_VERDICT_PROMPT_TRUTH -u ENABLE_PRICE_FALLBACK_MAY_DECLINE "$PY" "$NSP/harness/pyt.py" --bound 600 --tag "ship-w411-digest" --log "$OUT/digest.log" --cwd "$WT" -- tests/test_prompt_fence.py -q -k "digest or G1" 2>&1 | grep -E '^\[pyt\]|passed|failed|error|no tests' | tail -n 3
echo "[ship] ALL DONE"
