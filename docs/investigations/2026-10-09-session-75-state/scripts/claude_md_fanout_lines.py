"""Session 75, unit FANOUT-STARVE: the CLAUDE.md lines written by the orchestrator
at merge (the flag rows, the configuration-truth bullet, the comm-gate lesson of
PR #341). Same contract as claude_md_u3b_lines.py: stdin = CLAUDE.md bytes;
--check dry-runs; argv[1] = output path, argv[2] = PR number. Every edit must
match EXACTLY once. Anchors assume the U3b bullet (PR #342) is already in the
SESSION 73 block, i.e. the branch is rebased onto the post-#342 main."""
import sys

PR = sys.argv[2] if len(sys.argv) > 2 else "<PR>"

U3B_BULLET_TAIL = "Follow-ups (UY6): the 'Privacy' eyebrow and the Step 5 headline (LISTING-TRUTH), the inventory purposes + the stale row-12 `api.ts` anchors, the native re-pin unit."

FANOUT_BULLET = (
    "\n- **FANOUT-STARVE (session 75, PR #" + PR + "; four dark flags + configuration truth; spec / rulings FS-R1..R20, FG-1..FG-10, FY1-FYn in the session-75 state folder):** "
    "UNFLAGGED and flag-OFF byte-identical on every response: `ADAPTER_EXECUTOR_MAX_WORKERS` default 40 -> **96** (web since 2026-10-08; ~30 blocking adapter fetches per compare under `ENABLE_BH_GCC_CATALOG_SOURCES` saturated 40 and the adapter TIMEOUT drops were the queue); the Serper fail-fast connect default 3.0 -> **8.0 s** (`SERPER_CONNECT_TIMEOUT`; under uvloop the connect budget includes a getaddrinfo that queues on libuv's 4-thread default pool); the start command in `railway.json` AND `Procfile` (a byte-identical pair) is `exec env UV_THREADPOOL_SIZE=\"${UV_THREADPOOL_SIZE:-64}\" uvicorn ...`, proven by the `[loop] class=... uvloop=... UV_THREADPOOL_SIZE=...` INFO line at startup; one `[STAGE] parse done elapsed_ms=<int> mode=llm|presplit|fallback` INFO per q-form parse; Bright Data auth rejection = ONE ERROR per process per status (401 / 403) naming `BRIGHTDATA_API_KEY` (renewal: `docs/runbooks/brightdata-token-renewal.md`), the 401/403 WARNING body withheld; `/health` gains `adapter_executor` {workers, queued} and, after a 401/403 only, `brightdata_auth` {last_status, at}. "
    "FOUR NEW FLAGS, default OFF, read PER CALL, knobs reject unset / garbage / nan / inf / <= 0: `ENABLE_PARSE_PRESPLIT` (a q-form query splitting cleanly on its first case-insensitive \" vs \" takes the app's explicit-pair shape with NO parse LLM call: brand \"\", keyword category, `parser_path` False, `metadata.parse_presplit`); `ENABLE_PARSE_BUDGET` + `PARSE_TIMEOUT_SECONDS` (8.0; a stall guard on `parse_product_query`: on timeout the same split with `metadata.parse_fallback`, or today's parse-failure body without a \" vs \"); `ENABLE_UNIFIED_SEARCH_BOUND` + `UNIFIED_SEARCH_TIMEOUT_SECONDS` (12.0; on timeout specs/reviews get an explicit EMPTY payload, never None); `ENABLE_PHASE2_RESIDUAL_GUARD` + `PHASE2_MIN_RESIDUAL_SECONDS` (8.0; a product within that residual of the compare deadline skips the verified rating and the smart-fallback refill so the compare reaches scoring and a verdict; `metadata.phase2_skipped`). An LLM parse JSON cannot forge the marks (its `_parse_*` keys are stripped; each mark counts only under its own flag). "
    "Canary D9: `scripts/verify_after_credits.py --form q|pair|both` (default = today's rows byte for byte; `both` = each pair in both forms, RESULT line ends ` q_fail=<n> pair_fail=<n>`, the q rows drive the exit only under `--strict-q`); `run_canary.sh` passes `--form both`. "
    "Stated limits: the libuv pool size is proven only by the first-deploy boot line (uvloop is absent on Windows); `price-warmer` gets D1 nothing and D4/D6 only per cron run; under the parse flags a q-form compare loses the LLM identity (brand, variant, full-context category); flag OFF, D4 widens the unbounded unified search's worst case 27 -> 32 s on a 3-key rotation (D5 closes it). **Flips are the owner's, one per canary window, after canary 7** (`run_canary.sh canary7a` then `--form both`); FANOUT-BOUND (D3) is the deferred follow-up."
)

GATE_RULE_TAIL = "Where installing the pin is not allowed, write the assertion so it runs on whatever version is present and let CI settle it on the pinned build; say in the report which version the local number came from."

GATE_RULE_ADD = (
    "\n- **Every backend comm set includes the SOURCE-SCANNING pins (session 75, PR #341):** the tests that glob or read `app/` (or the start command) as source -- `tests/test_model_config.py` (the stray-model-literal pin), `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command*.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py` -- reference no changed module by name, so a set chosen by grep-reference can never pick them: COST-METER's 151-file set, two adversaries and a final adversary were green and CI went red on ONE node after 14 minutes (the five exact-key model ids of the new price table). Union the set with those files at HEAD; an allowlist entry for a DATA table (not a dispatch site) is fine with the reason in the comment (ruling X15). The twin of the mobile rule for tests that scan `SmartCompareApp/`."
)

EDITS = [(U3B_BULLET_TAIL, U3B_BULLET_TAIL + FANOUT_BULLET), (GATE_RULE_TAIL, GATE_RULE_TAIL + GATE_RULE_ADD)]


def main() -> int:
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    check = "--check" in sys.argv[1:]
    ok = True
    for old, new in EDITS:
        n = text.count(old)
        print(f"match x{n}: {old[:70]!r}")
        if n != 1:
            ok = False
    if not ok:
        print("NOT APPLIED: an edit does not match exactly once")
        return 2
    if check:
        print("dry run OK")
        return 0
    for old, new in EDITS:
        text = text.replace(old, new.replace("\n", nl), 1)
    with open(sys.argv[1], "wb") as fh:
        fh.write(text.encode("utf-8"))
    print("written", sys.argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
