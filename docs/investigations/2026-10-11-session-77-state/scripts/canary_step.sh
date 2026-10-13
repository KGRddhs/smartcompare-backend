#!/usr/bin/env bash
# Session-77 load-flag canary: one cold compare set while /health is polled for event-loop lag.
# Usage: canary_step.sh <label> "<A vs B>" ["<C vs D>" ...]
# Writes runs/canary_<label>.{txt,json,health.txt} next to this script's parent folder and prints a
# one-line summary: max loop_lag_max_60s_ms seen, /health timeouts, and the warm-up RESULT line.
# Runs the warm-up as the admin caller through `railway run` (the key is read in-process, never printed).
set -u
LABEL="$1"; shift
HERE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="/c/Users/SynAckITPC/Documents/AI/sc-docs-70"
PY="C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe"
OUT="$HERE/runs"; mkdir -p "$OUT"
HEALTH="$OUT/canary_${LABEL}.health.txt"; : > "$HEALTH"
(
  while [ ! -f "$OUT/.stop_${LABEL}" ]; do
    printf '%s ' "$(date +%T)" >> "$HEALTH"
    curl -s --max-time 5 -w ' t=%{time_total}\n' https://web-production-58776.up.railway.app/health >> "$HEALTH" || echo " TIMEOUT" >> "$HEALTH"
    sleep 1
  done
) &
POLL=$!
( cd "$REPO" && PYTHONIOENCODING=utf-8 timeout 900 railway run -s web -- "$PY" scripts/review_warmup.py \
    --send-admin-key --runs 1 --pace 5 --report "$OUT/canary_${LABEL}.json" --pairs "$@" ) > "$OUT/canary_${LABEL}.txt" 2>&1
sleep 3; touch "$OUT/.stop_${LABEL}"; wait "$POLL" 2>/dev/null; rm -f "$OUT/.stop_${LABEL}"
MAXLAG=$(grep -oE '"loop_lag_max_60s_ms":[0-9.]+' "$HEALTH" | cut -d: -f2 | sort -g | tail -1)
TIMEOUTS=$(grep -cvE '"status"' "$HEALTH")
RESULT=$(grep '^RESULT:' "$OUT/canary_${LABEL}.txt" | tail -1)
echo "CANARY ${LABEL}: max_loop_lag_60s_ms=${MAXLAG:-n/a} health_misses=${TIMEOUTS} ${RESULT:-RESULT: none}"
