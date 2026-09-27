#!/usr/bin/env bash
# Ship checks for W4-14 after the rebase onto main (DRAFT written before the red report; adjust UNIT /
# CLIENT_CI once the red records .qa-s68/ci_order_set.txt and the client set). Backend: unit files x5
# states + the CI-order set x2 states (ONE process per state) through the bounded runner, the netguard
# ratchet, ruff + py_compile, the must-not-touch diff gate. Client (from SmartCompareApp, BY PATH under
# the coreutils bound): the client CI-order set, the FULL jest suite (no -u), tsc --noEmit, eslint.
# Usage: bash ship_w414.sh
set -u
NSP="C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
WT="C:/Users/SynAckITPC/Documents/AI/sc-w4-14"
OUT="$NSP/ship_w414"
mkdir -p "$OUT"
cd "$WT" || exit 2
UNIT="tests/test_dimension_label_catalog_parity_w414.py tests/test_arabic_verdict_output_w414.py"
{ cat .qa-s68/ci_order_set.txt 2>/dev/null; for f in $UNIT; do echo "$f"; done; } | tr -d '\r' | sed 's#^\./##' | grep '^tests/' | sort -u > "$OUT/ci_set.txt"
CI=$(tr '\n' ' ' < "$OUT/ci_set.txt")
echo "[ship] backend CI-order set: $(wc -l < "$OUT/ci_set.txt") files"
DESEL=""
if [ -f tests/.pre_impl_failures.txt ]; then
  DESEL=$(grep '::' tests/.pre_impl_failures.txt | grep -v '^[[:space:]]*#' | tr -d '\r' | sed 's/^[[:space:]]*//; s/^/--deselect=/' | tr '\n' ' ')
fi
FLAGS="-u ENABLE_ARABIC_VERDICT_OUTPUT -u ENABLE_VERDICT_PROMPT_TRUTH -u ENABLE_COHORT_PERSONALIZATION -u ENABLE_SELF_CRITIQUE -u ENABLE_GPT_WINNER"
run_unit () {
  local name="$1"; shift
  echo "[ship] === backend unit state $name: $* ==="
  env $FLAGS "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 600 --tag "ship-w414-unit-$name" --log "$OUT/unit_$name.log" --cwd "$WT" -- $UNIT -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
}
run_ci () {
  local name="$1"; shift
  echo "[ship] === backend CI-order state $name: $* ==="
  env $FLAGS QAREN_NETGUARD_REPORT="$OUT/netguard_$name.json" "$@" \
    "$PY" "$NSP/harness/pyt.py" --bound 1500 --tag "ship-w414-ci-$name" --log "$OUT/ci_$name.log" --cwd "$WT" -- $CI $DESEL -q 2>&1 | grep -E '^\[pyt\] tag|passed|failed|error' | tail -n 3
  "$PY" scripts/netguard_ratchet.py "$OUT/netguard_$name.json" tests/.network_attempt_baseline.txt 2>&1 | grep -v shrink | tail -n 2
}
run_unit unset
run_unit AR ENABLE_ARABIC_VERDICT_OUTPUT=true
run_unit AR_TRUTH ENABLE_ARABIC_VERDICT_OUTPUT=true ENABLE_VERDICT_PROMPT_TRUTH=true
run_unit TRUTH ENABLE_VERDICT_PROMPT_TRUTH=true
run_unit AR_COHORT ENABLE_ARABIC_VERDICT_OUTPUT=true ENABLE_COHORT_PERSONALIZATION=true
run_ci unset
run_ci AR ENABLE_ARABIC_VERDICT_OUTPUT=true
echo "[ship] === ruff + py_compile ==="
BACK="app/api/text_routes.py app/services/structured_comparison_service.py app/services/extraction_service.py"
"$PY" -m ruff check --select E9,F63,F7,F82 $BACK $UNIT 2>&1 | tail -n 2
for f in $BACK; do "$PY" -m py_compile "$f" || echo "[ship] py_compile FAILED $f"; done
echo "[ship] py_compile done"
echo "[ship] === must-not-touch diff gate vs the merge base ==="
BASE=$(git merge-base HEAD origin/main)
echo "[ship] merge-base $BASE"
git diff --stat "$BASE" HEAD -- app/services/prompt_personalities.py app/services/response_builder.py app/services/scoring_service.py \
  tests/.network_attempt_baseline.txt tests/fixtures/w4_11_prompt_render_digests.json tests/.pre_impl_failures.txt \
  SmartCompareApp/src/utils/formatNumber.ts SmartCompareApp/src/utils/currencyDisplay.ts SmartCompareApp/src/components/results/ResultsContent.tsx \
  SmartCompareApp/src/screens/HistoryScreen.tsx SmartCompareApp/src/components/results/ResultsAccordion.tsx SmartCompareApp/src/components/results/PersonalizationChip.tsx \
  SmartCompareApp/src/components/results/CategoryProfile.tsx SmartCompareApp/src/utils/_deltaText.ts SmartCompareApp/app.json SmartCompareApp/eas.json \
  SmartCompareApp/package.json SmartCompareApp/package-lock.json requirements.txt | tail -n 1
echo "[ship] (empty above = gate OK)"
git diff --stat "$BASE" HEAD -- '*.snap' | tail -n 1
echo "[ship] (empty above = no snapshot moved)"
git diff --stat "$BASE" HEAD | tail -n 1
echo "[ship] === client (SmartCompareApp, by path, bounded) ==="
cd "$WT/SmartCompareApp" || exit 2
node --version; node node_modules/jest/bin/jest.js --version; node node_modules/typescript/bin/tsc --version
# the client half of the red's recorded CI-order set (entries prefixed SmartCompareApp/), fallback = the spec 9.5 list
CLIENT_CI=$(tr -d '\r' < "$WT/.qa-s68/ci_order_set.txt" 2>/dev/null | grep '^SmartCompareApp/' | sed 's#^SmartCompareApp/##' | tr '\n' ' ')
if [ -z "$CLIENT_CI" ]; then
  CLIENT_CI="__tests__/i18n __tests__/i18n.test.ts __tests__/copy-policy.test.ts __tests__/components/DimensionBars.snapshot.test.tsx __tests__/DimensionBars.bundle-c.test.tsx __tests__/components/DimensionBars.arabicLabels.w414.test.tsx __tests__/components/DimensionBars.globalMockLabel.w414.test.tsx __tests__/api.outputLang.w414.test.ts __tests__/api.streamComparison.noBodyFallback.test.ts"
fi
echo "[ship] client CI-order set: $(echo $CLIENT_CI | wc -w) entries"
timeout -k 15 600 node node_modules/jest/bin/jest.js --ci $CLIENT_CI > "$OUT/client_ci.log" 2>&1; echo "[ship] client CI exit $?"; grep -E '^(Tests|Test Suites|Snapshots):' "$OUT/client_ci.log"
echo "[ship] FULL jest suite (the arbiter; no -u)"
timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci > "$OUT/client_full.log" 2>&1; echo "[ship] full jest exit $?"; grep -E '^(Tests|Test Suites|Snapshots):' "$OUT/client_full.log"
echo "[ship] tsc --noEmit"
timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit --pretty false > "$OUT/tsc.log" 2>&1; echo "[ship] tsc exit $? ($(wc -l < "$OUT/tsc.log") lines)"
echo "[ship] eslint"
timeout -k 15 600 node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}" > "$OUT/eslint.log" 2>&1; echo "[ship] eslint exit $?"; grep -E 'problems?' "$OUT/eslint.log" | tail -n 1
echo "[ship] ALL DONE"
