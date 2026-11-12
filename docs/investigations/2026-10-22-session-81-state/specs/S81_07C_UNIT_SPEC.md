# S81-07c CLAUDE-ROLE-FIX: unit spec (orchestrator-written, S94, 2026-11-12 19:40; SAFE unit: LC-1 / LC-8, the orchestrator's own spec review)

- Unit: S81-07c CLAUDE-ROLE-FIX. Part V = the verdict winner contract; part T = the image_tier3 request shape.
- Flag: NONE (unflagged by design: no live model reads either request today: every `ENABLE_ANTHROPIC_*` is unset on web and the OpenAI key is rejected; the measured state must equal the shipping state, and the harness measures code defaults).
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-s81-s07c` (detached at the base, node_modules junction made by the orchestrator). Branch at GREEN: `feature/s81-07c-role-fix`.
- Base: origin/main `c6ebbd2ed593081cb6241915c36ae29af4c29bca` (PR #402 S81-07 merged). Re-anchor to any moved main the orchestrator passes.
- Evidence: run 1 report and raw records `C:/Users/SynAckITPC/MYEZ-meas/s81-07-run1/` (REPORT.md, text/results.json, text/spend.jsonl, moderation/spend.jsonl; synthetic inputs only, no credential inside); the orchestrator's reading `S94_FIRST_REPORT.md` (copy in the scratchpad notes); the relay's `S81_07_NOGO_ANALYSIS_2026-11-12.md` (copy in the scratchpad notes).
- The owner's words for this work (2026-11-12 about 18:45, verbatim): "we want the issues fixed so the roles are are GO in result". The relay's rule: NO bar is relaxed; the evaluation is never weakened; a fix is a production change measured by the unchanged harness.
- Personal data: none; synthetic values only. Measurement location: `<scratch>/s07c/` (agents: `<scratch>/s07c/<round>/`).

## 0. WHAT

Run 1 of S81-07 (2026-11-12 17:51-18:24, code at 1c3fc375 = c6ebbd2e) gave VERDICT NO-GO on one bar (A6 winner mismatch 22 / 120 = 0.1833 against 0.10) and TEXT NO-GO on one bar (`p95_s.image_tier3` 2.609 s against 2.5). This unit removes both causes in PRODUCTION code; run 2 (a new folder, the TEXT stage) then measures the merged code with the unchanged harness, gold and bars.

- V (verdict): the verdict prompt carries the deterministic result only as text ("Score winner: <name> (narrow lead)") plus one soft sentence; the model re-decides `winner_index` and follows the star rating when the price behind the scorer's value lead is hidden. FIX: the deterministic winner index is GIVEN to the model in one fixed block and the model only explains it.
- T (image_tier3): the closed `json_schema` output format on the image_tier3 site costs a first-use grammar compile and a steady per-call overhead (run 1: r00 schema calls 3.187 / 2.297 s with normal no-schema neighbours; p50 about +0.25 to +0.35 s on every schema site). FIX: image_tier3 moves from R-S06-1 option (a) to option (b): no output format, the JSON-only line, the Claude-branch fence strip, exactly the path of the eleven prose-JSON sites. The site's parser already enforces the contract.

## 1. BASE STATE (measured at c6ebbd2e; re-measure every line before relying on it)

| what | where |
|---|---|
| `generate_comparison(product1, product2, region, concern="value", user_preferences=None, scores_summary=None, category="other", demographics_profile=None, comparison_quality="normal", output_lang=None)` | `app/services/extraction_service.py:2552-2563` |
| the scores block (`## Scoring Context` + `## Verdict Requirements` 1-4 + "Your verdict MUST be consistent..." + the cross-tier sentence), appended to `system_msg` only `if scores_summary:` | `extraction_service.py:2601-2615` |
| then, in order: preferences OR cohort block, the independent-winner block (flag), the Arabic directive (flag) | `extraction_service.py:2617-2634` |
| `_WEIRD_VERDICT_INSTRUCTION` ("Do NOT force a winner_declaration") and `_WEAK_VERDICT_INSTRUCTION`, inside `build_verdict_prompt` | `extraction_service.py:2143-2175, :2247` |
| non-streaming caller: `scoring_result` in scope, `generate_comparison(..., scores_summary=scores_summary, category=category_used, ...)` | `app/services/structured_comparison_service.py:4700-4707` |
| streaming caller: the same, `_verdict_coro = generate_comparison(...)` | `structured_comparison_service.py:5561-5568` |
| the URL-mode caller: `generate_comparison(products[0], products[1], region, category=category_used)` (no scores) | `app/services/url_extraction_service.py:1467` |
| the guard: `_scoring_winner = (scoring_result or {}).get("winner_index")`; on a disagreement the index is forced and the prose replaced | `app/services/response_builder.py:248-352` (`:294` the read) |
| the scores text: `Score winner: <display name> (clear lead / narrow lead)` from `scoring_result.get("winner_index", 0)` | `app/services/scoring_service.py:3017-3095` |
| `IMAGE_TIER3_SCHEMA` (closed: `image_url` string-or-null) | `app/services/llm_router.py:103-108` |
| `SITES["image_tier3"] = SiteSpec("text", 256, IMAGE_TIER3_SCHEMA, True)`; the comment at `:208-210` names image_tier3 among the closed-schema sites | `llm_router.py:208-221` |
| `to_claude_request`: JSON-only line when `expects_json and schema is None`; `output_config = {"effort": "low"}` plus the format when a schema exists | `llm_router.py:719-755` |
| `_normalise`: the fence strip only at a no-format JSON site | `llm_router.py:1035-1052` |
| `_schema_failure` (finish length or JSON parse failure) and the one-per-compare escalation in `route` | `llm_router.py:1082-1130` |
| Tier 3: the prompt, `route("image_tier3", ...)`, its own fence strip, `json.loads`, `_is_valid_image_url`, every failure returns None | `app/services/image_service.py:136-217` |
| harness A1 verdict builder (synthetic summary "72/100; 75/100") | `scripts/meas_claude_gate.py:1691` |
| harness A6 builder: `generate_comparison(c["product_a"], c["product_b"], "bahrain", None, None, c["scores_summary"], "fragrances")` per case and repeat | `scripts/meas_claude_gate.py:1781-1791` |
| harness A1 metrics: `has_schema` read from `SITES[site].output_schema` at report time | `scripts/meas_claude_gate.py:1364-1392` |
| gold: `tests/fixtures/s81_s07/verdict_gold.json` (60 cases; `gold_winner_index` = the production scorer's `winner_index`, `_gen_fixtures.py:136-165`) | fixture |

## 2. CONTRACT

V1. `generate_comparison` gains ONE new parameter, LAST, with a default: `score_winner_index: Optional[int] = None`. Every existing positional and keyword call keeps working.

V2. A value is VALID iff `type(score_winner_index) is int and score_winner_index in (0, 1)` (bool, float, str, None, -1, 2 are invalid). VALID and `scores_summary` truthy: `system_msg` gains the FIXED-WINNER block, placed IMMEDIATELY after the existing scores block (after the cross-tier sentence) and BEFORE the preferences / cohort block. Anything else: `system_msg` is byte-identical to the base for the same other arguments; no exception, no log line.

V3. The block, exact bytes (module constant `_FIXED_WINNER_BLOCK`, formatted with `label = index + 1`, `index = index`; pure ASCII; LF):

```
\n## Fixed Winner\nThe deterministic scoring above picked PRODUCT {label} as the winner. Set "winner_index" to {index}. Do not re-decide the winner from ratings, review counts, prices or any other field, and never present the other product as the winner. Name what the other product does better in key_tradeoff.\n
```

The block names no product (an int and a position label only: no new user-influenced text enters the system message). PRODUCT 1 / PRODUCT 2 are the labels the user message already uses. It does not touch `winner_declaration` or `winner_reason` wording rules (compatible with the weird and weak clauses, the independent-winner block and the Arabic directive).

V4. Both production callers in `structured_comparison_service.py` pass `score_winner_index=scoring_result.get("winner_index")`: the exact value `reconcile_winner_prose` enforces (no default 0: an absent index invents no winner). The URL-mode caller is unchanged.

V5. Harness request parity (`scripts/meas_claude_gate.py`), and nothing else in the harness: the A6 builder passes `score_winner_index=c["gold_winner_index"]` (the production scorer's index, the value production passes); the A1 verdict builder passes `score_winner_index=1` with a comment (the higher of its two synthetic scores, 75 > 72). UNCHANGED: `A6_SENTENCE`, the gold fixture bytes, the 60 cases x reps, the A6 scoring (`_metrics` A6 arm), `evaluate_role`, every bar, the A1 round order, every other builder.

T1. `SITES["image_tier3"] = SiteSpec("text", 256, None, True)`: option (b). `to_claude_request("image_tier3", ...)` then carries NO `output_config["format"]`, `output_config == {"effort": "low"}`, `thinking == {"type": "disabled"}`, `max_tokens == 256`, and a system text equal to `JSON_ONLY_INSTRUCTION` (the Tier-3 call sends no system message of its own). `_normalise` strips a fence at this site.

T2. `IMAGE_TIER3_SCHEMA` is DELETED (dead after T1). The `:208-210` comment is rewritten: vision_v1 / vision_v2 / disambiguate carry closed schemas; image_tier3 takes (b) since S81-07c (the measured schema cost). The `:101-102` heading comment stays true.

T3. `app/services/image_service.py` is NOT edited (its parser already strips a fence, parses, validates the URL, returns None on any failure).

T4. A JSON failure at image_tier3 can now consume the compare's one escalation (`_schema_failure` -> Sonnet) inside the 5.0 s image leg: a STATED LIMIT (section 9), no code.

## 3. CHANGE LIST (opens with byte copies of every file below into the round's notes folder; closes with "No other file")

1. `app/services/extraction_service.py`: `_FIXED_WINNER_BLOCK`; the new parameter; the block appended inside the `if scores_summary:` arm after the existing f-string, guarded by V2; one docstring sentence.
2. `app/services/structured_comparison_service.py`: one keyword at each of the two `generate_comparison` calls.
3. `app/services/llm_router.py`: the `image_tier3` SiteSpec, the deleted constant, the comment.
4. `scripts/meas_claude_gate.py`: the two builder keywords (V5).
5. The NEW frozen RED file `tests/test_s81_s07c_role_fix.py`.
6. The E-row files the RED round measures (section 4.1).
7. `CLAUDE.md`: the S81-07c block after the S81-07 block (what changed, no flag, no knob, the run-2 precondition, the stated limits), plus the in-place rewrite of any row that names image_tier3's schema (the GREEN round measures).

No other file.

## 4. EXISTING PINS

4.1 Deliberate changes (E-rows; the RED round measures the full list at base by grep for `IMAGE_TIER3_SCHEMA`, `"image_tier3"`, `generate_comparison`, `score_winner`, the A6 / A1 builders and the SITES tables, and runs each candidate):
- E1 `tests/test_s81_s06_anthropic_router.py` R02c (`:753-759`): image_tier3 is no longer the closed schema; R02c pins vision_v2 / vision_v1 / disambiguate and image_tier3 = None.
- E2 `tests/test_s81_s06_anthropic_router.py:671`: the exported-name list drops `IMAGE_TIER3_SCHEMA`.
- E3 `tests/test_s81_s06_anthropic_router.py:1540-1559` and `:525` / `:602`: the per-site request rows: image_tier3 now has no format and gets the JSON-only line.
- E4.. any harness-test row in `tests/test_s81_s07_meas_harness.py` that pins the A6 / A1 verdict capture without the index, or SITES-derived schema counts (the synthetic `schema_n` rows at `:2525` / `:2548` are measured: if they derive has_schema from SITES they move to a no-schema site or to disambiguate).
- Any other red the RED round finds at a prototype of the change list (named, with the reason).

4.2 Stay green (no E-row allowed): the verdict prompt digests and fences (`tests/test_prompt_truth.py`, `tests/test_prompt_fence.py`, `tests/fixtures/w4_11_prompt_render_digests.json` through `tests/w4_11_prompt_digest_recorder.py`: they call `generate_comparison` without the new keyword, so their bytes are unchanged; `image_tier3_user` / `image_tier3_kwargs` are the OpenAI-shaped user message and kwargs, unchanged); `tests/test_model_config_enforced.py:154`; `tests/test_s81_s22b_self_critique_retire.py:79`; the reconcile and response-builder suites; every S81-07 row that is not an E-row.

## 5. RED TESTS (`tests/test_s81_s07c_role_fix.py`; RED rows fail at base on an AssertionError ONLY: read new symbols with getattr / inspect.signature and assert; PIN rows green at base)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| V01 | signature | `score_winner_index` is the LAST parameter of `generate_comparison`, default None | RED | V1 |
| V02 | block bytes, index 0 and 1 | the captured system message (offline: the route seam replaced by a recorder that raises after capture, the harness `_capture` pattern) contains `_FIXED_WINNER_BLOCK` formatted for (1, 0) / (2, 1) exactly once; the module constant equals the V3 bytes | RED | V2, V3 |
| V03 | identity outside the block | removing the block from the index-0 system message gives EXACTLY the system message of the same call without the keyword (with and without `user_preferences`, with the weird and the weak quality) | RED | V2 |
| V04 | placement | the block starts right after the cross-tier sentence of the scores block and before the preferences block | RED | V2 |
| V05 | invalid values | None, True, False, 2, -1, "0", 0.0 -> system byte-identical to the no-keyword call, no exception | PIN where it can run at base, else RED by signature | V2 |
| V06 | no scores | `scores_summary` None and "" with index 0 -> byte-identical to the no-keyword call | as V05 | V2 |
| V07 | the Claude request | `llm_router.to_claude_request("verdict", <the captured kwargs>)["system"]` contains the block (the router keeps it) | RED | V2 |
| V08 | callers | AST of `structured_comparison_service.py`: exactly two `generate_comparison(...)` calls, each with keyword `score_winner_index` whose value is the AST of `scoring_result.get("winner_index")` (no default argument) | RED | V4 |
| V09 | URL caller | AST of `url_extraction_service.py`: its `generate_comparison` call has no `score_winner_index` | PIN | V4 |
| V10 | harness A6 parity | offline (no key, the S81-07 tests' plan helpers, a socket guard): for EVERY gold case and repeat the A6 request's `system` contains the block for that case's `gold_winner_index`; the A1 verdict request contains the block for index 1 | RED | V5 |
| V11 | evaluation unchanged | sha256 of `verdict_gold.json`, `A6_SENTENCE`, the TEXT and VERDICT bar dicts and the A6 scoring on a synthetic record set equal their base values (literals recorded at base) | PIN | V5 |
| T01 | site | `SITES["image_tier3"]`: output_schema None, expects_json True, role "text", claude_max_tokens 256 | RED | T1 |
| T02 | request | `to_claude_request("image_tier3", <the kwargs extract_image_via_gpt builds>)`: no format, `output_config == {"effort": "low"}`, thinking disabled, max_tokens 256, system == `JSON_ONLY_INSTRUCTION` | RED | T1 |
| T03 | constant gone | `getattr(llm_router, "IMAGE_TIER3_SCHEMA", None) is None` | RED | T2 |
| T04 | fence and parse (Claude branch, mocked client, every ANTHROPIC flag set only through monkeypatch) | a fenced `{"image_url": "<synthetic https .jpg>"}` -> that URL; `{"image_url": null}` -> None; prose -> None; an extra key -> the URL | RED where the base path differs, else PIN | T1, T3 |
| T05 | harness counts | with the new SITES, A1 metrics count image_tier3 under json_n / json_valid with schema_n 0; disambiguate keeps schema_n | RED | T1 |
| T06 | other schema sites unchanged | disambiguate, vision_v1, vision_v2, moderation schemas byte-equal to base literals | PIN | T2 |

## 6. MUTATION TABLE (each KILLED by an assertion; equivalents reported for a ruling)

M01 the block never appended (V02); M02 label = index (V02); M03 bool accepted (V05); M04 block before the scores block (V04); M05 block after the preferences block (V04); M06 block emitted with an empty summary (V06); M07 one caller omits the keyword (V08); M08 one caller passes `.get("winner_index", 0)` (V08); M09 the A6 builder passes 0 for every case (V10); M10 the A1 builder omits the keyword (V10); M11 the block text drifts by one word (V02); M12 image_tier3 keeps a schema (T01 / T02); M13 image_tier3 expects_json False (T01 / T02); M14 max_tokens 120 (T01); M15 the constant kept (T03); M16 the harness gold read changed (V11).

## 7. GATES (cheapest first)

ruff `E9,F63,F7,F82` and py_compile on every touched python file; the RED file; each E-row file alone; the comm set by the union rule at base and HEAD (branch-only-new EMPTY; the stored base records at 445f8de3 / c6ebbd2e are reused per file where valid, LC-6); the fourteen client fences by path through the junction; an OFFLINE dry run of the harness text stage under a process-wide socket guard with the credential variable unset: the plan's call count and per-stage worst case printed, 0 sockets, 0 credential reads, empty stderr.

## 8. CLAUDE.md block and owner steps

The S81-07c block after the S81-07 block: V and T in two sentences each; no flag, no knob; "run 2 of S81-07 (a NEW output folder, the TEXT stage) on the merged code is the precondition of the ENABLE_ANTHROPIC_TEXT and ENABLE_ANTHROPIC_VERDICT flips; MODERATION stands from run 1 (code untouched)". Owner steps: none (the relay's ops session runs run 2 with the owner's key file; no agent opens it).

## 9. STATED LIMITS

- L1 A6 checks `winner_index` only: whether the prose leans toward the other product is not measured; `reconcile_winner_prose` still guards an index mismatch.
- L2 With a matching index the FULL Claude verdict shows (reason, tradeoff, value context, best-for, pros and cons); before this unit about one A6 call in five showed the fallback line instead.
- L3 A JSON failure at image_tier3 can consume the compare's one escalation inside the 5.0 s image leg (T4); measured JSON validity of trivial outputs is high; run 2 prints image_tier3's json_valid.
- L4 disambiguate and moderation keep their schemas (the same measured overhead; no bar fails).
- L5 No request sets cache_control (run 1 cache-read share 0.0); a forward unit after the flips.
- L6 The production scorer can rest a value lead on a price the card shows as pending; the block tells the model the winner but the model cannot cite that price (WS-C C1 stays): a forward note.
- L7 The harness A1 verdict summary is synthetic, not production-shaped (pre-existing).

## 10. OUT OF SCOPE

Sonnet routing for the verdict role; the gold or any fixture; any bar or the A6 sentence; the knobs (ANTHROPIC_CLASSIFY_LLM_TIMEOUT, ANTHROPIC_TAIL_RESERVE_SECONDS); caching; the schemas of other sites; `reconcile_winner_prose`; the OpenAI path; the client.

## 11. OPEN QUESTIONS

None blocking. The RED round reports any base fact that contradicts section 1 before writing a row on it.

Not done in this spec: the E-row list beyond E1-E3 (measured by the RED round), the comm-set member list (GREEN), the CLAUDE.md row text (GREEN).
