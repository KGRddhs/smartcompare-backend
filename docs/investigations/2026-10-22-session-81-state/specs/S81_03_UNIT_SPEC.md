# S81-03 UNIT SPEC: LLM-LEDGER-V2 (a provider-neutral LLM cost ledger: one pricing leaf, `metadata.llm`, provider-aware rate sites, admin sums, an off-clock spend table)

- Unit: S81-03 LLM-LEDGER-V2 (PLAN_S81 milestone M1, lane B, build-order slot 4).
- Flag: `ENABLE_LLM_LEDGER_V2` (new name, default OFF, read PER CALL with the house idiom; flag OFF byte-identical and pinned). No knobs, no credential, no new external host.
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-s81-s03`, detached at base `95cf6f864b4e70980ca191daa064c0118e223c13` (origin/main = the PR #365 merge: B1 `ENABLE_RESULT_STATUS_METADATA` + B3 `ENABLE_VISION_IDENTITY_V2`, both dark).
- Branch (to be cut by the orchestrator): `feature/s81-llm-ledger-v2`.
- `git status --short`: EMPTY at 22:10 AST before the first probe and EMPTY after every probe (re-checked 22:38, 22:50, 22:52). The probes ran through `pyt.py` (`-p no:cacheprovider`) or in a DETACHED scratch worktree of 95cf6f86 under the notes folder (created with `git worktree add --detach`, removed with `git worktree remove --force`, `git worktree list` re-checked). The only file this spec writes in the worktree is this one, under the gitignored `.qa-s80/` (`.gitignore:72: .qa-*/`).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-03/` (notes.md, base_ledger.log, base_ident.log, probe.log, probe.json, probe_test_copy.py = the probe file, comm_set.txt and its component lists comm_ref / comm_scan / comm_claudemd / comm_client / comm_mig / comm_helper_importers).
- Evidence pointers: `docs/investigations/2026-10-22-session-81-state/specs/S81_03_BRIEF.md` (the brief, binding); PLAN_S81.md (unit text "S81-03 LLM-LEDGER-V2" under M1; the VERIFY "Provider adapter" correction, Ledger bullet; the standing risk "cost truth diverges unless `_track_gpt_cost` and `search_logs.cost` follow the ledger"; Fable ruling F4 on migration numbers: 045 KB core, 046 feedback, 047 the 012 REVOKE, 048 compare_runs, 049 share_target); PLAN_S80.md section 0 (contract freeze) and rulings R-A1, R-A13, R-A15; RULINGS_R0.md (R0-1 persistence: only text and camera rows persist; R0-8 the Anthropic SDK pin, NOT touched here); `runs/research/A1.json` (the 16 chat sites + 1 moderation call; the hardcoded mini rates at `openai_service.py:569-574, 676-684` and `scs:9606-9610` as cited at the S80 code root, re-measured below at 95cf6f86); `runs/research/R1.json` (the live pricing lines, platform.claude.com, read 2026-10-22); `runs/critic.json` (cost_table, assumptions 1 and 7, the Sonnet cache-read correction to $0.10); session-80 `runs/research/contract_freeze.json` (finding: build 3 reads only `metadata.partial` from `metadata`).
- Sister units and contracts:
  - S81-04 SPEND-BREAKER (`ENABLE_LLM_SPEND_BREAKER`, not built): owns the per-day USD caps and its lanes `live`, `escalation`, `search`, `offclock`; it will price its `admit` upper bound and its `record(actual)` through this unit's `llm_pricing.price_call`. It edits `api_budget_service.py` and `guarded_llm_create`; this unit edits NEITHER (pinned by K1), so S81-04 re-records K1 deliberately.
  - S81-06 ANTHROPIC-ROUTER (lane A, not built): calls `llm_pricing.anthropic_usage_record(...)` and `llm_pricing.record_llm_call(...)` for every Claude call, binds `llm_pricing.start_llm_ledger()` beside each `start_openai_ledger()` (`scs:4146`, `scs:4740`, `image_routes.py:340`; this unit does NOT add those bindings, section 9 L3), passes `provider=` to `ModelRouterService.record_usage`, and widens `tests/test_model_config.py:135` to `claude-*` (then `llm_pricing.py` joins that test's `ALLOWED` set, a data table per ruling X15).
  - S81-16 KB-SEED-BATCH and S81-22 COMPARE-RUNS: the first writers of `public.llm_spend_ledger` (migration 050) through `llm_pricing.spend_ledger_row(...)`; S81-22's `llm_calls` reuse `llm_pricing.LLM_RECORD_KEYS` and `OTEL_GENAI_ATTRIBUTES`.
  - D03 DENY-AND-GUARDS (in flight, `sc-s81-d03`): edits other hunks of `structured_comparison_service.py`, and adds a CLAUDE.md flag row next to the one this unit adds (known rebase: the CLAUDE.md row block only). B4 (`sc-s80-b4`) shares no file with this unit.
- Personal-data rule: the repo is public. No real name, email, phone, Apple id, device id, address or account id in any file, test, fixture or log line; synthetic values only (model ids, token counts, USD figures, `.test` hosts). No secret, key or credential-shaped literal; this unit reads no credential and adds no env name to `tests/_env_safety.CREDENTIALS_UNSET`.

## 0. What the unit does

Under `ENABLE_LLM_LEDGER_V2` (default OFF):

1. Adds `app/services/llm_pricing.py`, a leaf (stdlib + `app.services.openai_pricing`, itself a stdlib leaf) that holds the claude-haiku-5-5 and claude-sonnet-5-5 price rows (input, output, cache read, 5-minute and 1-hour cache writes, the Haiku over-100K tier, the Batch multiplier, $0.01 per server web search), re-exports the OpenAI rows of `openai_pricing` (same objects), and prices ANY provider through one function `price_call`; it normalises every call into one provider-neutral usage record (provider, model, role, input / output / cache read / cache write 5m / cache write 1h tokens, web search requests, normalised prompt and completion tokens, cost, latency, stop reason, batch) with an OpenTelemetry GenAI name map for the keys that have a name; it summarises records into the additive `metadata.llm`; it builds the row shape of the off-clock spend table. `openai_pricing.py` is NOT edited (pinned K2), so `tests/test_cost_meter_s74.py` `EXACT_KEYS` stays green.
2. `build_comparison_response` writes `metadata.llm` beside `metadata.openai` (totals from the same OpenAI summary plus any records a future provider recorded; per-call records from the bound ledger, verified against that summary); the camera route merges its vision call into `metadata.llm` as it does for `metadata.openai`.
3. Makes the hardcoded gpt-4o-mini rate sites provider-aware through the leaf: the two vision cost formulas and the variant-disambiguation cost in `openai_service.py`, and `StructuredComparisonService._track_gpt_cost` (the ONLY `structured_comparison_service.py` hunk), which prices each tracked call from the ledger entry it came from (so `metadata.total_cost` and `search_logs.cost` follow the ledger for every tracked call); `ModelRouterService` stops charging the OpenAI 4o token cap for calls served by another provider.
4. `/api/v1/admin/costs` and `/api/v1/admin/costs/api` add an `llm` block summing `metadata.llm` (a separate paged read; the `openai` block and the `X-Admin-Key` guard untouched); `app/static/admin/costs.html` renders that block when present.
5. Adds migration 050 `public.llm_spend_ledger` (+ rollback): an append-only, service-role-only spend table for batches and crons, inert until S81-16 / S81-22 write to it.

Unflagged (R-A1(c), each proven byte-identical for every flag-OFF request or row): the public share view strips `metadata.llm` exactly where it strips `metadata.openai` (a row can carry `metadata.llm` only if the flag was ON when it was written; stripping it unconditionally keeps a later rollback from exposing it; F3); the static `costs.html` additions render nothing unless the endpoint sends `llm`, which only the flag does (G7, G3); the additive keyword `ModelRouterService.record_usage(..., provider=None)` is passed by no existing caller (E4, E6); the migration 050 files change nothing until the owner applies them and nothing writes the table.

It does NOT touch `guarded_llm_create` (neither of its two `create(**kwargs)` calls, nor anything else in it), makes no Anthropic SDK call and adds no dependency, changes no prompt, no model id, no route parameter or request field, no processor row and no client file.

## 1. Base state (MEASURED at 95cf6f86 in this run)

### 1.1 Every site that computes a USD cost today

| Site | What it is at base |
|---|---|
| `app/services/openai_pricing.py:32` | `PRICE_TABLE_AS_OF = "2026-10-08"`. |
| `openai_pricing.py:34-44` | `_GPT4O_RATES` 2.50 / 1.25 / 10.00, `_GPT4O_MINI_RATES` 0.15 / 0.075 / 0.60; `PRICE_USD_PER_1M` = five EXACT keys (gpt-4o, gpt-4o-2024-08-06, gpt-4o-2024-11-20, gpt-4o-mini, gpt-4o-mini-2024-07-18). |
| `openai_pricing.py:46-51` | `BASIS = "list_price"`; `_LEDGER` = `ContextVar("openai_usage_ledger", default=None)`. |
| `openai_pricing.py:53-78` | `price_row` (exact key or None); `list_price_usd(model, prompt, completion, cached=0)` = `(uncached*input + cached*cached_input + completion*output) / 1e6`, None for an unpriced model or a None count. |
| `openai_pricing.py:81-86` | `start_openai_ledger()` binds a fresh list to the ContextVar and returns it. |
| `openai_pricing.py:121-154` | `record_openai_response(model, response)`: appends `{model, prompt_tokens, completion_tokens, cached_tokens, cost_usd}`; never raises; unreadable usage = an unpriced entry. |
| `openai_pricing.py:164-202` | `summarize_openai_ledger` -> `{calls, priced_calls, unpriced_calls, prompt_tokens, cached_tokens, completion_tokens, cost_usd, cost_complete, by_model, basis, price_table_as_of}`; zero calls = 0.0, all unpriced = None. |
| `openai_pricing.py:209-237` | `merge_openai_summaries(a, b)`, None-aware (the camera route). |
| `app/services/api_budget_service.py:934-952` | The census comment ("WIRED (14 dispatches ...)"; A1 measured 16 chat sites + 1 moderation call; stale, NOT edited here). |
| `api_budget_service.py:954-1035` (AST-measured span) | `guarded_llm_create`: `kwargs["store"] = False` first; flag-OFF branch `create(**kwargs)` + `record_openai_response` at `:986`; flag-ON branch `create(**kwargs)` at the breaker path + `record_openai_response` at `:1032`. NOT edited (the U3c pins `tests/test_u3c_store_false_pin.py:231-310` hold it at exactly two `create(**kwargs)` dispatches; K1 pins its AST). |
| `app/services/openai_service.py:550-556` | `_identify_products_v2` cost: `usage is None` -> 0.0, else `round((prompt*0.15)/1e6 + (completion*0.60)/1e6, 6)` via `_vision_usage_int` (`:431-435`); model `_vision_model = vision_model()` (`:470`, the V2 dispatch right below it). Pinned by `tests/test_s80_b3_vision_identity_v2.py:634, :704` (cost 2.4e-05). |
| `openai_service.py:676-685` | `identify_products` V1 cost: `usage = response.usage`; `(usage.prompt_tokens*0.15)/1e6 + (usage.completion_tokens*0.60)/1e6`, returned `round(total, 6)`; model `_vision_model` (`:637`). Pinned by `tests/test_cost_meter_s74.py:1180, :1230` (vision_cost 0.000135 for 500/100 on gpt-4o-mini). |
| `openai_service.py:920-925` | `disambiguate_variant_line` cost (same mini formula, `getattr(usage, ..., 0)`, rounded 6), model `_model = standard_model()` (`:885`). The value is returned and dropped by its only caller (`price_service.py:9120-9136`). |
| `app/services/structured_comparison_service.py:9606-9613` | `_track_gpt_cost(usage)`: `prompt_tokens = usage.get("prompt_tokens", 0) or 0`; same for completion; `cost = (p * 0.15 / 1_000_000) + (c * 0.60 / 1_000_000)`; `self.total_cost += cost`; `api_calls += 1`; `gpt_calls += 1`. Every model (gpt-4o verdict included) priced at mini rates. |
| `scs:4277, 4484, 4916, 5296, 6527, 8545, 8730, 9543, 9578` + `review_service.py:710-711` (via `track_gpt_cost_fn`, `scs:8836`) | The callers of `_track_gpt_cost`; each passes ONE call's `{prompt_tokens, completion_tokens}` built from `response.usage` (`extraction_service.py:1543-1547, 1706-1710, 1758-1762, 1806-1810, 1864-1868, 2754-2758`; `verdict_critique_service.py:217-218`). No caller sums two calls (read at each site). |
| `scs:9615-9623` | `_track_serper_cost` (+0.001) and `_track_cost_amount` (Tier 1.5); untouched. |
| `app/services/response_builder.py:2077` | `metadata.total_cost = round(total_cost, 6)` (the scs `self.total_cost`). |
| `app/api/text_routes.py:446-456, :496-499, :713, :917, :1257` | `search_logs.cost`: success rows read `metadata.total_cost`; failure rows read the top-level `total_cost`, else `metadata.total_cost` (`_failure_log_cost`). Untouched; they follow `self.total_cost`. |
| `app/api/image_routes.py:82-95, :435, :537-541, :572, :607` | Camera: `vision_cost = vision_result.get("cost", 0)`; `metadata.total_cost += vision_cost`; the camera `search_logs` cost. |
| `app/services/model_router_service.py:39, :48-68, :70-100, :102-112` | `DAILY_4O_CAP = 1_000_000`; `daily_4o_cap()` per call; `get_model("high")` reads the Redis counter and routes to `standard_model()` at >= 80 %; `record_usage(model, tokens)` increments only when `model == verdict_model()`. Callers: `extraction_service.py:2528-2529` (get_model) and `:2702-2704` (record_usage with the REQUESTED id), `scs:891` (get_model for the Tier-3 synthesis). |

### 1.2 The ledger and `metadata.openai`

- Bound at `scs:4146` (`_compare_from_text_impl`, REST) and `scs:4740` (`compare_from_text_streaming`); `self._openai_ledger = None` at `scs:3278`; the import `scs:78`.
- Summarised into the builder at `scs:3846` (`_build_partial_response`, the hard-cap partial), `scs:4627` (REST success), `scs:5471` (stream complete): `openai_usage=summarize_openai_ledger(self._openai_ledger)`.
- `response_builder.py:1477` (`openai_usage` parameter), `:2129-2135`: `if openai_usage is not None: result["metadata"]["openai"] = openai_usage`, BEFORE the caller `metadata` override merge.
- The client: build 3 reads only `metadata.partial` from `metadata` (session-80 contract_freeze finding 1); `metadata` is optional. A new `metadata.llm` key is additive and unread by every shipped client.

### 1.3 Share, owner views, admin, the dashboard

- `app/api/share_routes.py:64-76`: the PUBLIC view copies `full_response` without `metadata.openai` when that key is present; the stored dict is never mutated (cm16, `tests/test_cost_meter_s74.py:1289-1328`). The owner history view keeps `metadata.openai` (cm18).
- `app/api/admin_routes.py:123-145` (the comment `:123`, `OPENAI_COST_NOTE` `:133`, `OPENAI_COST_SOURCE`, page 1000 x 10, the select strings `id,created_at,full_response->metadata->openai` and `id,created_at,full_response`), `:147` `_openai_of_row`, `:156-211` `_openai_rows` (paged, `run_db`, blob fallback logged by type), `:214` `_recorded_cost`, `_int_field`, `:231-300` `_aggregate_openai`, `:303-420` `GET /costs` (`summary["openai"]`, comparison count, `avg_cost_per_comparison`, `estimated_monthly_total`), `:944-1000` `GET /costs/api` (`openai_list_usd`, `daily_burn`, ...), `:1064-1104` `GET /costs/gauges` (`openai_4o_today` from the router counter). Every route `Depends(verify_admin_key)`, 30/minute.
- `app/static/admin/costs.html` (266 lines, CRLF, 24 bytes > 127 at base, all in pre-existing text): `fmtUsd` `:160-162` (null -> "n/a"), `renderApiKpis` `:164-184` into `<div class="grid" id="apiKpis">` `:70`, `load()` `:242-260`. Pinned by cm12 (`tests/test_cost_meter_s74.py:1043-1100`: fmtUsd null branch, `${api.note || ""}`, forbidden labels).

### 1.4 The camera merge

`image_routes.py:337-340`: the route binds its OWN ledger (`vision_ledger = start_openai_ledger()`) before `identify_products`; `compare_from_text` then binds the compare's own at `scs:4146`; `:530-550`: `merge_openai_summaries(vision, compare)` written to `metadata.openai` only when the compare carried a summary or the vision ledger recorded a call.

### 1.5 Migrations

- Files at base: `migrations/001..044` (no 039, reserved for M13-29) plus `add_share_token.sql`; rollbacks under `migrations/rollback/`. PLAN_S81 ruling F4 reserves 045-049; the next free number for this unit is 050.
- The pattern to follow: `migrations/044_apple_siwa_tokens.sql` (one transaction; `CREATE TABLE IF NOT EXISTS`; `ENABLE ROW LEVEL SECURITY`; no policy; `REVOKE ALL ... FROM PUBLIC, anon, authenticated`; one explicit `GRANT ... TO service_role`; COMMENTs; a header with apply order, owner postcheck and the rollback path) and `migrations/rollback/044_apple_siwa_tokens.sql`.
- Readers that a new migration must satisfy: `tests/test_migration_index_predicate_immutability.py` (no `now()` / `CURRENT_*` in an index predicate; SECURITY DEFINER guard rule), `tests/test_sqlfluff_config.py::test_sqlfluff_lints_the_migration_corpus_clean` (sqlfluff 4.3.0 on the pinned venv over `migrations/` must stay clean), the 043 deletion fence `tests/test_migration_043_delete_user_cascade.py` (`fence_user_tables`: a column matching `USER_REF_ID_RX` / `PERSONAL_RX` at `:360-369` or an FK to users needs a cascade or a KEEP entry), plus the numbering pins of 042/043/044 (039 stays reserved). `gen_random_uuid()` has precedent in migrations 002, 011, 012, 014, 028-031.

### 1.6 Flag-reader idiom and libraries

House idiom (`openai_service.py:256-263` `vision_identity_v2_enabled`): `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call. Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe` = CPython 3.12.9 (`asyncio.wait_for` with a positive timeout awaits the coroutine IN THE SAME TASK, so a ContextVar bound inside `_compare_from_text_impl` is visible to the outer hard-cap handler; measured by probe P1 below). The leaf needs only the stdlib (`os`, `math`, `contextvars`, `typing`, `datetime`) and `app.services.openai_pricing`. No dependency is added; `requirements*.in/txt` untouched. sqlfluff 4.3.0 is on the venv.

### 1.7 Guards the new code must not trip

- `tests/test_model_config.py:121-151` (stray model literal scan over `app/services/*.py`, regex `["'](gpt-[0-9a-zA-Z.\-]+|omni-moderation-[a-z]+)["']`, `ALLOWED = {"model_config.py", "openai_pricing.py"}`): `llm_pricing.py` must hold NO quoted `gpt-*` literal (the OpenAI rows are imported, never re-typed; the legacy track rates are bare floats). `claude-*` literals are invisible to this regex today (S81-06 widens it and adds `llm_pricing.py` to `ALLOWED`). This is the COST-METER CI-red class (CLAUDE.md:932).
- `tests/test_legal_docs_u8.py` T7b (`CLIENT_CONSTRUCTORS` `:763`, the scanner `:837`, the node `test_t7b_external_hosts_and_clients_map_to_manifest` `:1039`): no non-docstring string literal under `app/services` may hold an `http(s)://` external host; the pricing-page URL lives only in a `#` comment or the module docstring.
- `tests/test_u3c_store_false_pin.py`: `guarded_llm_create` untouched (K1); no OpenAI SDK surface outside it (the leaf calls no SDK).
- `tests/test_model_config_enforced.py`, `test_prompt_fence.py`, `tests/w4_11_prompt_digest_recorder.py`: no prompt, kwargs or dispatch changes, so the flag needs NO clear-list entry. The T23 OpenAPI fixture (`tests/test_s71_u13_compare_auth_required.py`): no route parameter or body field; the admin routes return plain dicts (no response model), so the schema is unchanged.
- The 043 fence (section 1.5): the 050 table carries no user, device, session or address column.
- Pre-commit hook + secret scanner: no credential-shaped literal; the hook runs sqlfluff on staged migrations.

### 1.8 Line endings

Backend files are CRLF in the working copy and LF in the index (`core.autocrlf=true`, `cat -A` shows `^M$` on `openai_pricing.py`); `costs.html` is CRLF. Edit with the Edit tool only; a whole-file diff in `git diff --stat` is a defect. New files (`llm_pricing.py`, the RED file, both 050 SQL files) are written LF, pure ASCII (bytes > 127 = 0). `openai_pricing.py` sha256: working copy `349fcbdf0a39da7d55f420c9240264a31b046bca5d02de68737ca1c02b1ff6b7`, blob / LF-normalised text `0406b617bd91b2a1ea5a5bacd37fd48e28e106ed99991bfec9087d144ec14094` (K2 pins the LF-normalised text, so the pin holds on CI's LF checkout). `guarded_llm_create` `ast.dump(node, include_attributes=False)` sha256 on 3.12.9: `8fa87b61645971d65a41d38cf70938f38d441d0b0a0d91a055b16d74b1b3a63d` (K1).

### 1.9 The pricing inputs (cited, not fetched by this run)

- Anthropic, from `runs/research/R1.json` (the live page platform.claude.com/docs/en/about-claude/pricing.md, "model table rows Haiku 5.5 and long-context section", read 2026-10-22) and the brief: claude-haiku-5-5 $0.10 input / $0.50 output per MTok for prompts up to 100K tokens; cache write 5 min $0.125, 1 h $0.20, cache read $0.01; "$0.50 / $2.50 above 100K. The higher tier applies to the whole request, cache reads included." claude-sonnet-5-5 $2 / $10, cache writes $2.50 / $4, cache read $0.10 (the bundled skill's $0.20 is wrong, critic contradiction 2). Batch: "50% off input and output ... stacks with cache multipliers. Web search inside a batch is charged the same $10 per 1,000 searches." web_search $10 per 1,000 ($0.01 each, `server_tool_use.web_search_requests`); "a search that errors is not billed".
- NOT cited anywhere: the cache-token rates INSIDE the Haiku over-100K tier, Sonnet 5.5 long-context pricing, Opus 5.5 rows (out of the brief's scope), OpenAI Batch rates. Each stays unpriced (None) here (section 2.3).

### 1.10 Base pass state of the files the unit touches (bounded runner)

```
s03-base-ledger: tests/test_cost_meter_s74.py tests/test_cost_dashboard.py tests/test_model_router.py tests/test_s70_model_router_downgrade.py tests/test_share_routes.py tests/test_w4_13_flag_off_ledger.py tests/test_u3c_store_false_pin.py tests/test_model_config.py
====================== 190 passed, 13 warnings in 54.90s ======================
[hermeticity] sentinel checked 190 test(s)
[netguard] blocked 1 attempt(s) from 1 node(s)
[netguard]   tests/test_share_routes.py::test_view_shared_no_auth_needed [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s03-base-ledger start=2026-10-22 22:35:37 end=2026-10-22 22:36:36 elapsed=59s bound=600s status=OK rc=0

s03-base-ident: tests/test_s75_fanout_identity.py tests/test_s80_b3_vision_identity_v2.py tests/test_variant_llm_hint_b3b.py tests/test_camera_vision.py tests/test_paid_route_metering.py tests/test_admin_referral_endpoints.py tests/test_legal_docs_u8.py tests/test_migration_044_apple_siwa_tokens.py tests/test_migration_index_predicate_immutability.py tests/test_sqlfluff_config.py tests/test_migration_043_delete_user_cascade.py
========== 379 passed, 1 deselected, 12 warnings in 70.53s (0:01:10) ==========
[hermeticity] sentinel checked 379 test(s)
[netguard] blocked 2 attempt(s) from 2 node(s)
[netguard]   tests/test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_paid_route_metering.py::test_url_compare_saves_history_with_input_type_url [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=s03-base-ident start=2026-10-22 22:37:05 end=2026-10-22 22:38:24 elapsed=79s bound=600s status=OK rc=0
```

The three netguard nodes are pre-existing baseline nodes (blocked by the sentinel, the test passes). The FY25 nine-digest node `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` and the W4-13 ledger `tests/test_w4_13_flag_off_ledger.py` are green at base. The 3 `test_camera_vision.py::TestIdentifyProductsMocked` nodes are green at base (pruned in B3, R-A14). The full comm set (section 7) is NOT run by this spec; GREEN runs it at base and head.

### 1.11 Satisfiability probe (measured in the scratch worktree)

`tests/test_zz_s03_probe.py` (copy at `notes/probe_test_copy.py`), harness = `tests/test_cost_meter_s74.py` cm13/cm14/cm17 helpers + `tests/test_openai_breaker.py` `_FanOutCounters`, `_run_compare`, `_run_stream`:

```
======================= 5 passed, 10 warnings in 20.64s =======================
[hermeticity] sentinel checked 5 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s03-probe start=2026-10-22 22:44:07 end=2026-10-22 22:44:33 elapsed=26s bound=600s status=OK rc=0
```

- P1 (the ContextVar at build time): at every `build_comparison_response` call on the REST full path, the stream full path and the REST hard-cap partial (cm17 shape), `openai_pricing._LEDGER.get()` is not None and `summarize_openai_ledger(bound) == openai_usage` (REST: 1 build, 11 calls; stream: 1 build, 11 calls; partial: 1 build, 1 call). So the builder can take per-call records from the bound ledger and VERIFY them against the summary it was handed.
- P2 (`_track_gpt_cost` against the ledger, every dispatch carrying a DISTINCT usage `prompt = 1000 + 17n`, `completion = 200 + 3n`): 11 dispatches = 11 ledger entries (8 gpt-4o-mini, 3 gpt-4o); 9 tracked usages; EVERY tracked usage matched a distinct ledger entry with equal (prompt, completion); the 8 mini entries' list price equals the base estimate (to the last digit or 1 ulp); the tracked gpt-4o verdict (1187 / 233) costs 0.0052975 in the ledger against a base estimate of 0.00031785 (16.7x under-count); the 2 UNTRACKED entries are gpt-4o calls (1153 / 227 = 0.0051525 and 1170 / 230 = 0.005225; the Tier-3 synthesis, `tier3_synthesize_non_negotiables` `scs:839-891`, whose usage no caller tracks). `metadata.total_cost` 0.016634 (8 Serper x 0.001 + Tier 1.5 amounts + the 9 mini-rate estimates) against `metadata.openai.cost_usd` 0.017992.

## 2. Contract

Contract freeze (PLAN_S80 section 0, re-read for this section): additive keys only (`metadata.llm`, the admin `llm` blocks); no key removed, renamed or retyped; `metadata.total_cost` stays a float under both flag states (its VALUE follows the ledger under ON for tracked calls); `vision_cost` stays a float; no refusal path, no status code and no envelope changes (this unit refuses nothing; never a bare 503).

### 2.1 Flag and knobs

| Name | Type | Default | Read | Where |
|---|---|---|---|---|
| `ENABLE_LLM_LEDGER_V2` | bool (house idiom) | OFF | per call, first statement of every new branch | `llm_pricing.llm_ledger_v2_enabled()` |

No knob, no credential, no new env name anywhere else. The share strip (section 2.6 S) is unflagged.

### 2.2 `app/services/llm_pricing.py` (new leaf)

Imports: `from __future__ import annotations`, `contextvars`, `math`, `os`, `datetime` (only for isoformat of the row builder), `typing`, and `from app.services import openai_pricing as _openai_pricing`. Nothing else from `app` (pinned A1). The module docstring carries the source line ("platform.claude.com pricing, read 2026-10-22, R1") as prose; no `http(s)://` in any non-docstring string (T7b).

Constants (public names are the contract):

- `FLAG = "ENABLE_LLM_LEDGER_V2"`.
- `ANTHROPIC_PRICE_TABLE_AS_OF = "2026-10-22"`.
- `ANTHROPIC_PRICE_USD_PER_1M: Dict[str, Dict[str, float]]` EXACT keys only:
  - `"claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write_5m": 0.125, "cache_write_1h": 0.20}`
  - `"claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.10, "cache_write_5m": 2.50, "cache_write_1h": 4.00}`
- `HAIKU_LONG_CONTEXT = {"model": "claude-haiku-5-5", "threshold_prompt_tokens": 100000, "input": 0.50, "output": 2.50}`.
- `WEB_SEARCH_USD_PER_REQUEST = 0.01`; `BATCH_TOKEN_MULTIPLIER = 0.5`.
- `OPENAI_PRICE_USD_PER_1M = _openai_pricing.PRICE_USD_PER_1M` (the SAME object); `OPENAI_PRICE_TABLE_AS_OF = _openai_pricing.PRICE_TABLE_AS_OF`.
- `PRICE_TABLE_AS_OF = {"openai": OPENAI_PRICE_TABLE_AS_OF, "anthropic": ANTHROPIC_PRICE_TABLE_AS_OF}`; `BASIS = "list_price"`; `SCHEMA_VERSION = 1`.
- `LEGACY_TRACK_RATES_USD_PER_1M = (0.15, 0.60)` (the base `_track_gpt_cost` / vision literals, kept as bare floats; A4 pins them equal to the gpt-4o-mini input / output rates of `openai_pricing`).
- `LLM_RECORD_KEYS = ("provider", "model", "role", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens", "web_search_requests", "prompt_tokens", "completion_tokens", "cost_usd", "latency_ms", "stop_reason", "batch")`.
- `RECORDS_CAP = 64`.
- `OTEL_GENAI_ATTRIBUTES = {"provider": "gen_ai.provider.name", "model": "gen_ai.request.model", "prompt_tokens": "gen_ai.usage.input_tokens", "completion_tokens": "gen_ai.usage.output_tokens", "stop_reason": "gen_ai.response.finish_reasons"}` (the five keys whose OpenTelemetry GenAI semantic-convention name the spec writer can state; not fetched in this run, OQ-6; the cache and web-search keys have no entry).
- `SPEND_LANES = ("live", "escalation", "search", "offclock")` (the S81-04 lanes); `SPEND_MODES = ("sync", "batch")`; `SPEND_PROVIDERS = ("openai", "anthropic")`.
- `SPEND_LEDGER_COLUMNS = ("job", "lane", "mode", "provider", "model", "role", "provider_batch_id", "request_count", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens", "web_search_requests", "cost_usd", "cost_complete", "basis", "price_table_as_of", "period_start", "period_end")` (migration 050 minus `id`, `created_at`).
- `_LLM_LEDGER: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar("llm_usage_ledger", default=None)`.

Functions (none raises unless stated; every token argument is a non-negative non-bool `int`, anything else makes the price None):

| Function | Contract |
|---|---|
| `llm_ledger_v2_enabled() -> bool` | the house idiom on `FLAG`, per call. |
| `provider_of(model) -> Optional[str]` | `"anthropic"` when `model` is a str starting `claude-`; `"openai"` when it starts `gpt-` or `omni-moderation-`; else None (non-str included). |
| `price_call(provider, model, *, input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_5m_tokens=0, cache_write_1h_tokens=0, web_search_requests=0, batch=False) -> Optional[float]` | Section 2.3. Unrounded USD. |
| `legacy_track_cost_usd(prompt_tokens, completion_tokens)` | EXACTLY the base expression `(prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)` with the operands as given (same operation order, so the float is bit-identical to the base `_track_gpt_cost` for the same inputs). |
| `openai_usage_cost_usd(model, usage) -> float` | `p`, `c` = the int `prompt_tokens` / `completion_tokens` of the usage object (non-int -> 0, the `_vision_usage_int` rule); `cached` = `usage.prompt_tokens_details.cached_tokens`, else `usage.prompt_tokens_cached`, else 0 (the `openai_pricing._cached_tokens` rule, re-implemented, never imported as a private); returns `price_call("openai", model, input_tokens=max(p - cached, 0), cache_read_tokens=min(cached, p), output_tokens=c)` when not None, else `legacy_track_cost_usd(p, c)` (never None: a float for the existing float fields). `usage` None -> 0.0. |
| `tracked_call_cost_usd(usage, claims) -> float` | The `_track_gpt_cost` ON body. `p = usage.get("prompt_tokens", 0) or 0`, `c = usage.get("completion_tokens", 0) or 0` (the base coercion). Candidates = the bound OpenAI ledger entries (key `("openai", i)`) then the bound llm-ledger records (key `("llm", i)`). `claims` is a caller-owned dict: when `claims.get("ledger")` is not the bound OpenAI ledger object, it is reset to `{"ledger": <bound>, "llm": <bound llm list>, "taken": set()}`. The FIRST candidate not in `taken` whose `prompt_tokens == p` and `completion_tokens == c` is claimed; its `cost_usd`, when a finite non-negative float, is returned; a claimed candidate with cost None (unpriced model) returns `legacy_track_cost_usd(p, c)`; no candidate (or no bound ledger, or a non-dict usage) returns `legacy_track_cost_usd(p, c)`. Each candidate is claimed at most once. |
| `openai_entry_record(entry) -> Dict` | An OpenAI ledger entry -> a record with exactly `LLM_RECORD_KEYS`: provider `"openai"`, model `str(entry.model)`, role None, `prompt_tokens` = entry prompt, `completion_tokens` = entry completion, `cache_read_tokens` = entry cached, `input_tokens` = prompt - cached (clamped >= 0; None when prompt is None), `output_tokens` = completion, cache writes 0 (None when prompt is None), web search 0, `cost_usd` = `price_call("openai", ...)` on those tokens (== the entry's own `cost_usd`, pinned A11/A15), latency None, stop reason None, batch False. |
| `anthropic_usage_record(model, usage, *, role=None, latency_ms=None, stop_reason=None, batch=False) -> Dict` | For S81-06. Reads `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_creation.ephemeral_5m_input_tokens`, `cache_creation.ephemeral_1h_input_tokens`, `server_tool_use.web_search_requests` by attribute or key (a missing value = 0). 5m / 1h come from the breakdown when present; otherwise ALL `cache_creation_input_tokens` count as 5-minute writes (the default TTL; stated L7). `prompt_tokens` = input + cache_read + cache_write_5m + cache_write_1h; `completion_tokens` = output; `cost_usd` = `price_call("anthropic", model, ...)`; provider `"anthropic"`. Unreadable usage = every token None and cost None (never raises). |
| `start_llm_ledger() -> List` | Binds a FRESH list to `_LLM_LEDGER` and returns it (S81-06 binds it beside `start_openai_ledger`). |
| `record_llm_call(record) -> None` | Appends a copy of `record` (only `LLM_RECORD_KEYS`) to the bound llm ledger; a no-op when none is bound; never raises. |
| `current_openai_ledger()` / `current_llm_records()` | `_openai_pricing._LEDGER.get()` / `_LLM_LEDGER.get()` (the one sanctioned read of the untouched leaf's ContextVar; pinned A1 so nothing else reads it). |
| `summarize_llm_records(records) -> Dict` | Section 2.5 shape from a record list (records = the list, capped). |
| `llm_summary_from_openai(openai_usage) -> Optional[Dict]` | Section 2.5 shape from a `metadata.openai` summary (totals and `by_model` mapped 1:1; `records` None); None for None. |
| `merge_llm_summaries(a, b) -> Optional[Dict]` | None-aware like `merge_openai_summaries`: counts and token sums add; `cost_usd` = sum of the non-None (None only when both None); `cost_complete` = a AND b; `by_provider` / `by_model` merge per key; `records` = a's then b's when both are lists (capped, `records_truncated` OR-ed / set on cap), else None; `basis`, `price_table_as_of`, `schema_version` from a, else b. |
| `build_llm_metadata(openai_usage) -> Optional[Dict]` | The builder's one call. None when `openai_usage` is None. Else `merge_llm_summaries(<openai part>, <llm part>)` where the OpenAI part is `summarize_llm_records([openai_entry_record(e) for e in bound])` when the bound OpenAI ledger is not None AND `_openai_pricing.summarize_openai_ledger(bound) == openai_usage` (verified), else `llm_summary_from_openai(openai_usage)` (records None); the llm part is `summarize_llm_records(current_llm_records())` when an llm ledger is bound, else None. |
| `spend_ledger_row(*, job, lane, mode, provider, model, records, role=None, provider_batch_id=None, period_start=None, period_end=None) -> Dict` | The migration 050 row (keys exactly `SPEND_LEDGER_COLUMNS`). Raises `ValueError` on: job not a str of 1-64 chars; lane not in `SPEND_LANES`; mode not in `SPEND_MODES`; provider not in `SPEND_PROVIDERS`; model not a str of 1-64 chars; role not None and not a str of 1-32; `provider_batch_id` not None and not a str of 1-128; a record whose provider or model differs; mode `batch` with a record whose `batch` is not True (or `sync` with one that is). Sums each token field (None counts 0); `request_count` = len(records); `cost_usd` = round(sum of priced, 6), None when none priced; `cost_complete` = every record priced (True for zero records with cost 0.0); `basis` `"list_price"`; `price_table_as_of` = `PRICE_TABLE_AS_OF[provider]`; `period_start` / `period_end` = `datetime.isoformat()` or None. The off-clock writer (S81-16 / S81-22) is the only caller. |

### 2.3 Price rules (`price_call`)

- Any token count that is not a non-negative non-bool int, or a `web_search_requests` that is not one -> None.
- provider `"openai"`: a non-zero cache write, a non-zero web search or `batch=True` -> None (no cited OpenAI rate). Else `_openai_pricing.list_price_usd(model, input_tokens + cache_read_tokens, output_tokens, cache_read_tokens)` (DELEGATION: the float is bit-identical to the OpenAI ledger's own cost for the same call, pinned A11). Unknown id -> None.
- provider `"anthropic"`: `row = ANTHROPIC_PRICE_USD_PER_1M.get(model)` (EXACT key; a dated id, `claude-opus-5-5`, `""`, a non-str -> None). `prompt_total = input + cache_read + cache_write_5m + cache_write_1h`.
  - Haiku long context: when `model == HAIKU_LONG_CONTEXT["model"]` and `prompt_total > 100000` (strictly): if any cache token (read or write) is non-zero -> None (the tier's cache rates are not cited, L5); else `tokens = input * 0.50 + output * 2.50`.
  - Otherwise `tokens = input*row.input + output*row.output + cache_read*row.cache_read + cache_write_5m*row.cache_write_5m + cache_write_1h*row.cache_write_1h`.
  - `cost = (tokens / 1e6) * (BATCH_TOKEN_MULTIPLIER if batch else 1.0) + web_search_requests * WEB_SEARCH_USD_PER_REQUEST` (the search fee is never discounted).
- Any other provider -> None. Results are unrounded; summaries round to 6 decimals.

### 2.4 The usage record

Exactly `LLM_RECORD_KEYS`; types: provider str; model str; role str or None; the eight token keys int or None; `web_search_requests` int; `cost_usd` float or None; `latency_ms` int or None; `stop_reason` str or None; `batch` bool. `prompt_tokens` is the normalised total input (OpenAI `prompt_tokens`; Anthropic input + cache_creation + cache_read) so every existing `prompt_tokens` reader keeps its meaning; `input_tokens` is the uncached input billed at the base rate. In this unit OpenAI records carry role / latency / stop reason None (L2).

### 2.5 `metadata.llm` (written only ON)

```
{
  "schema_version": 1,
  "calls": int, "priced_calls": int, "unpriced_calls": int,
  "prompt_tokens": int, "completion_tokens": int,
  "input_tokens": int, "output_tokens": int,
  "cache_read_tokens": int, "cache_write_5m_tokens": int, "cache_write_1h_tokens": int,
  "web_search_requests": int,
  "cost_usd": float | None,          # 0.0 for zero calls, None when no call priced, else round(sum, 6)
  "cost_complete": bool,             # priced_calls == calls
  "by_provider": {"<provider>": {"calls": int, "cost_usd": float | None}},
  "by_model": {"<model>": {"provider": str | None, "calls": int, "prompt_tokens": int,
                           "completion_tokens": int, "cache_read_tokens": int, "cost_usd": float | None}},
  "records": [ <record>, ... ] | None,   # None when the per-call detail could not be verified
  "records_truncated": bool,             # True when more than RECORDS_CAP records existed
  "basis": "list_price",
  "price_table_as_of": {"openai": "2026-10-08", "anthropic": "2026-10-22"}
}
```

Token sums skip None values (the openai summary rule). For OpenAI-only traffic the OpenAI part equals `metadata.openai` field for field: `calls`, `priced_calls`, `unpriced_calls`, `prompt_tokens`, `completion_tokens`, `cache_read_tokens` (= `cached_tokens`), `cost_usd`, `cost_complete`, and `by_model[m].calls / cost_usd` (pinned B1).

### 2.6 Consumer contracts (ON; OFF = base bytes)

- RB `response_builder.build_comparison_response` (after the `metadata.openai` write at `:2134-2135`, before the caller override merge): `if llm_ledger_v2_enabled() and openai_usage is not None: llm = build_llm_metadata(openai_usage); if llm is not None: result["metadata"]["llm"] = llm`. A caller `metadata={"llm": X}` wins (B6). The flag is read only on this line.
- TG `StructuredComparisonService._track_gpt_cost` (`scs:9606-9613`, the only scs hunk; local import inside the method, no module-level import):
  ```
  def _track_gpt_cost(self, usage: dict):
      """Track real GPT cost from token usage."""
      from app.services import llm_pricing as _llm_pricing  # S81-03: the unit's only scs hunk
      if _llm_pricing.llm_ledger_v2_enabled():
          claims = self.__dict__.setdefault("_llm_track_claims", {})
          cost = _llm_pricing.tracked_call_cost_usd(usage, claims)
      else:
          prompt_tokens = usage.get("prompt_tokens", 0) or 0
          completion_tokens = usage.get("completion_tokens", 0) or 0
          cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
      self.total_cost += cost
      self.api_calls += 1
      self.gpt_calls += 1
  ```
  So under ON every tracked call adds its ledger list price (the requested model's row, cached tokens priced) to `self.total_cost`, hence to `metadata.total_cost`, the failure dicts' top-level `total_cost` and `search_logs.cost`; counters unchanged.
- OV1 `openai_service.identify_products` (`:676-685`): ON -> `total_cost = _llm_pricing.openai_usage_cost_usd(_vision_model, response.usage)`, the return shape unchanged (`round(total_cost, 6)`, `tokens_used` as base). A None usage under ON costs 0.0 (base raises AttributeError; stated L9).
- OV2 `openai_service._identify_products_v2` (`:550-556`): ON -> `usage is None` 0.0 as base, else `cost = round(openai_usage_cost_usd(_vision_model, usage), 6)`.
- OD `openai_service.disambiguate_variant_line` (`:920-925`): ON -> `if usage is not None: cost = round(openai_usage_cost_usd(_model, usage), 6)`.
- MR `ModelRouterService` (`model_router_service.py`):
  - `get_model(priority="high")`: ON and `provider_of(verdict_model()) == "anthropic"` -> return `verdict_model()` without reading the counter; every other case as base.
  - `record_usage(self, model, tokens_used, provider=None)` (an additive keyword, default None): ON -> `served = provider if provider is not None else provider_of(model)`; when `served` is not None and not `"openai"`, return without incrementing; else the base body (count only when `model == verdict_model()`). OFF: `provider` is ignored.
- IR camera (`image_routes.py:530-550`): ON -> `vision_llm = summarize_llm_records([openai_entry_record(e) for e in vision_ledger])`; `compare_llm = result["metadata"].get("llm")` (dict metadata only); `merged_llm = merge_llm_summaries(vision_llm, compare_llm)`; written to `result["metadata"]["llm"]` under the SAME condition as `metadata.openai` (`compare_llm is not None or vision_llm["calls"] > 0`), on both metadata branches (`:537-547`). `vision_cost` comes from OV1 / OV2.
- S share (`share_routes.py:64-76`, UNFLAGGED): the stripped key set becomes `("openai", "llm")`; the copy is made when either key is present; the stored dict is never mutated; a row with neither key passes through exactly as at base.
- AD admin (`admin_routes.py`): new constants `LLM_COST_NOTE` (pure ASCII; states list price, persisted comparisons only, every provider, the same exclusions as `OPENAI_COST_NOTE` plus "off-clock batches and crons (llm_spend_ledger)", and "not a bill"), `LLM_COST_SOURCE = "comparisons.full_response.metadata.llm"`, `_LLM_SELECT_JSON_PATH = "id,created_at,full_response->metadata->llm"`, `_LLM_SELECT_BLOB = "id,created_at,full_response"`; new `_llm_rows(client, since_iso)` (the `_openai_rows` paging, ordering, de-dup, `run_db`, blob fallback logged by type; rows `{id, created_at, llm}`) and `_aggregate_llm(rows, truncated)` (the `_aggregate_openai` rules: `cost_usd` None when no row recorded a cost, never 0; `rows_with_cost` / `rows_partial` / `rows_without_cost`; `cost_complete` None / False / True; `today_usd`; `by_day`; plus `calls`, the eight token sums, `web_search_requests`, `by_provider` and `by_model` `{calls, cost_usd}`, `basis`, `price_table_as_of` = `llm_pricing.PRICE_TABLE_AS_OF`, `note`, `source`). `GET /costs`: ON -> `summary["llm"] = _aggregate_llm(...)` (a read failure = the aggregate of None rows: cost None); `GET /costs/api`: ON -> the response gains `"llm": _aggregate_llm(...)`. Both reads happen only ON; `_openai_rows`, `_aggregate_openai`, the select strings, the count query, `OPENAI_COST_NOTE` and every existing response key are untouched; `verify_admin_key` untouched.
- CH `app/static/admin/costs.html`: a new empty container `<div class="grid" id="llmKpis"></div>` after `apiKpis`; a new `renderLlmKpis(api)` called from `load()` after `renderApiKpis(api)`: when `api.llm` is an object, it writes ONE card "ALL-PROVIDER LLM LIST PRICE (${days}D)" with `${fmtUsd(api.llm.cost_usd)}` and `${api.llm.note || ""}`; otherwise it writes "" (the DOM is unchanged when the key is absent). Only ASCII is added; no cm12-forbidden phrase is introduced.

### 2.7 The off-clock spend ledger: migration 050 (decision)

Decision: a NEW table `public.llm_spend_ledger`, migration `050_llm_spend_ledger.sql`, inert until S81-16 / S81-22 write to it. Why it beats the alternatives:
- `search_logs.cost` is a per-COMPARE KPI series: every `analytics_service` reader (daily stats, cost trends, error stats, popular queries, `get_error_stats` exact-text buckets) counts each row as a search; batch and cron rows would move those series (the W4-13 measurement-truth lesson) or need an `is_synthetic`-style exclusion on every reader. Rejected.
- An existing table (`eval_runs` 031, `verdict_critiques` 030): different grain and semantics. Rejected.
- Redis (the S81-04 day counters): enforcement state with TTLs, not a durable audit record. Complementary, not a substitute.
DDL contract (GREEN writes it in the 044 style, keywords upper case, lint clean under `.sqlfluff`):
- `CREATE TABLE IF NOT EXISTS public.llm_spend_ledger (` `id uuid PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at timestamptz NOT NULL DEFAULT now()`, `job text NOT NULL CHECK (char_length(job) BETWEEN 1 AND 64)`, `lane text NOT NULL CHECK (lane IN ('live', 'escalation', 'search', 'offclock'))`, `mode text NOT NULL CHECK (mode IN ('sync', 'batch'))`, `provider text NOT NULL CHECK (provider IN ('openai', 'anthropic'))`, `model text NOT NULL CHECK (char_length(model) BETWEEN 1 AND 64)`, `role text CHECK (role IS NULL OR char_length(role) BETWEEN 1 AND 32)`, `provider_batch_id text CHECK (provider_batch_id IS NULL OR char_length(provider_batch_id) BETWEEN 1 AND 128)`, `request_count integer NOT NULL DEFAULT 0 CHECK (request_count >= 0)`, six token columns `bigint NOT NULL DEFAULT 0 CHECK (<col> >= 0)` (input, output, cache_read, cache_write_5m, cache_write_1h) and `web_search_requests integer NOT NULL DEFAULT 0 CHECK (web_search_requests >= 0)`, `cost_usd numeric(14, 6) CHECK (cost_usd IS NULL OR cost_usd >= 0)` (NULL = unpriced, never 0), `cost_complete boolean NOT NULL`, `basis text NOT NULL DEFAULT 'list_price' CHECK (basis = 'list_price')`, `price_table_as_of text NOT NULL`, `period_start timestamptz`, `period_end timestamptz` `)`.
- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` no policy; `REVOKE ALL ON TABLE public.llm_spend_ledger FROM PUBLIC, anon, authenticated;` `GRANT SELECT, INSERT ON public.llm_spend_ledger TO service_role;` (append-only: no UPDATE / DELETE grant); `COMMENT ON TABLE` (spend of batches and crons, list price, no user data, service role only); no index, no function, no trigger, nothing else touched. One `BEGIN; ... COMMIT;`.
- Header: "MERGING THIS CHANGES NOTHING IN PRODUCTION"; no flag reads or writes the table; apply any time (no ordering against 045-049); owner postcheck: `relrowsecurity = true`; `has_table_privilege('service_role', 'public.llm_spend_ledger', 'INSERT')` and `'SELECT'` true; for `anon` and `authenticated` `SELECT` false; `service_role` `UPDATE` false; rollback path.
- Rollback `migrations/rollback/050_llm_spend_ledger.sql`: `BEGIN; DROP TABLE IF EXISTS public.llm_spend_ledger; COMMIT;` with a header saying it is destructive (the spend history is lost) and that no flag needs flipping first.
- No column matches the 043 fence regexes (no user / owner / account / device / session / address / ip / email column, no FK to users), so no KEEP entry and no cascade change (H3).

### 2.8 Failure table

| Case | Behaviour |
|---|---|
| Flag OFF | Every site runs its base statements; no new read, no new key, no extra query (section 2.9). |
| ON, no ledger bound (a direct service call, a script) | `metadata.llm` absent when `openai_usage` is None; `_track_gpt_cost` adds `legacy_track_cost_usd` (bit-identical to base). |
| ON, bound ledger does not summarise to `openai_usage` | `metadata.llm` from the summary, `records` None. |
| ON, a tracked usage with no matching entry, or a matched entry that is unpriced | the base estimate (a float, never None). |
| ON, an unknown / dated model id | `price_call` None; the record is unpriced; `cost_complete` False; the vision / disambiguation float falls back to the base estimate. |
| ON, Haiku request > 100K prompt tokens with cache tokens | the record is unpriced (None), `cost_complete` False. |
| ON, `record_llm_call` with no llm ledger bound | no-op. |
| ON, an unreadable Anthropic usage | a record with None tokens and cost (unpriced). |
| ON, admin `metadata.llm` read raises | the `llm` block with `cost_usd` None, `rows` 0, `cost_complete` None; logged WARNING with the exception TYPE only; the `openai` block unaffected. |
| ON, a corrupt `metadata.llm` in a stored row (non-dict, NaN, negative, bool cost) | counted `rows_without_cost`; never raises. |
| `spend_ledger_row` invalid input | `ValueError` (off-clock writers only; the live path never calls it). |
| Share view, either flag state | a stored `metadata.llm` never reaches the public response. |

Log lines: none added on the request path; the admin read reuses the existing WARNING shape (`"[ADMIN] llm JSON-path select rejected (%s); falling back to the blob select"`, `"[ADMIN] Failed to fetch LLM costs: %s"` with `type(e).__name__`). No value, URL body or credential is ever logged.

### 2.9 Flag-OFF identity: the main invariant

With `ENABLE_LLM_LEDGER_V2` unset or any falsy value (`""`, `false`, `0`, `off`, `no`, ` FALSE `), measured by PIN rows that run with the ledger BOUND, recorders on every `llm_pricing` entry point (when the module exists) and the unit's state primed (claims dict present, an llm ledger bound):
- every compare body (REST full, stream complete, hard-cap partial, camera) is byte-identical: no `metadata.llm`, `metadata.openai` and `metadata.total_cost` equal to the base recording (B4, B5, C6, I2), the FY25 nine digests and the W4-13 45-scenario ledger unchanged;
- `_track_gpt_cost`, the three openai_service cost sites and both router methods run their base statements (C6, D3, D6b, E4, E6);
- the admin endpoints issue exactly the base queries and return exactly the base keys (G3); `costs.html` renders the same DOM (the new function returns "" without `api.llm`; G7 static pins);
- no `llm_pricing` summarise / build / track / price function is called (the recorders read zero calls).
`openai_pricing.py` (K2) and `guarded_llm_create` (K1) are byte- / AST-identical in both states.

### 2.10 Test seams (production value in brackets)

- `llm_pricing.current_openai_ledger` / `current_llm_records` [the ContextVars], `ANTHROPIC_PRICE_USD_PER_1M` [the two rows], `RECORDS_CAP` [64]; monkeypatch only.
- `os.environ["ENABLE_LLM_LEDGER_V2"]` per test via `monkeypatch.setenv` / `delenv` [unset in production by construction: a new name; Railway not read].
- The model ids per call: `OPENAI_MODEL_VERDICT` / `_STANDARD` / `_VISION` / `_CRITIC` [gpt-4o / gpt-4o-mini x3] (`_pin_default_models`).
- The admin fake: a fake Supabase that answers BOTH JSON paths (`->openai` and `->llm`) by key, records every select string, and can raise on one path only.
- The router: `_get_4o_usage_today` / `_increment_4o_usage` recorders (the test_model_router pattern) [Redis].

## 3. Change list (in the order GREEN applies it)

0. Byte copies of every file the unit edits into the notes folder (Python `shutil.copyfile`), sha256 recorded.
1. `app/services/llm_pricing.py` (new, LF, ASCII): section 2.2 / 2.3 / 2.4 / 2.5.
2. `app/services/response_builder.py`: one import line (`from app.services.llm_pricing import build_llm_metadata, llm_ledger_v2_enabled`) and the RB block after `:2135` (section 2.6 RB).
3. `app/services/structured_comparison_service.py`: the TG hunk inside `_track_gpt_cost` (`:9606-9613`) ONLY.
4. `app/services/openai_service.py`: one import (`from app.services import llm_pricing as _llm_pricing`) and the OV2 (`:550-556`), OV1 (`:676-685`) and OD (`:920-925`) branches; each OFF branch keeps the base lines verbatim.
5. `app/services/model_router_service.py`: one import (`from app.services.llm_pricing import llm_ledger_v2_enabled, provider_of`) and the MR changes (section 2.6 MR).
6. `app/api/image_routes.py`: extend the `openai_pricing` import neighbourhood with `from app.services import llm_pricing as _llm_pricing` and the IR block at `:530-550`.
7. `app/api/share_routes.py`: the S change (unflagged).
8. `app/api/admin_routes.py`: the AD constants, `_llm_rows`, `_aggregate_llm`, the two ON blocks; import `from app.services import llm_pricing as _llm_pricing`.
9. `app/static/admin/costs.html`: the CH container and function (Edit tool, CRLF preserved).
10. `migrations/050_llm_spend_ledger.sql` + `migrations/rollback/050_llm_spend_ledger.sql` (new, LF, ASCII).
11. `.qa-s80/APPLY_050_1_PRECHECK.sql`, `APPLY_050_2_ONE_PASTE.sql`, `APPLY_050_3_POSTCHECK.sql` (gitignored; the orchestrator copies them to the session-81 state folder): PRECHECK = `to_regclass('public.llm_spend_ledger') IS NULL`; ONE_PASTE = the forward file verbatim; POSTCHECK = the section 2.7 grid.
12. `tests/test_s75_fanout_identity.py`: `"ENABLE_LLM_LEDGER_V2"` appended to `UNIT_ENV` (deliberate E1).
13. `CLAUDE.md`: the section 8 row after the last flag row, the SESSION 80 B3 VISION-IDENTITY-V2 paragraph (`CLAUDE.md:476-477`; the B3-B row is `:471-472`, the B1 row `:474-475`), before the blank line `:478` and `## Tests` (`:479`).
14. The RED file `tests/test_s81_s03_llm_ledger_v2.py` stays byte-unchanged (its RED-gate sha).

No other file. In particular NOT: `openai_pricing.py`, `api_budget_service.py`, `extraction_service.py`, `text_routes.py`, `database_service.py`, `processors.json`, any legal text, any requirements file, any client file.

## 4. Existing pins

### 4.1 Pins that change deliberately

| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_s75_fanout_identity.py:60-64` `UNIT_ENV` | `"ENABLE_LLM_LEDGER_V2"` appended (the B1 E1 precedent, `ENABLE_RESULT_STATUS_METADATA`) | a developer shell or `.env` carrying the flag would add `metadata.llm` and move all nine digests; the node itself stays green and its fixture is NOT re-recorded. |

No other existing pin changes. K1 (the `guarded_llm_create` AST hash) is NEW in this unit and is S81-04's deliberate re-record later.

### 4.2 Pins that must stay green and unedited

`tests/test_cost_meter_s74.py` (all of it: EXACT_KEYS cm01, cm02-cm06 recorder, cm07 builder, cm08-cm12 admin and costs.html, cm13 / cm14 / cm17 end to end, cm15 / cm15b / cm15c camera vision_cost 0.000135 and the merge, cm16 share strip, cm18 owner view, cm19); `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (fixture unchanged); `tests/test_w4_13_flag_off_ledger.py` + `tests/test_w4_13_measurement_truth.py`; `tests/test_s80_b3_vision_identity_v2.py:634, :704, :825, :845, :1472` (V2 cost values OFF); `tests/test_variant_llm_hint_b3b.py`; `tests/test_model_router.py`, `tests/test_s70_model_router_downgrade.py`, `tests/test_m18_openai_tpm_sizing.py`; `tests/test_share_routes.py`; `tests/test_cost_dashboard.py`, `tests/test_admin_referral_endpoints.py`, `tests/test_security_regression.py` (admin key and share sections); `tests/test_u3c_store_false_pin.py`; `tests/test_model_config.py` (stray literal scan), `tests/test_model_config_enforced.py`, `tests/test_prompt_fence.py`; `tests/test_legal_docs_u8.py` (T7b); `tests/test_migration_index_predicate_immutability.py`, `tests/test_sqlfluff_config.py`, `tests/test_migration_043_delete_user_cascade.py`, `tests/test_migration_044_apple_siwa_tokens.py`, `tests/test_migration_042_search_logs_is_synthetic.py`; `tests/test_paid_route_metering.py`, `tests/test_retro_w2_1.py`, `tests/test_camera_vision.py`; every file of the section 7 comm set.

## 5. RED tests: `tests/test_s81_s03_llm_ledger_v2.py`

Hash literals that contain an 8-digit run (the K1 hash holds `61645971`) are built by string concatenation in the RED file so the added-line sweep's 8-digit rule cannot misfire. Hermetic: no socket (the `install_network_guard` helper of `tests/_retro_r_mig_sql.py` for the static rows; the conftest netguard everywhere), fake OpenAI clients and fake Supabase, recorders; pure ASCII, LF; no credential-shaped literal (the B3B rule: anything key-shaped is built at run time). Harness imports (read-only): `tests.test_cost_meter_s74` (`_usage`, `_response`, `_usage_client`, `_pin_default_models`, `_no_supabase`, `_no_egress`, `_FakeSupabase`-style fakes are RE-WRITTEN in this file for the two-path read), `tests.test_openai_breaker` (`_FanOutCounters`, `_all`, `_arm_prod_search_config`, `_run_compare`, `_run_stream`), `tests.test_compare_timeout_graceful._fake_product`, `tests._retro_r_mig_sql`, `tests.test_migration_043_delete_user_cascade` (fence helpers). Every RED reads a missing symbol through `importlib.util.find_spec` / `getattr(..., None)` / `inspect.signature` and ASSERTS, so base fails on an AssertionError only. Every PIN row is green at base and runs with the B1-RULE configuration (the flag set to a falsy value, the ledger bound, recorders installed when `llm_pricing` exists, an llm ledger bound and a claims dict primed when the module exists). A distinct-usage fake client (`prompt = 1000 + 17n`, `completion = 200 + 3n`, cached 0) is defined in the file (the probe's `_distinct_client`). Gold-set / eval_regression scenarios do not apply (no compare outcome changes; the cost of a compare is not an eval axis).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| A1 | `test_a1_leaf_exists_and_imports_only_stdlib_and_openai_pricing` | `find_spec("app.services.llm_pricing")` not None; AST of the file: every `import` / `from` is stdlib or `app.services.openai_pricing`; the only `_LEDGER` attribute read in `app/` outside `openai_pricing.py` is in `llm_pricing.current_openai_ledger` | RED (spec None) | 2.2 |
| A2 | `test_a2_flag_reader_idiom_per_call` (param: unset, "", "false", "0", "off", "no", "garbage", " FALSE " -> False; "true", " TRUE ", "1", "yes", "On" -> True; toggled twice in one test) | the reader result | RED | 2.1 |
| A3 | `test_a3_anthropic_rows_exact_keys_rates_and_as_of` | keys == {"claude-haiku-5-5", "claude-sonnet-5-5"}; the ten rates; cache_write_5m == approx 1.25 x input and 1h == approx 2 x input per row; `ANTHROPIC_PRICE_TABLE_AS_OF == "2026-10-22"`; `PRICE_TABLE_AS_OF == {"openai": "2026-10-08", "anthropic": "2026-10-22"}` | RED | 2.2 |
| A4 | `test_a4_openai_rows_reexported_same_object_and_legacy_rates` | `OPENAI_PRICE_USD_PER_1M is openai_pricing.PRICE_USD_PER_1M`; `LEGACY_TRACK_RATES_USD_PER_1M == (rows["gpt-4o-mini"]["input"], rows["gpt-4o-mini"]["output"])` (the literal lives in the test) | RED | 2.2 |
| A5 | `test_a5_haiku_price_with_every_cache_field` | `price_call("anthropic", "claude-haiku-5-5", input 1000, output 200, cache_read 5000, cw5m 2000, cw1h 1000)` == approx 0.0007 (abs 1e-12) | RED | 2.3 |
| A6 | `test_a6_sonnet_price_and_cache_read_is_010` | Sonnet 1000 / 200 / cache_read 5000 == approx 0.0045 | RED | 2.3 |
| A7 | `test_a7_web_search_is_001_each` | Haiku 0 / 0 / ws 3 == approx 0.03; Sonnet ws 1 == approx 0.01 | RED | 2.3 |
| A8 | `test_a8_batch_halves_tokens_not_search` | Haiku 1000 / 200 batch == approx 0.0001; + ws 1 == approx 0.0101 | RED | 2.3 |
| A9 | `test_a9_haiku_long_context_tier` | 150000 / 1000 == approx 0.0775; input exactly 100000 / 1000 == approx 0.0105 (base tier); 100001 / 1000 == approx 0.0525005; input 60000 + cache_read 50000 -> None; Sonnet 150000 / 1000 at flat rates == approx 0.31 | RED | 2.3 |
| A10 | `test_a10_unknown_ids_and_bad_counts_price_to_none` | None for "claude-haiku-5-5-20261001", "claude-opus-5-5", "", None, 123, provider "mistral"; None for a bool, a float, a negative count | RED | 2.3 |
| A11 | `test_a11_openai_price_delegates_bit_identically` | `price_call("openai", "gpt-4o", input 800, cache_read 200, output 100) == openai_pricing.list_price_usd("gpt-4o", 1000, 100, 200)` (==, not approx) for gpt-4o and gpt-4o-mini over 5 token tuples; None with a cache write, a web search or batch | RED | 2.3 |
| A12 | `test_a12_provider_of` | claude-haiku-5-5 / claude-sonnet-5-5 -> anthropic; gpt-4o / gpt-4o-mini / gpt-5 / omni-moderation-latest -> openai; "o3", "", None, 7 -> None | RED | 2.2 |
| A13 | `test_a13_record_keys_and_otel_map` | `LLM_RECORD_KEYS` exactly the 15 names in order; `OTEL_GENAI_ATTRIBUTES` exactly the 5 entries of 2.2 | RED | 2.2 / 2.4 |
| A14 | `test_a14_anthropic_usage_normalisation` (param: breakdown present; breakdown absent; dict usage; object usage; garbage usage) | input 300, output 50, cache_read 4000, cache_creation 1500 = 5m 1000 + 1h 500, ws 2 -> prompt_tokens 5800, completion 50, the three cache fields, cost == price_call(...); no breakdown -> cw5m 1500, cw1h 0; garbage -> every token None, cost None, no raise | RED | 2.2 |
| A15 | `test_a15_openai_entry_record` | a recorded gpt-4o entry 1000 / 200 / cached 300 -> record input 700, cache_read 300, prompt 1000, output 200, cost == the entry's `cost_usd` (==); the unpriced entry shape -> None tokens and cost; keys == `LLM_RECORD_KEYS` | RED | 2.2 |
| A16 | `test_a16_summary_cost_semantics` | zero records -> cost 0.0, complete True; all unpriced -> None, False; mixed -> round(sum priced, 6), False; token sums skip None; by_provider / by_model | RED | 2.5 |
| A17 | `test_a17_records_cap_64` | 65 records -> `len(records) == 64`, `records_truncated` True, totals over all 65; 64 -> False | RED | 2.5 |
| A18 | `test_a18_merge_llm_summaries` | None + x = x; counts add; cost None only when both None; complete AND; records concatenated a then b; one side records None -> None | RED | 2.2 |
| A19 | `test_a19_record_llm_call_no_op_unbound_and_appends_bound` | unbound: returns None, no raise, `current_llm_records()` None; bound: a copy restricted to `LLM_RECORD_KEYS` appended (an extra key dropped; the caller's dict not mutated) | RED | 2.2 |
| A20 | `test_a20_spend_ledger_row_shape_and_validation` | keys == `SPEND_LEDGER_COLUMNS`; sums, request_count, cost round 6, complete; `ValueError` for each invalid input of 2.2 (one param row each, 9 rows) | RED | 2.2 |
| B1 | `test_b1_rest_compare_carries_metadata_llm` (`ENABLE_LLM_LEDGER_V2=true`, distinct client) | `metadata.llm` present; calls == dispatches (11); records len 11 in dispatch order with provider openai and the REQUESTED models; the OpenAI fields of 2.5 equal `metadata.openai`'s; `by_provider == {"openai": {"calls": 11, "cost_usd": metadata.openai.cost_usd}}`; `price_table_as_of` dict | RED (key absent) | RB |
| B2 | `test_b2_stream_complete_carries_metadata_llm` | B1 on the `complete` payload | RED | RB |
| B3 | `test_b3_hard_cap_partial_carries_metadata_llm` (cm17 shape) | `metadata.partial` True and `metadata.llm.calls == 1`, cost approx 0.00027, records len 1 | RED | RB |
| B4 | `test_b4_flag_off_no_metadata_llm_full_config` (param: unset, "", "false", "0", "off", "no", " FALSE ") | REST and stream bodies carry no `metadata.llm`; recorders on `llm_pricing.build_llm_metadata` / `summarize_llm_records` / `tracked_call_cost_usd` (when the module exists) read 0 calls | PIN | 2.9 |
| B5 | `test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording` (distinct client, flag "false") | `metadata.openai` == the literal recorded at base by RED (calls 11, cost 0.017992, by_model, tokens) and `metadata.total_cost == 0.016634`, `serper_calls == 8`, `gpt_calls == 9` (the probe values; RED re-records the full literal at base and pastes it) | PIN | 2.9 |
| B6 | `test_b6_caller_metadata_override_wins` (ON, direct builder call, `metadata={"llm": {"x": 1}}`, `openai_usage` = a summary) | `metadata.llm == {"x": 1}` | PIN (the base override merge already yields it; kills M4) | RB |
| B7 | `test_b7_builder_without_openai_usage_writes_no_llm` (ON) | `"llm" not in metadata` | PIN (green at base, kills an unconditional write) | RB |
| B8 | `test_b8_unverified_ledger_gives_totals_without_records` (ON, a bound ledger of 2 entries, a hand-made `openai_usage` of 3 calls) | `metadata.llm.calls == 3`, `records is None`, cost == the summary's | RED | 2.2 build_llm_metadata |
| B9 | `test_b9_llm_ledger_records_join_metadata_llm` (ON, cm17-shape impl binds `start_llm_ledger()` and records one Haiku record) | `metadata.llm.calls == 2`, `by_provider` has anthropic (calls 1, cost == price_call), `metadata.openai.calls == 1` (OpenAI-only), records len 2 | RED | 2.2 |
| C1 | `test_c1_track_prices_the_matched_ledger_entry` (ON, a fresh service, a bound ledger with a recorded gpt-4o 1187 / 233 entry) | `svc.total_cost` delta == approx 0.0052975 (abs 1e-12); api_calls / gpt_calls +1 | RED (mini 0.00031785) | TG |
| C2 | `test_c2_each_entry_claimed_once` (ON, two entries with the same tokens: gpt-4o-mini then gpt-4o) | two calls add the mini cost then the 4o cost (sum == both); a third call with the same tokens adds the base estimate | RED | TG |
| C3 | `test_c3_no_bound_ledger_is_bit_identical_base` (ON and OFF, 5 token tuples) | delta == `(p * 0.15 / 1_000_000) + (c * 0.60 / 1_000_000)` (==) | PIN | 2.2 legacy |
| C4 | `test_c4_unmatched_usage_is_base_estimate` (ON) | delta == the base expression (==) | PIN | TG |
| C5 | `test_c5_unpriced_match_is_base_estimate_never_none` (ON, a gpt-5 entry) | delta == base expression; `isinstance(svc.total_cost, float)` | PIN | TG |
| C6 | `test_c6_flag_off_adds_base_estimate_with_ledger_bound` (flag "false", a gpt-4o entry bound, claims primed) | delta == base mini estimate (==); the `tracked_call_cost_usd` recorder reads 0 calls | PIN | 2.9 |
| C7 | `test_c7_e2e_tracked_deltas_follow_the_ledger` (ON, distinct client, REST) | every tracked delta == the cost of a distinct ledger entry with equal tokens; the verdict delta == approx (p*2.5 + c*10)/1e6; `metadata.total_cost == round(sum(deltas) + serper + tier15 amounts, 6)` via recorders on `_track_serper_cost` / `_track_cost_amount` | RED | TG |
| C8 | `test_c8_claims_reset_on_a_new_ledger` (ON, one instance, two `start_openai_ledger()` binds) | the second ledger's identical-token entry is claimed (not blocked by the first ledger's claim) | RED | 2.2 |
| C9 | `test_c9_claims_never_mutate_ledger_entries` (ON) | the bound entries `==` their pre-call copies after tracking; `summarize_openai_ledger` unchanged | PIN (green at base; kills M18) | TG |
| D1 | `test_d1_v1_vision_cost_priced_by_model` (ON, `OPENAI_MODEL_VISION=gpt-4o`, 500 / 100) | cost == 0.00225 | RED (0.000135) | OV1 |
| D2 | `test_d2_v1_vision_cost_prices_cached_tokens` (ON, mini, 500 / 100 / cached 200) | cost == 0.00012 | RED (0.000135) | OV1 |
| D3 | `test_d3_v1_flag_off_full_config_base_cost` (flag "false", gpt-4o, 500 / 100) | cost == 0.000135; `openai_usage_cost_usd` recorder 0 calls | PIN | 2.9 |
| D4 | `test_d4_v1_unpriced_model_falls_back_to_base` (ON, `OPENAI_MODEL_VISION=gpt-5`) | cost == 0.000135 (a float) | PIN | OV1 |
| D5 | `test_d5_v2_vision_cost_priced_by_model` (ON + `ENABLE_VISION_IDENTITY_V2=true`, gpt-4o, the B3 V2 fake at `:620-640` shape with usage 100 / 15) | cost == round((100*2.5 + 15*10)/1e6, 6) = 0.0004 | RED (2.4e-05 class) | OV2 |
| D6 | `test_d6_disambiguation_cost_priced_by_model` (ON, `OPENAI_MODEL_STANDARD=gpt-4o`, 300 / 20) | cost == 0.00095 | RED (5.7e-05) | OD |
| D6b | `test_d6b_disambiguation_flag_off_base_cost` (flag "false", the same env and usage, recorders on) | cost == 5.7e-05; `openai_usage_cost_usd` recorder 0 calls | PIN | 2.9 |
| E1 | `test_e1_record_usage_accepts_provider_keyword` | `"provider" in inspect.signature(ModelRouterService.record_usage).parameters` with default None | RED | MR |
| E2 | `test_e2_record_usage_skips_non_openai_provider` (ON) | `record_usage("gpt-4o", 100, provider="anthropic")` -> 0 increments; `provider="openai"` -> 1 | RED (guarded by E1's check, asserts first) | MR |
| E3 | `test_e3_record_usage_skips_claude_verdict_id` (ON, `OPENAI_MODEL_VERDICT=claude-sonnet-5-5`) | `record_usage("claude-sonnet-5-5", 100)` -> 0 increments | RED (1 at base) | MR |
| E4 | `test_e4_flag_off_claude_verdict_id_counts_as_base` (flag "false", same env) | 1 increment | PIN | 2.9 |
| E5 | `test_e5_get_model_claude_verdict_skips_the_counter` (ON, same env) | returns "claude-sonnet-5-5", `_get_4o_usage_today` 0 calls | RED (1 call) | MR |
| E6 | `test_e6_get_model_openai_cap_unchanged_both_states` (ON and OFF; used 900000 of 1000000) | returns the standard model; counter read once | PIN | MR |
| F1 | `test_f1_public_share_strips_metadata_llm_and_openai` | neither key in the public body; `total_cost` and `query` kept; the handed dict still carries both (copy) | RED (llm passes) | S |
| F2 | `test_f2_public_share_strips_llm_only_row` | `llm` absent; other keys intact | RED | S |
| F3 | `test_f3_public_share_row_without_either_key_unchanged` | the body's `full_response` == the stored one (and the cm16 fixture still yields cm16's body) | PIN | S |
| F4 | `test_f4_owner_history_view_keeps_metadata_llm` (cm18 shape) | the owner view returns `metadata.llm` | PIN | S |
| G1 | `test_g1_admin_costs_sums_metadata_llm` (ON; rows with llm costs 0.004 / 0.0012 partial / 0.0 / legacy / corrupt) | `summary["llm"]` cost 0.0052, rows 5, with_cost 3, partial 1, without 2, complete False, by_provider sums, note == `LLM_COST_NOTE` | RED | AD |
| G2 | `test_g2_admin_costs_api_carries_llm_block` (ON) | `body["llm"]` == the G1 aggregate shape for the window | RED | AD |
| G3 | `test_g3_flag_off_admin_queries_and_keys_are_base` (flag "false", rows carrying metadata.llm) | the issued select strings == exactly the base list (openai JSON path pages + the count); no `llm` key in either body; every base key present with the base values | PIN | 2.9 |
| G4 | `test_g4_on_openai_block_identical_to_off` | `/costs` and `/costs/api` minus `llm` are equal between the flag states (time-insensitive fields) | PIN (OFF half green; ON half asserts equality after removing `llm`, passes at base too) | AD |
| G5 | `test_g5_llm_read_failure_is_unknown_not_zero` (ON, the llm path raises on both selects) | `llm.cost_usd is None`, `rows == 0`, `cost_complete is None`; `openai` block intact; the WARNING carries the exception type name only | RED | AD |
| G6 | `test_g6_admin_key_guard_unchanged` (both states) | no key -> 403; wrong key -> 403 | PIN | AD |
| G7 | `test_g7_costs_html_renders_llm_block_safely` | regex: `id="llmKpis"`; a `renderLlmKpis` function guarded by an `api.llm` object check; `fmtUsd(api.llm.cost_usd`; `${api.llm.note || ""}`; called from `load()`; added bytes ASCII; the cm12 forbidden phrases absent | RED | CH |
| G8 | `test_g8_llm_cost_note_text` | `LLM_COST_NOTE` ASCII; contains "list price", "persisted comparisons only", "not a bill", "llm_spend_ledger", "retried by the sdk" (lower-cased); `OPENAI_COST_NOTE` byte-equal to its base literal | RED | AD |
| H1 | `test_h1_050_and_rollback_exist_once_and_reserved_numbers_absent` | exactly `050_llm_spend_ledger.sql` forward and rollback; no `045_*`..`049_*` (reserved, F4) and no `039_*` | RED | 2.7 |
| H2 | `test_h2_050_one_transaction_creates_exactly_the_table` | one BEGIN / COMMIT; one CREATE TABLE `public.llm_spend_ledger`; the column names == `{"id", "created_at"} + SPEND_LEDGER_COLUMNS`; the CHECK lists for lane / mode / provider / basis; `cost_usd` nullable numeric(14,6) | RED | 2.7 |
| H3 | `test_h3_050_is_service_role_only_and_append_only` | RLS enabled; REVOKE ALL FROM PUBLIC, anon, authenticated; exactly one GRANT = `SELECT, INSERT` to service_role; no UPDATE / DELETE / TRUNCATE grant; no POLICY, FUNCTION, INDEX, TRIGGER, ALTER of another table | RED | 2.7 |
| H4 | `test_h4_050_outside_the_043_fence` | `fence_user_tables(real_forward_files())` has no `llm_spend_ledger` entry; `fence_report(...)["table_gaps"]` empty; the file contains `llm_spend_ledger` (so the scan is not vacuous) | RED | 2.7 |
| H5 | `test_h5_050_header_and_rollback` | header states "CHANGES NOTHING IN PRODUCTION", apply any time, no flag, the postcheck grid and the rollback path; rollback drops only the table and says destructive | RED | 2.7 |
| I1 | `test_i1_camera_merges_vision_into_metadata_llm` (ON, cm15b harness with the compare's metadata carrying an llm summary of 3 calls) | `metadata.llm.calls == 4`, the vision record first, cost == vision + compare, complete AND | RED | IR |
| I2 | `test_i2_camera_flag_off_no_metadata_llm` (flag "false", the same harness incl. a compare llm summary) | `"llm"` in metadata only as the compare's own dict passed through UNMERGED? NO: the fake compare returns metadata WITHOUT llm under OFF (as the builder would); assert no `llm` key and `metadata.openai` == cm15b's | PIN | 2.9 |
| I3 | `test_i3_camera_vision_cost_follows_the_vision_model` (ON, `OPENAI_MODEL_VISION=gpt-4o`, 500 / 100) | `metadata.vision_cost == 0.00225`; `metadata.total_cost == round(0.01 + 0.00225, 6)` | RED | OV1 + IR |
| J1 | `test_j1_track_matches_an_llm_record` (ON, an llm ledger record for Haiku with prompt 5800 / completion 50) | `_track_gpt_cost({"prompt_tokens": 5800, "completion_tokens": 50})` adds the record's cost | RED | TG |
| K1 | `test_k1_guarded_llm_create_untouched` | sha256 of `ast.dump(<guarded_llm_create>, include_attributes=False)` == `8fa87b61645971d65a41d38cf70938f38d441d0b0a0d91a055b16d74b1b3a63d` (CPython 3.12) | PIN | 0 |
| K2 | `test_k2_openai_pricing_untouched` | sha256 of the LF-normalised text of `openai_pricing.py` == `0406b617bd91b2a1ea5a5bacd37fd48e28e106ed99991bfec9087d144ec14094` | PIN | 0 |
| K3 | `test_k3_leaf_has_no_url_or_gpt_literal` | no non-docstring string literal in `llm_pricing.py` holds `http://` / `https://`; no `["']gpt-` literal on a non-comment line | RED (file absent: assert on existence) | 1.7 |

Counts: 75 rows (A1-A20, B1-B9, C1-C9, D1-D6 + D6b, E1-E6, F1-F4, G1-G8, H1-H5, I1-I3, J1, K1-K3); RED 53 (A1-A20; B1, B2, B3, B8, B9; C1, C2, C7, C8; D1, D2, D5, D6; E1, E2, E3, E5; F1, F2; G1, G2, G5, G7, G8; H1-H5; I1, I3; J1; K3); PIN 22 (B4, B5, B6, B7; C3, C4, C5, C6, C9; D3, D4, D6b; E4, E6; F3, F4; G3, G4, G6; I2; K1, K2). Parametrised rows (A2, A10, A14, A20, B4, C3, G6) expand to about 100 collected nodes; the RED agent reports the exact per-node split at base.

## 6. Mutation table (on GREEN's bytes; each mutant on a byte copy, restored and sha256-checked; `--bound 600` per mutant via `pyt.py -k`)

| # | Mutant | Killing rows |
|---|---|---|
| M1 | `llm_ledger_v2_enabled` returns True always | B4, C6, D3, D6b, E4, G3, I2 |
| M2 | the reader drops `.strip().lower()` | A2 (" TRUE ", " FALSE ") |
| M3 | RB writes `metadata.llm` without the flag check | B4 |
| M4 | RB writes `metadata.llm` after the caller override merge | B6 |
| M5 | `build_llm_metadata` takes records without the summary-equality check | B8 |
| M6 | zero-call summary cost None instead of 0.0 | A16 |
| M7 | all-unpriced summary cost 0.0 instead of None | A16 |
| M8 | cache_write_1h priced at the 5m rate | A5 |
| M9 | the web search fee halved under batch | A8 |
| M10 | long-context threshold `>=` instead of `>` | A9 (input exactly 100000) |
| M11 | long-context cache tokens priced instead of None | A9 |
| M12 | a dated claude id priced from the base row (prefix match) | A10 |
| M13 | OpenAI `price_call` re-implements the arithmetic (no delegation) | A11 (== on 5 tuples) |
| M14 | `tracked_call_cost_usd` never marks a claim | C2 |
| M15 | an unpriced match returns None into the float sum | C5 |
| M16 | the TG OFF branch deleted (ON body always) | C6 |
| M17 | claims not reset on a new ledger | C8 |
| M18 | claims stored by mutating the ledger entry dicts | C9 |
| M19 | OV1 ignores cached tokens (prompt priced at full input) | D2 |
| M20 | OV1 / OV2 / OD branch not gated | D3, D6b |
| M21 | `record_usage` ignores `provider` | E2 |
| M22 | `get_model` ON still reads the counter for a claude verdict id | E5 |
| M23 | MR `record_usage` gate inverted (skips openai) | E2 (`provider="openai"` -> 1), E6 |
| M24 | share strips only `openai` | F1, F2 |
| M25 | share strip mutates the stored dict in place | F1 |
| M26 | the admin llm block computed with the flag OFF | G3 |
| M27 | an llm read failure reported as 0.0 | G5 |
| M28 | the llm read reuses / widens the openai select string | G3, G4 |
| M29 | `costs.html` renders `api.llm.cost_usd` without `fmtUsd` | G7 |
| M30 | migration grants UPDATE to service_role | H3 |
| M31 | migration REVOKE omits anon | H3 |
| M32 | migration adds a `device_id` column | H4, H2 |
| M33 | the camera overwrites `metadata.llm` with the vision summary instead of merging | I1 |
| M34 | the camera merge runs with the flag OFF | I2 |
| M35 | `record_llm_call` raises without a bound ledger | A19 |
| M36 | `build_llm_metadata` ignores the llm-ledger records | B9 |
| M37 | Anthropic normalisation leaves cache_read out of `prompt_tokens` | A14, J1 |
| M38 | the records cap keeps 65 | A17 |
| M39 | `spend_ledger_row` emits an extra key | A20 |
| M40 | `_track_gpt_cost` OFF branch reordered to `(p+c-mix)` / a different operation order | C3, C6 (== exact) |

Equivalent survivors, if any, are reported for a ruling with the measured reason.

## 7. Comm set and gates for GREEN (cheapest first)

1. `py_compile` and `ruff check --select E9,F63,F7,F82 --no-cache` on every edited / new `.py`; `json.loads` not applicable; bytes > 127 = 0 on every NEW file and on the ADDED lines of `costs.html` / `CLAUDE.md` (`git diff -U0` added-line scan).
2. `sqlfluff lint --config .sqlfluff migrations/050_llm_spend_ledger.sql migrations/rollback/050_llm_spend_ledger.sql` -> 0 violations.
3. The RED file ON and OFF (`ENABLE_LLM_LEDGER_V2=true` exported for that ONE runner call only; never in `.env`), bound 600: all green ON-intended and PIN rows green in both.
4. The pin files of section 4.2 that are cheapest and closest: `tests/test_cost_meter_s74.py tests/test_s75_fanout_identity.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py tests/test_u3c_store_false_pin.py tests/test_model_config.py tests/test_legal_docs_u8.py tests/test_sqlfluff_config.py tests/test_migration_043_delete_user_cascade.py tests/test_migration_index_predicate_immutability.py tests/test_s80_b3_vision_identity_v2.py tests/test_model_router.py tests/test_share_routes.py`, bound 1200, flag unset.
5. CI-order set (sorted, one process, bound 1200): the step-4 files + `tests/test_cost_dashboard.py tests/test_admin_referral_endpoints.py tests/test_variant_llm_hint_b3b.py tests/test_camera_vision.py tests/test_paid_route_metering.py tests/test_retro_w2_1.py tests/test_s70_model_router_downgrade.py tests/test_m18_openai_tpm_sizing.py tests/test_security_regression.py tests/test_s81_s03_llm_ledger_v2.py`.
6. The comm set (zero-regression gate): 364 files measured at base in this run (`notes/comm_set.txt`) = module and symbol reference grep of the edited modules (structured_comparison_service / StructuredComparisonService / get_comparison_service, openai_service / identify_products / disambiguate_variant_line, model_router / ModelRouterService / DAILY_4O_CAP, response_builder / build_comparison_response, image_routes / `/api/v1/image`, share_routes / `/api/v1/share`, admin_routes / `/api/v1/admin` / costs.html, openai_pricing / llm_pricing; 275 files) UNION the source-scanning tests (tests reading `app/` by path, `inspect.getsource`, `ast.parse`, `rglob`; 127) UNION the named source-scanning pins (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit) UNION the CLAUDE.md readers (34 files naming CLAUDE.md, test_ci_gates and test_behavior_dimension_translation among them) UNION the migration readers (31) UNION the SmartCompareApp-scanning backend tests (25; `metadata.llm` is part of the client-visible owner response) UNION the importers of the harness modules this RED file imports (test_cost_meter_s74, test_openai_breaker, test_compare_timeout_graceful, test_response_builder_phase1_none_guard: 5 files) UNION the FY25 / W4-13 pins and test_legal_docs_u8 / test_sqlfluff_config; MINUS the 4 `test_precommit_hook*.py` files (no `.githooks` edit). GREEN re-derives the set at HEAD (the new RED file joins it), runs it in chunks of at most 25 files, bound 1200 each, at base and at head, flag unset, and reports `comm -13` of the sorted FAILED node-id sets EMPTY; the 2 tiktoken `test_prompt_truth.py` nodes are the known environmental base noise (record identically at base and head). A branch-only-new failure is re-run against base to tell a network flake from a regression.
7. The pre-commit hook runs on GREEN's commit (sqlfluff on the staged migrations, ruff, py_compile, the credential scan); the hook test files are NOT re-run (no `.githooks` edit).
8. The mutation table of section 6 (one mutation harness, the `.qa-mutation.lock` rule).

## 8. CLAUDE.md flag row and owner steps

Row text for GREEN (after the SESSION 80 B3 VISION-IDENTITY-V2 paragraph at `CLAUDE.md:476-477`, before `## Tests` at `:479`; ASCII; the D03 row of the same session lands in the same place, known rebase):

**SESSION 81 flag (S81-03, 2026-10-22; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); spec `.qa-s80/S81-03_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_LLM_LEDGER_V2` (S81-03, `app/services/llm_pricing.py::llm_ledger_v2_enabled`, a leaf over the untouched `openai_pricing.py`). **Effect ON:** one function prices any provider (`price_call`: the OpenAI rows of `openai_pricing` by delegation; claude-haiku-5-5 0.10 / 0.50 per MTok, cache read 0.01, 5-minute write 0.125, 1-hour write 0.20, 0.50 / 2.50 above 100K prompt tokens with no cache tokens (with cache tokens: unpriced); claude-sonnet-5-5 2 / 10, cache read 0.10, writes 2.50 / 4.00; Batch halves token charges, never the 0.01-per-request web search fee; any other id = null, never 0; read from platform.claude.com on 2026-10-22); `build_comparison_response` adds `metadata.llm` beside `metadata.openai` on all three build paths (provider-neutral totals equal to `metadata.openai` for OpenAI traffic, `by_provider`, `by_model`, up to 64 per-call records verified against the summary, else `records: null`), and the camera route merges its vision call into it; `_track_gpt_cost` prices each tracked call from the ledger entry it came from (so `metadata.total_cost` and `search_logs.cost` carry the real gpt-4o verdict price, 16.7x the old mini-rate estimate in the unit's probe), the vision and variant-disambiguation costs use the vision / standard model's row, and `ModelRouterService` never charges the OpenAI 4o token cap for a call served by another provider (`record_usage(..., provider=)`, a claude verdict id skips the counter); `/api/v1/admin/costs` and `/costs/api` add an `llm` block (a separate paged read of `full_response->metadata->llm`; null when nothing is recorded, never 0) that `costs.html` renders. **Flag OFF:** byte-identical (pinned by `tests/test_s81_s03_llm_ledger_v2.py` B4 / B5 / C6 / D3 / E4 / G3 / I2, the FY25 nine digests, the W4-13 45-scenario ledger and `tests/test_cost_meter_s74.py`). **Unflagged (no-op on every row written OFF):** the public share view strips `metadata.llm` with `metadata.openai`. **Migration 050** `public.llm_spend_ledger` (append-only, service role only, no user data) is written, NOT applied, and inert until S81-16 / S81-22 write batch and cron spend through `llm_pricing.spend_ledger_row`; apply any time, PRECHECK / POSTCHECK in the session-81 state folder. **Stated limits:** calls no caller tracks (the gpt-4o Tier-3 synthesis: 2 of 11 calls and 58 % of the LLM list price in the probe; classification, disambiguation, the Tier-3 image) are in `metadata.llm` but not in `metadata.total_cost`; OpenAI records carry no role, latency or stop reason; prices are literals with a read date, never fetched; the llm ledger is bound by S81-06, so `metadata.llm` holds OpenAI calls only until then. **Canary (after approval, the owner's yes):** three never-compared pairs; `metadata.llm.cost_usd` == `metadata.openai.cost_usd`, `records` length == `calls`, `metadata.total_cost` above its pre-flip level by the verdict delta; `/admin/costs` `llm` block present. **Rollback:** unset the variable (per call, immediate).

Owner steps (names only): none to merge; to apply 050: the PRECHECK, ONE_PASTE and POSTCHECK in the SQL editor (any time; no flag depends on it); to flip: set `ENABLE_LLM_LEDGER_V2=true` on `web` in its own canary window after approval (PLAN_S81 flip order: "ledger, breaker, request context ON").

## 9. Stated limits

- L1 Untracked calls: `_track_gpt_cost` prices only the calls a caller tracks; the gpt-4o Tier-3 synthesis (`tier3_synthesize_non_negotiables`, `scs:839-891`), `classify_category_llm`, `disambiguate_variant_line`, the Tier-3 image call and the critic when not tracked stay out of `metadata.total_cost` / `search_logs.cost` (as at base) while `metadata.llm` carries them. Measured: 2 of 11 dispatches, 0.0103775 of 0.017992 USD in the probe harness. Closing it needs a lane-A hunk (OQ-2).
- L2 OpenAI records carry `role`, `latency_ms`, `stop_reason` None: the only capture point is `guarded_llm_create`, which this unit must not touch; S81-06's router (above the chokepoint) owns role and latency for every provider.
- L3 The llm ledger (`start_llm_ledger`) is not bound by this unit (no scs entry hunk); until S81-06 binds it, `record_llm_call` is a no-op and `metadata.llm` holds OpenAI calls only.
- L4 The match is by (prompt_tokens, completion_tokens): two calls with identical counts on different models can swap costs between them; the sum is exact whenever both are tracked, and off by the price difference when only one is (vanishingly rare with real counts; a stated limit, not a defect).
- L5 The Haiku over-100K tier is priced for input and output only (R1's cited line); a request above 100K with any cache token is unpriced until the tier's cache rates are read from the live page (OQ-4). Sonnet 5.5 long-context pricing is not modelled (flat rates apply).
- L6 No live price fetch: every rate is a literal with a read date (`PRICE_TABLE_AS_OF`); a price change on either provider needs a code change.
- L7 An Anthropic usage without the `cache_creation` breakdown counts every cache write as 5-minute (the cheaper rate): a 1-hour write then under-prices by 0.075 / 1.50 USD per MTok (Haiku / Sonnet).
- L8 The Batch rate applies only to records flagged `batch=True`; none exist until S81-16.
- L9 Under ON a vision response without usage costs 0.0 instead of raising (base V1 raises AttributeError there and the route reports a vision failure); the ON path is more tolerant by design.
- L10 `metadata.llm` adds about 2-4 KB per persisted comparison (up to 64 records); the admin read pages it like `metadata.openai`.
- L11 The admin `llm` block exists only while the flag is ON (a rollback hides it; the stored rows keep the key, and the public share view still strips it).
- L12 Link-mode compares are never persisted (#340), so neither `metadata.openai` nor `metadata.llm` reaches the admin sums for them; off-clock spend reaches them only after S81-16 / S81-22 write `llm_spend_ledger`, and no admin view reads that table yet.
- L13 K1 pins `guarded_llm_create` by an `ast.dump` hash on CPython 3.12; a Python minor upgrade or S81-04's chokepoint change re-records it deliberately.

## 10. Out of scope

The Anthropic adapter, SDK, router, consent gating and any Claude call (S81-06); the spend breaker and its caps (S81-04); the census comment at `api_budget_service.py:934-952`; `guarded_llm_create`; tracking the untracked calls (OQ-2); any write to `llm_spend_ledger` and an admin view of it (S81-16 / S81-22 / a follow-up); compare_runs (S81-22); the privacy / processors text (S81-12); the `OPENAI_COST_NOTE` wording about the OpenAI free allowance (true until OpenAI is off; S81-12 or the OpenAI-off change rewrites it); the client; Opus 5.5 rows; OpenAI Batch rates; a live price fetch.

## 11. Open questions for the orchestrator

- OQ-1 Branch name: `feature/s81-llm-ledger-v2` (the template's `feature/s81-<slug>`).
- OQ-2 Cost truth for untracked calls: accept L1 for this unit (recommended; the scs hunk budget is one) or rule a follow-up lane-A unit that tracks the Tier-3 synthesis usage (`scs:839-891`) and the classifier, so `metadata.total_cost` equals non-LLM + `metadata.llm.cost_usd` on success rows.
- OQ-3 The share strip ships UNFLAGGED (R-A1(c): a no-op on every row written OFF; flagging it would expose `metadata.llm` after a rollback). Confirm, or rule it behind the flag.
- OQ-4 The cache-token rates inside the Haiku over-100K tier (and whether Sonnet 5.5 has a long-context tier) need a read of the live pricing page by someone allowed to fetch it; until then L5 stands.
- OQ-5 Binding `start_llm_ledger()` at `scs:4146` / `scs:4740` / `image_routes.py:340` now (three one-line hunks, two of them in scs) instead of in S81-06: recommended to leave to S81-06 (lane A owns scs; the brief's one-hunk rule).
- OQ-6 The OpenTelemetry GenAI names in `OTEL_GENAI_ATTRIBUTES` (provider.name, request.model, usage.input_tokens / output_tokens, response.finish_reasons) are stated from the spec writer's knowledge, not fetched; S81-22 should verify them (and any cache-token attribute names) against the semantic conventions before it relies on them.
- OQ-7 E1 (adding the flag to FY25's `UNIT_ENV`) is optional hygiene; drop it if the gate prefers every 4.2 pin byte-unedited.

## Not done in this spec

No RED file, no prototype of the GREEN code (the satisfiability rests on probe P1 / P2 and the arithmetic in section 5), no comm-set run (base or head), no mutation run, no sqlfluff run on the 050 DDL (it does not exist yet), no live read of any pricing page, Railway, Supabase or Anthropic.
