# U3c privacy pins - spec (session 74, 2026-10-08)

Base: main dfbda511 (worktree sc-s71-t0b, branch feature/s74-u3c-privacy-pins, clean). Evidence and logs:
NOTES = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad/u3c/spec
(notes.md, census.py/.out, sdk_body_probe.py/.out, draft/ = ready RED test files, u3c_green_scratch.patch = the GREEN
measured in a detached scratch worktree, since removed). All file:line below are at dfbda511 unless marked.

## 0. Scope and non-goals
- (a) `store=False` on every OpenAI chat-completion dispatch: ONE line at the chokepoint
  `app/services/api_budget_service.py::guarded_llm_create` (def :951) covering both branches, plus the two direct
  dispatches outside the chokepoint in `scripts/` (in scope per the brief). Unconditional, no flag.
- (b) the Loop 2 referral push shows the invitee's display name or no name; never any part of the email.
- Policy sentences made true (U8 redraft, origin/feature/s73-u8-legal @ 6c74d9b6): `landing/privacy.html:246`
  ("OpenAI may keep data sent to its API in abuse-monitoring logs for up to 30 days": no stored completion on top;
  the training half of :246 is rewritten by OA2, the pin stands per OA3) and `:264` (section 5: "the notification
  we send that friend can show your display name").
- Non-goals: Responses API (no `responses.create` under app/ or scripts/); embeddings (no call exists); moderation
  (`content_safety_service.py:252` `moderations.create`, no store parameter); U3b; U8 text; OpenAI org settings
  (OA2/OA3); `backend/` (legacy, NOT deployed: Procfile and railway.json start `app.main`; CLAUDE.md:41 "Do NOT
  edit"; it has 23 direct dispatches, untouched).

## 1. Code truth table at main
Client constructions (all `AsyncOpenAI`, no sync `OpenAI(`): extraction_service.py:76 (get_client :64);
openai_service.py:34 (module singleton), :63 (shared project) and :72 (private project, env NAME
OPENAI_API_KEY_PRIVATE) in get_client :48; url_extraction_service.py:33 (get_client :29). image_service.py:42 and
verdict_critique_service.py:39 import openai_service.get_client. scripts/: none (they reuse extraction_service.get_client).

Dispatch nodes (AST census over app/ scripts/ tests/, census.out):
| site | function | kwargs | via chokepoint |
| api_budget_service.py:967 | guarded_llm_create, flag OFF bare dispatch | **kwargs | IS the chokepoint |
| api_budget_service.py:974 | guarded_llm_create, flag ON after admission :968 | **kwargs | IS the chokepoint |
| extraction_service.py:1385/1525/1583/1742/1847 | classify_category_llm / parse_product_query / extract_specs / extract_price / extract_reviews | model, messages, **token_limit_kwargs, **sampling_kwargs | yes |
| extraction_service.py:1791 | extract_price_from_training_data | same + **_json_mode (:1790, response_format only) | yes |
| extraction_service.py:2643, 2685 | generate_comparison primary + fallback | same + response_format | yes |
| openai_service.py:217 | identify_products (vision) | model, messages, helpers | yes |
| openai_service.py:328/403/465 | extract_specs_targeted / extract_specs_synthesized / disambiguate_variant_line | + response_format | yes |
| image_service.py:179 | extract_image_via_gpt | model, messages, helpers | yes |
| url_extraction_service.py:434 | extract_with_ai | model, messages, helpers | yes |
| verdict_critique_service.py:174 | critique_verdict | + response_format | yes |
| scripts/seed_spec_spine.py:382 | extract_spine_specs (off-clock seeder) | model, messages, max_tokens, temperature | NO (in scope) |
| scripts/shadow_experiments.py:998 | _create_with_retry (eval harness) | **kwargs | NO (in scope) |
No call site passes store, extra_body, stream, metadata, user or safety_identifier. Helpers: model_config
sampling_kwargs (:107-123) returns only {temperature}, token_limit_kwargs (:126-139) only {max_tokens|max_completion_tokens}.
Chokepoint: flag read per call `llm_preflight_breaker_enabled()` (:709-714, env ENABLE_LLM_PREFLIGHT_BREAKER).
OFF -> :967 bare dispatch. ON -> `_openai_dispatch_admission()` (:792); denied -> LLMUnavailableError, no dispatch;
admitted -> :974 dispatch; CancelledError / Exception / BaseException arms record or release (:975-1011);
`openai_record_success()` when outcome_matters (:1012-1013).

Pinned SDK: requirements.txt:97 openai==3.3.1 = venv `openai/_version.py:2`. `AsyncCompletions.create`
completions.py:2858-2965: `store: Optional[bool] | Omit = omit` :2888; body dict `"store": store` :2937 inside
`await async_maybe_transform(...)` :2909; `extra_body=extra_body` :2956. `_utils/_transform.py:436` skips a
not-given (Omit) value, so an explicit False is kept; `_base_client.py:538-543` merges extra_body OVER the body
(`_merge_mappings` :2278, "the second mapping takes precedence"). Measured with a hermetic MockTransport
(sdk_body_probe.out): omitted -> no store key; False -> false; True -> true; None -> null is SENT;
store=False + extra_body {"store": true} -> TRUE (bypass); stream=True + store=False -> false.
Why explicit matters: OpenAI migrate guide (openai/data notes): "Chat completions are stored by default for new
accounts" and "To disable storage in either API, set store: false"; "Enabled per call" has no official definition.

## 2. The referral push
- referral_service.py:926-930: `display = (invitee.get("display_name") or (invitee.get("email") or "").split("@")[0] or "A friend")`.
- `invitee` = `_load_invitee` (:758-771) or {"id", "email": ""} (try_trigger_loop2 :655-658). `_load_invitee` selects
  "id, email, subscription_tier" (:762): display_name is NEVER loaded, so in production every push with a non-empty
  email shows the email local part. `users.display_name` exists (migrations/014_referral_system.sql:100 RPC reads
  it; 043:84/139 erases it).
- push_service.send_loop2_push (:54-85) localises via `_get_user_language` (:136, users.preferences.language,
  default English) into `_loop2_copy` (:173-194): fallback "Your friend" (:181); EN body
  f"{name}, your friend just used MYEZ. ..." (:191); AR body f"{name}" + U+060C + " " + AR "your friend" (:185).
- i18n: the push text IS localised. A literal "A friend" would give EN "A friend, your friend just used MYEZ." and an
  Arabic body opening with Latin text (today the same happens with the email local part and with "Your friend").
- Other sites: `split("@")` under app/: only :928. `rpartition("@")` at url_routes.py:101, llm_provider.py:124,
  sentry_service.py:325 strip URL credentials (not emails); abuse_detection_service.py:158 reads the domain, never
  displayed. resolve_invite :406/:450-453 (landing payload) uses the RPC display_name or "A friend", no email.
  send_reengagement_push (:88) carries copy chosen by reengagement_service (no email/display_name reference).
  After the unit: push = display name (stripped) or the nameless localised body; nothing else changes.

## 3. Design
- Chokepoint: `kwargs["store"] = False` as the first statement after the docstring of guarded_llm_create (before
  the `if not llm_preflight_breaker_enabled()`), so both branches dispatch with it. HARD OVERRIDE, not setdefault
  (ruling R1): the policy sentence is unconditional, and a caller value that wins would let a future site make it
  false silently; the static pin T03 makes a literal `store=`/`extra_body=` at any call site fail CI instead.
  `**kwargs` is a fresh dict per call, so no caller dict is mutated (T08). Docstring gains 4-5 lines naming U3c.
- extra_body (ruling R2): static only (T03). Runtime scrub `if isinstance(kwargs.get("extra_body"), dict) and
  "store" in kwargs["extra_body"]: kwargs["extra_body"] = {**kwargs["extra_body"], "store": False}` is the
  belt-and-braces alternative (+3 lines, +1 test) if Fable wants it; no caller or spread can carry it today.
- Scripts (R5): seed_spec_spine.py add `store=False,` after `temperature=0.1,` (:389); shadow_experiments.py `_create_with_retry`
  add `kwargs["store"] = False` before the retry loop (:994).
- Referral (R3, R4): referral_service :926-930 -> `display = (invitee.get("display_name") or "").strip()`;
  `_load_invitee` :762 select "id, email, subscription_tier, display_name"; push_service `_loop2_copy`:
  `name = (invitee_display_name or "").strip()`; AR `lead = f"{name}" + U+060C + " " if name else ""` prefixed to
  the unchanged Arabic sentence; EN `lead = f"{name}, your friend" if name else "Your friend"` then
  f"{lead} just used MYEZ. ". Named copy byte-identical (T16); nameless EN = "Your friend just used MYEZ. You got
  N bonus comparisons. Expires in 3 days."; nameless AR = today's Arabic body minus the name prefix (no new
  translation authored). R3 alternative (plan text literally): pass "A friend" (1-line change; drop T14/T15,
  T12 expects "A friend") at the cost of the copy defects in section 2.
- AST pin: tests/test_u3c_store_false_pin.py T01 (statement dominance + single write), T02 (no dispatch outside
  the chokepoint under app/, plus forbidden surfaces with_raw_response/with_streaming_response/stream/parse/
  responses.create/responses.stream), T03, T04. Runtime pin: fake client capturing kwargs, flag patched via
  `monkeypatch.setattr(abs_mod, "llm_preflight_breaker_enabled", lambda: on)`; flag ON also patches
  `_openai_dispatch_admission` -> (True, True, False) and `openai_record_success`. Body pin: real pinned SDK with
  `httpx2.MockTransport` (T09). Referral pin: `patch("app.services.push_service.send_loop2_push")` capturing
  invitee_display_name for present / email-only / neither, plus the push payload end to end.

## 4. Tests (drafts ready: NOTES/draft/, pure ASCII, LF; sha256 store 29f39319..., referral e19ef437...)
RED author copies them verbatim to tests/ (or rewrites; the ids and pins are the contract). RED at main = measured
(u3c-red-at-base: 34 failed, 60 passed); GREEN = measured (u3c-green-set: 94 passed).
tests/test_u3c_store_false_pin.py:
- T01 test_u3c_01_chokepoint_assigns_store_false_before_every_dispatch - RED: no assignment exists.
- T02 test_u3c_02_no_chat_dispatch_outside_the_chokepoint_under_app - GUARD (green at main; kills a bypass).
- T03 test_u3c_03_call_sites_pass_no_store_or_extra_body - GUARD; census floor 15 sites (non-vacuity).
- T04 test_u3c_04_scripts_direct_dispatches_carry_store_false - RED: seed_spec_spine.py:382, shadow_experiments.py:998.
- T05 test_u3c_05_dispatch_carries_store_false[flag_off|flag_on] - RED: no 'store' key; ON asserts record_success x1.
- T06 test_u3c_06_caller_store_true_is_overridden[flag_off|flag_on] - RED: True forwarded (pins R1).
- T07 test_u3c_07_streaming_dispatch_carries_store_false - RED: KeyError 'store'.
- T08 test_u3c_08_caller_dict_is_not_mutated - GUARD.
- T09 test_u3c_09_pinned_sdk_puts_store_false_in_the_request_body[flag_off|flag_on] - RED: body has no store key.
tests/test_u3c_referral_push_name.py:
- T10 test_u3c_10_display_name_is_sent_when_present - GUARD.
- T11 test_u3c_11_email_local_part_is_never_sent[email_only|name_none|name_empty|name_blank] - RED: "sara.q"; blank sends "   ".
- T12 test_u3c_12_no_name_no_email_sends_empty[empty|email_blank|email_none] - RED: "A friend" (pins R3).
- T13 test_u3c_13_load_invitee_selects_display_name - RED: select lacks display_name (pins R4).
- T14 test_u3c_14_nameless_english_copy - RED: "Your friend, your friend just used MYEZ. ...".
- T15 test_u3c_15_nameless_arabic_copy_has_no_latin_fallback - RED: Arabic body opens with Latin "Your friend".
- T16 test_u3c_16_named_copy_is_unchanged - GUARD (EN exact string; AR prefix by code points).
- T17 test_u3c_17_end_to_end_payload_never_carries_the_email_local_part[English|Arabic] - RED: body opens "sara.q".
Existing-test edits (NOT append-only; R6; RED owns them, both turn RED at main for the right reason):
- tests/test_referral_service.py:1011-1012 `== "sara"` (pins the bug) -> `== ""` with a U3c comment.
- tests/test_model_config_enforced.py:266 `assert kw == SHIPPED[site]` -> `assert kw == {**SHIPPED[site], "store": False}`
  (12 params of test_shipped_ids_kwargs_unchanged; becomes a per-site end-to-end store pin for 12 of 15 sites).
Runner (one file per call; PYT = <venv python> C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad/harness/pyt.py):
  PYTHONIOENCODING=utf-8 $PYT --bound 600 --tag u3c-store --log <notes>/u3c-store.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b -- tests/test_u3c_store_false_pin.py
  same with --tag u3c-referral / tests/test_u3c_referral_push_name.py; --tag u3c-mce / tests/test_model_config_enforced.py;
  --tag u3c-refsvc / tests/test_referral_service.py.
Comm gate (72 files = grep of tests/ for guarded_llm_create|completions.create|api_budget_service|_llm_breaker|
referral_service|push_service|send_loop2_push|_load_invitee and source reads of the touched files; list in
NOTES/comm_files.txt, chunks comm_chunk_00..02, bound 1200 each). Measured at GREEN: chunk0 3 failed / 658 passed
(tests/test_camera_vision.py::TestIdentifyProductsMocked x3: pre-existing, tests/.pre_impl_failures.txt:81-83,
identical at base); chunk1 613 passed 2 skipped (netguard 156 attempts / 20 nodes, identical at base); chunk2 735
passed 1 skipped. Files: test_admin_referral_endpoints, test_api_budget_service, test_arabic_verdict_output_w414,
test_auth_routes_invite_fingerprint, test_brightdata_budget_gate, test_camera_vision, test_comparison_id_echo,
test_comparison_quality_v2, test_diagnostics_flag_gated, test_extraction_pros_cons_diagnostic, test_feedback_service,
test_fragrance_content_quality, test_guidance_insights, test_hotfix_shopping_query_clean,
test_image_identify_llm_unavailable_s69, test_image_service, test_image_service_edges, test_image_service_longtail,
test_landing_fallback_pages_s69, test_legal_routes, test_loop2_gift_copy, test_m13_28_referral_hardening,
test_m13_31_half_open_probe, test_m13_32_serper_breaker, test_m18_offload_sweep_residual, test_m18_openai_tpm_sizing,
test_model_config_enforced, test_model_router, test_openai_breaker, test_personalization,
test_price_pipeline_diagnostic, test_prompt_caching, test_push_service, test_referral_e2e, test_referral_expiry,
test_referral_full_response_column, test_referral_lifetime_cap, test_referral_loop2, test_referral_must_fixes,
test_referral_service, test_referral_service_internals, test_referral_share_privacy,
test_referral_share_status_lifetime, test_register_invite_linking, test_resolve_category, test_retro_w0_4,
test_retro_w0_4_efg, test_retro_w1_2d, test_retro_w1_3, test_review_prompt_quality, test_s70_exc_summary_logs,
test_s70_model_router_downgrade, test_security_regression, test_seed_zyte_guard, test_self_critique_orchestration,
test_serper_budget_gate, test_serper_gcc_fallback, test_serper_multikey_failover, test_serper_record_usage,
test_shadow_experiments, test_social_login_device_fingerprint, test_spec_spine_d2, test_specs_no_fabrication_guard,
test_subtype_spec_reconciliation, test_tier3_synth, test_tradeoffs_dedup_parity, test_verdict_critique_service,
test_verdict_prompt_unification, test_verdict_response_format, test_w49_extraction_catch_redaction,
test_warmer_preconditions, test_youtube_budget_metering (+ the two new files).
Mutants measured (NOTES/mutate.py, byte-copy restore, sha OK): store only in the flag-OFF branch -> killed by
T01, T05[on], T06[on], T09[on]; setdefault -> killed by T01, T06[off], T06[on]. Adversary should add: assignment
after the `if` (T05[off]); scripts edit dropped (T04); referral split restored (T11, T17); select reverted (T13).

## 5. Edge cases
- Caller store=True: overridden (R1, T06). Caller store=None: the SDK would SEND null; overridden too.
- extra_body carrying store: real bypass in the SDK (measured); closed statically (R2, T03).
- stream=True: carries store=False (T07; probe stream case). No app caller streams today.
- Breaker: the assignment precedes admission; a denied admission still raises without dispatch; outcome recording
  unchanged (T05[on] record_success x1; test_openai_breaker, test_retro_w1_3, test_m13_31 green at GREEN).
- model_config helpers unaffected (M2 test_gpt5_ids_emit_no_rejected_kwargs green); kwargs-equality pins:
  test_arabic_verdict_output_w414.py:625 compares on vs base (both carry store, green); test_model_config_enforced
  M3 updated (R6). All 12 fake `create` functions in tests/ accept **kwargs (grep), so no TypeError.
- Whitespace-only display name -> nameless (T11 name_blank). Display name containing "@" -> shown as typed (Q2).
- Under ZDR store is forced false anyway; this org is not ZDR (openai/data notes).

## 6. Diff plan (measured in scratch, `git diff --numstat`; Edit tool only; CRLF working copy, LF index:
a whole-file diff is a defect; check `git diff --numstat` after every edit)
- app/services/api_budget_service.py +6/-0 (docstring 5 + `kwargs["store"] = False`); file has non-ASCII em dashes
  in nearby comments: leave them.
