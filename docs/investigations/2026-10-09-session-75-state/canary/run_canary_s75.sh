#!/usr/bin/env bash
# Session 74 post-funding canary (repointed 2026-10-08 21:05 after BE-HARNESS, PR #338).
# Runs scripts/verify_after_credits.py with the web service's environment injected by
# `railway run` (ADMIN_API_KEY never typed, never printed). The script enforces the
# runbook A1.8 rule and ends with a `RESULT:` line; exit 0 PASS / 1 FAIL / 3 NO_PRICE /
# 4 SETUP / 5 CRASH. Through the npm `railway run` wrapper every non-zero exit reads as 1,
# so this wrapper classifies the run by the RESULT line, never by the shell rc alone.
set -u
SP="/c/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f9970d11-1fa0-400e-9fb3-dd91f335e519/scratchpad"
# The docs worktree tracks main through the docs branches; any worktree at or after #338 works.
CANARY="C:/Users/SynAckITPC/Documents/AI/sc-docs-70/scripts/verify_after_credits.py"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
TAG="${1:-canary1}"
shift || true
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="$SP/canary/${TAG}_${STAMP}.log"
REPORT="$SP/canary/${TAG}_${STAMP}.json"
[ -f "$CANARY" ] || { echo "[canary] tag=$TAG verdict=SETUP canary script missing at $CANARY (is the docs worktree at or after #338?)"; exit 4; }
cd /c/Users/SynAckITPC/Documents/AI/smartcompare || exit 4
echo "[canary] tag=$TAG start=$(date +%H:%M:%S) script=$CANARY" | tee "$LOG"
# FANOUT-STARVE FS-R5 / FG-1 (2026-10-09): the script's default stays today's q rows; the
# wrapper passes --form both so every curated pair also runs in the app-shaped pair form
# (a later --form on the command line wins). Needs a script at or after FANOUT-STARVE.
PYTHONIOENCODING=utf-8 timeout -k 15 900 railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 PYTHONIOENCODING=utf-8 "$PY" "$CANARY" --report "$REPORT" --form both "$@" 2>&1 | grep -v -i -E "api[_-]?key=|token=|secret=|password=|sk-[A-Za-z0-9_-]{20,}" | tee -a "$LOG"
rc=${PIPESTATUS[0]}
# Classification: the report's exit field (0 PASS / 1 FAIL / 3 NO_PRICE / 4 SETUP / 5 CRASH) is the
# authority; the RESULT line is the fallback (a crash or a timeout may leave no report).
code=""
[ -f "$REPORT" ] && code="$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1]))['exit'])" "$REPORT" 2>/dev/null)"
result="$(grep -E '^RESULT:' "$LOG" | tail -1)"
# FY15: a Windows pipe can emit CRLF; strip a trailing CR so "RESULT: PASS" still reads PASS.
result="${result%$'\r'}"
case "$code" in
  0) verdict=PASS ;;
  1) verdict=FAIL ;;
  3) verdict=NO_PRICE ;;
  4) verdict=SETUP ;;
  5) verdict=CRASH ;;
  *) case "$result" in
       "RESULT: PASS"|"RESULT: PASS "*)  verdict=PASS ;;  # FG-2: --form both appends q_fail= pair_fail=
       RESULT:*setup=*) verdict=SETUP ;;
       "RESULT: FAIL error="*)  verdict=CRASH ;;  # FY29: the script's crash line is 'RESULT: FAIL error=<Class>' (never 'crash')
       RESULT:*)        verdict=FAIL ;;
       "")              verdict="NO_RESULT_LINE (treat as FAIL; rc=$rc; a timeout or a crash prints none)" ;;
     esac ;;
esac
echo "[canary] tag=$TAG end=$(date +%H:%M:%S) rc=$rc exit=${code:-none} verdict=$verdict result='$result' log=$LOG" | tee -a "$LOG"
