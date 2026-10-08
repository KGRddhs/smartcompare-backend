#!/usr/bin/env bash
# Session 74 post-funding canary. Runs the session-69 script with the web service's
# environment injected by `railway run` (ADMIN_API_KEY never typed, never printed).
set -u
SP="/c/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad"
CANARY="C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-09-29-session-69-state/verify_after_credits.py"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
TAG="${1:-canary1}"
LOG="$SP/canary/${TAG}_$(date +%Y%m%d_%H%M%S).log"
cd /c/Users/SynAckITPC/Documents/AI/smartcompare || exit 2
echo "[canary] tag=$TAG start=$(date +%H:%M:%S)" | tee "$LOG"
PYTHONIOENCODING=utf-8 timeout -k 15 600 railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 PYTHONIOENCODING=utf-8 "$PY" "$CANARY" 2>&1 | grep -v -i -E "api[_-]?key|token|secret|password" | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "[canary] tag=$TAG end=$(date +%H:%M:%S) rc=$rc log=$LOG" | tee -a "$LOG"