- app/services/referral_service.py +5/-6 (select +display_name; :926-930 -> 3 comment lines + 1 expression).
- app/services/push_service.py +7/-3 (strip, two `lead` lines, two body lines). The Arabic line edit must keep every
  other byte: change only `{name}` + U+060C + space -> `{lead}` at :185; T16 checks the named prefix by code point.
- scripts/seed_spec_spine.py +1/-0; scripts/shadow_experiments.py +1/-0.
- tests/test_referral_service.py +2/-2; tests/test_model_config_enforced.py +2/-1; two new test files.
- Reference patch NOTES/u3c_green_scratch.patch (sha256 78d73a74...): read it, do not `git apply` it.
- Gates: py_compile + ruff --select E9,F63,F7,F82 on the 7 touched .py + 2 new; full-config ruff passed in scratch.
- Post-deploy check (owner or orchestrator, platform dashboard, read only): after one compare, Logs > Completions
  shows no new stored completion.

## 7. Documentation (orchestrator commits)
- CLAUDE.md:650 (the ENABLE_LLM_PREFLIGHT_BREAKER bullet) append: "U3c (unflagged): `guarded_llm_create` sets
  `kwargs["store"] = False` before either branch, overriding any caller value, so no chat completion is a stored
  completion; pinned by `tests/test_u3c_store_false_pin.py` (AST, runtime, pinned-SDK body)."
- CLAUDE.md:268 (referrals inline) append: "The Loop 2 referrer push shows the invitee's `display_name` or a
  nameless localised body, never any part of the email (U3c, `tests/test_u3c_referral_push_name.py`)."
- docs/privacy-data-inventory.md: no OpenAI storage statement exists (grep "openai": 0 hits); no U3c change. The
  OA2 "used to train AI models = YES" row belongs to LISTING-TRUTH/U8.

## 8. Assumptions and open questions
- A1 hard override beats setdefault: an unconditional promise needs an unconditional mechanism; CI (T03) catches
  intent, runtime never stores. A2 scripts are in scope: same organisation key, so their calls land in the same
  dashboard Logs; 2 lines. A3 backend/ out of scope: not deployed, "Do NOT edit". A4 nameless copy beats "A friend":
  no mixed-script Arabic push, no "A friend, your friend" English, and no new translation (R3 can flip it).
  A5 users.display_name exists in prod: inferred from migrations 014 (RPC resolve_referral_code reads it) and 043;
  NOT verified against the live DB (no DB access). A6 T09 uses httpx2.MockTransport from httpx2 2.12.0 (measured).
- Rulings for Fable before RED: R1 override vs honour vs refuse; R2 extra_body static vs runtime scrub; R3 nameless vs
  "A friend"; R4 load display_name; R5 scripts in scope; R6 the two existing-test edits.
- Q1 the brief named the rules file scratchpad/s74-common.txt; it is at scratchpad/harness/s74-common.txt.
- Q2 a display name containing "@" (a user typing an email as a name) is shown as typed; filter it to nameless?
  (+1 condition, +1 param in T11). Recommend no filter: the policy discloses the display name.
- Q3 onboarding "What we never share: Your name" (SmartCompareApp en.json:567-568, U8 review C1) stays false for
  users with a display name; U3b/U8 scope.
- Q4 policy section 4 "We do not send your name, email address or account identifiers": true today (no `user`,
  `safety_identifier` or `metadata` kwarg anywhere) but unpinned; extend T03 to forbid them? (+1 tuple entry).
- Unverified: "Enabled per call" semantics (no official definition); the dashboard staying empty is an owner
  reading after deploy; the other ~610 of 682 tests/test_*.py files were not run against the scratch GREEN (CI does).
