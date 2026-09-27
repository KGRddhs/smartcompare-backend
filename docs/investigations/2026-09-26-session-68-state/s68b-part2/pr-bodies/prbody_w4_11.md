## W4-11: prompt truth (fence the last unfenced LLM inputs, stop the verdict prompt contradicting itself, route every call through model_config)

Findings: PO-PROMPTS-11 (status pin), PO-PROMPTS-01 + CR-SECURITY-08 (the `extract_specs_targeted` fence), PO-PROMPTS-02 (**re-rated P1**, ruling R8: Serper's shopping `source` reaches the gpt-4o verdict payload verbatim through `price.retailer`, with no LLM in between; measured with `ENABLE_EXACT_PRICE_GATE` both false and true), PO-PROMPTS-05 / -06 / -10 (verdict wording), PO-PROMPTS-13 (the price fallback may decline), PO-PROMPTS-03 (model_config bypassed).

Spec: `.qa-s68/specs/W4_11_UNIT_SPEC.md`. The binding rulings come in three sets:
- R1-R15, spec level: `.qa-s68/specs/W4_11_FABLE_RULINGS.md`.
- R16-R24, red gate: `.qa-s68/RULINGS_W4_11.md`.
- R25-R27, polish: `.qa-s68/RULINGS_W4_11_R25_R27.md`.

### Defects
1. **The refill prompts had no fence.** `openai_service.extract_specs_targeted` put raw Serper snippets in the user message with no `<SEARCH_RESULTS>` region or guard. It also put the raw product name into the SYSTEM message. A snippet or name carrying `</SEARCH_RESULTS>` / `</USER_INPUT>` plus a new line reached the model as instructions. `extract_specs_synthesized` did the same with the name.
2. **The verdict payload could close its own region.** `json.dumps` does not escape `<`, `/` or `>`. A review consensus or a shopping retailer string carrying `</USER_INPUT>` produced 1 open and 2 closes, and the attack text landed outside the region. The same applied to:
   - `concern` and `region`;
   - the two appended review-quote / YouTube blocks;
   - the URL-extraction page;
   - the image Tier-3 organic block.
3. **The verdict prompt contradicted itself.**
   - PO-06: `UNIVERSAL_TRUST_RULES` said "If scores disagree with your intuition, explain why (do not silently ignore scores)" and "<5 point gap", next to "NEVER mention internal scores". This appeared on 10/10 renders.
   - PO-05: "NEVER return empty pros[] or cons[]" plus a "2-4 cons" quota forced invented cons, i.e. cons about missing data such as "limited information on X".
   - PO-10: only 1 of 9 `reasoning_style` lines depended on the data actually supplied.
4. **The price fallback could not decline (PO-13).** "NEVER return null for amount -- always provide an estimate" was sent at temperature 0.2 with no JSON mode, and the dict was returned unvalidated. A NaN amount is truthy, so it was saved as an estimate.
5. **model_config was bypassed (PO-03).** Of 15 LLM call sites, 12 passed a literal `temperature=` and 6 a literal `max_tokens=`, so a GPT-5 id got kwargs it rejects. `image_service.py` made a direct `client.chat.completions.create` call outside the W1-3 breaker.

### Design
**Unflagged security controls (R4, R13, R20). Byte-identical unless a literal region tag is present.**
- The verdict product dumps (product 1 AND product 2), `concern` and `region` pass through `neutralize_prompt_tags`. It is applied to the dumped strings, never to the assembled `user_msg`.
- The appended review-quote strings (`domain`, `text`) and YouTube strings (`top_channel`, `top_video_title`) pass through `sanitize_untrusted_block`.
- `extract_specs_targeted`:
  - `SEARCH_RESULTS_GUARD` is prepended to the system message.
  - The snippets are wrapped in one `<SEARCH_RESULTS>` region (`_wrap_search_context`).
  - The brand, name and variant go through `sanitize_prompt_input` and whitespace collapse (`_sanitized_full_name`).
  - Every D1 substring is kept, including the training-fallback line.
- `extract_specs_synthesized`: the sanitised name only. It has no snippets, so no region.
- **Name coercion (R25).** `_sanitized_full_name` coerces each part BEFORE sanitising: None -> `''` (R3), any other non-string scalar -> `str(value)`, list/tuple -> the `str()` of its items joined by one space. So the unflagged name fence can never raise. Before this rule, an int, float or list brand (from LLM JSON) threw `TypeError` ahead of the function's `try:` and aborted the refill with 0 OpenAI calls. At base the f-string rendered those values and the refill ran. String inputs render exactly as before (digest keys unchanged).
- `url_extraction_service.extract_with_ai`: the guard sentence, plus ONE region holding the fetched page title and text through a `{page_block}` slot. The user-supplied URL stays OUTSIDE the region and passes through `neutralize_prompt_tags` (R20).
- `image_service.extract_image_via_gpt`: the guard sentence, plus the organic link/snippet block in one region.
- **Exactly four digest keys move** with the flags off: `targeted_system`, `targeted_user`, `url_extract_user`, `image_tier3_user`. Every other render is equal: 90 verdict renders, 18 specs renders, 10 personality blocks, the constants, the benign verdict user/system messages and the price fallback. Every kwargs dict is equal too.
- `brand=None` now renders `''` instead of the literal `None` in the two refill prompts. That is an improvement, but it is not byte-identical on that input (R3). The same holds for R25's list inputs (`['Apple']` renders `Apple`, not `['Apple']`).

**Unflagged routing (R7, R24).** All 12 raw sites now go through `sampling_kwargs` / `token_limit_kwargs` with today's values. This removed 12 literal temperatures and 6 literal max_tokens. The kwargs are byte-identical on every model id that resolves today; M3 pins all 12.

| site | model | kwargs |
|---|---|---|
| extraction_service.classify_category_llm | standard | temperature 0.0, max_tokens 10 |
| extraction_service.parse_product_query | standard | 0.1 / 500 |
| extraction_service.extract_specs | standard | 0.1 / 1000 |
| extraction_service.extract_price | standard | 0.1 / 300 |
| extraction_service.extract_price_from_training_data | standard | 0.2 / 200 (0 + json_object under MAY_DECLINE) |
| extraction_service.extract_reviews | standard | 0.2 / 600 |
| image_service.extract_image_via_gpt | standard | 0.1 / 120, now through `guarded_llm_create` (R7; with the breaker flag OFF it is a bare create) |
| openai_service.extract_specs_targeted | standard | 0.1 / 200 json_object |
| openai_service.extract_specs_synthesized | model or verdict | 0.1 / 300 |
| openai_service.disambiguate_variant_line | standard | 0 / 60 |
| url_extraction_service.extract_with_ai | standard | 0.1 / 800 |
| verdict_critique_service.critique_verdict | critic | 0.0 / 150 json_object |

The three sites that already complied (the verdict, its fallback, and vision) are unchanged. The AST pin (M1):
- matches both `completions.create` and `guarded_llm_create`;
- excludes the wrapper's two `**kwargs` pass-throughs (`api_budget_service.py:967`, `:974`);
- asserts at least 15 sites, so a matcher that stops matching cannot pass vacuously.

### Flags (both default OFF, read PER CALL as `os.getenv(...).strip().lower() in ("true","1","yes","on")`)
| flag | default | effect ON | OFF identity | knobs |
|---|---|---|---|---|
| `ENABLE_VERDICT_PROMPT_TRUTH` (`prompt_personalities.verdict_prompt_truth_enabled`) | OFF | See below. | All 90 fixture renders plus 10 personality blocks byte-identical (T-D4, T-G1). | none |
| `ENABLE_PRICE_FALLBACK_MAY_DECLINE` (`extraction_service.price_fallback_may_decline_enabled`) | OFF | See below. | `PRICE_FALLBACK_SYSTEM`, temperature 0.2, no response_format, raw dict (P4; fixture digests and kwargs). | none |

**With `ENABLE_VERDICT_PROMPT_TRUTH` ON:**
- `COMPARISON_SYSTEM_TRUTH` replaces the cons rule with "NEVER return an empty pros[] array ... an honest empty cons[] is correct ... a con about MISSING DATA is NEVER acceptable". It changes "2-4 cons" to "up to 4 cons" (R10).
- `UNIVERSAL_TRUST_RULES_TRUTH` describes closeness in plain words, never as a number. The replacement for rule 77 is the R17 wording: "The winner is set by the supplied scoring context; justify it with the product facts that support it, and never mention, quote or allude to the scores themselves".
- All 9 `reasoning_style` lines now depend on the data supplied. An unknown category falls back to the TRUTH 'other' entry (pinned, T-D3b).
- `build_verdict_prompt` reads the flag ONCE and passes `truth=`, so a single verdict never mixes states.
- Every TRUTH object is DERIVED from the untouched OFF object by swaps that must match exactly once and raise `RuntimeError` at IMPORT on zero OR duplicate matches (R11/R19; the duplicate case is pinned, T-D9b). `prompt_personalities` is imported at the top level of `extraction_service`, outside any try (R19).
- The prompt is static per category, so it can still be cached, with one extra cache entry per category.

**With `ENABLE_PRICE_FALLBACK_MAY_DECLINE` ON:**
- `PRICE_FALLBACK_SYSTEM_MAY_DECLINE` lets the model return a null amount, with confidence between 0.0 and 0.5.
- Temperature 0 and `response_format=json_object`.
- The amount is coerced (C6): bool -> None; int/float/str -> `float()`, kept only if finite and > 0. A JSON integer too large for a float (`OverflowError`) is also declined.
- Every decline logs ONE INFO line (R21).

### Canaries
- `[VERDICT_TRUTH] cons empty=N data_gap=N`: INFO, only under the TRUTH flag, once per verdict (R18).
  - "empty" counts falsy cons values: a missing key, `[]`, JSON null or `""`.
  - "data_gap" is counted **per cons string** (R18/R27a): each string containing "limited information", "no details on" or "no cons noted" (case-insensitive) adds 1, so two such strings on one side count 2.
  - A single bare string is counted as a one-item list. Non-string items are skipped, and the verdict survives them.
- `[PRICE_FALLBACK] declined (amount null) for <brand> <name>`: INFO, only under MAY_DECLINE (R21).
  - It fires for every decline: a model null AND every value coerced to None, including NaN, Infinity, <= 0, non-numeric strings, bool and int overflow.
  - It carries only the sanitised brand and name, with whitespace collapsed. A newline or a closing region tag in the user's own brand/name can neither split the line nor forge a second canary line (pinned, P7).
- Step 0 (the unflagged part): watch `[EXTRACT_TARGETED] Failed`, `[EXTRACT_SYNTH] Failed` (not `[TIER3_SYNTH] error`; R2) and `WINNER_INDEX_MISMATCH`.

### Activation notes
- **MAY_DECLINE:** a declined estimate plants NO 30-day `nogenuine:` negcache, so the full discovery cascade re-runs on every later request for that key. Watch Serper/Firecrawl spend per compare together with the decline line and the pending-price rate.
- **TRUTH:**
  - Activate by a smoke20 A/B against the step-0 run. The two arms share code, not a process: a Railway variable change rebuilds `web`, and in-process caches reset.
  - Then run N=20 `nocache=true` compares on the manual rubric. Empty `pros` must stay 0 (the Bundle C hot-fix guard, pinned in both states by T-D6).
  - With `ENABLE_SELF_CRITIQUE` ON, the critic's "balanced" axis may regenerate an honest empty-cons verdict.
  - Whether a product may ship with ZERO cons is Ahmed's product call; the flip needs his explicit yes.
- `ENABLE_SPECS_NO_FABRICATION` stays LAST (after Serper is restored and after TRUTH).
- **T-S1** is `xfail(strict=True)` by design (R6). The marker comes off in the change that makes the evidence-only specs prefix the CODE default, which is the planned retirement of `ENABLE_SPECS_NO_FABRICATION` after the Railway flip is proven. The xfail is not meant to be permanent.

### Existing tests edited (by id, the K1 pattern; R16 as amended by R26)
There are exactly two amended existing pins; no other existing test changes.
- `tests/test_retro_w0_4_efg.py::test_w04g_extract_with_ai_prompt_identical_on_vs_off_past_the_4000_char_truncation`: one line (R16).
  - It applies `removesuffix("\n</SEARCH_RESULTS>")` to the content slot, so the 4,000-char OFF==ON assertion stays exact.
  - Dropping the url fence reddens F11 while this pin stays meaningful.
  - Reverting the amendment reddens this pin.
- `tests/test_wall_caps_i57.py::test_reviews_trim_context_and_tokens`: **RATIFIED by R26** as the second amended pin.
  - The ruled unflagged routing forces it (R7/R24): the literal `max_tokens=600` no longer exists in `extract_reviews`, which now routes through `token_limit_kwargs(_model, 600)`.
  - Its two source assertions were replaced by the routed form: the routed 600 is present, and the stale 1000 is absent in BOTH spellings.
  - It is not vacuous. On the final bytes, three planted mutants each redden it: reviews routed at 1000, the amendment reverted, and a routed-1000 form.
- `tests/test_prompt_fence.py`: extended (F1-F13, plus F4b for R25).

### Gates (measured on the final bytes, fixer round 3, 2026-09-27)
- **Unit files** (fence / truth / model_config_enforced / price_fallback_may_decline): **129 passed, 1 xfailed** in each of 4 states (unset / TRUTH / MAY_DECLINE / both), `[netguard] blocked 0`, 6 s each.
- **Mutation:**
  - The R25 mutants: coercion removed -> the int/float/list rows red (6); list join removed -> the list rows red; `None -> ''` removed -> the None rows red.
  - The surviving adversary mutants re-run verbatim now each redden their pin: N1 (product-2 dump raw), N2 (url title outside the region), N3 (unknown category -> OFF 'other'), N4 / N4b (raw or uncollapsed names in the decline line), N17 (`_truth_swap` accepting a duplicated anchor), X1 (data_gap per side instead of per string).
  - The full 63-row table was re-run on the final bytes: 63/63 as expected (M-A6 neutral, as the spec predicts). Four anchors were re-anchored onto the coerced f-string with identical semantics.
  - Every restore was sha-verified.
- **Digest gate** at HEAD with flags unset:
  - Exactly the four fence keys moved, and every kwargs dict is equal.
  - The HEAD dump is byte-identical to the previous round's, so R25 moved no string render.
  - T-G1 is green in all four states.
  - base2 (a detached worktree at 58a86b3c) equals the fixture.
- **CI-order set**, 38 files in ONE process per state: **1004 passed, 1 skipped, 4 deselected, 1 xfailed, 0 failed** in all 4 states (86 s each). The netguard ratchet printed `OK: 31 attempting node(s), baseline 205` in every state; the unit files blocked 0.
- **Comm gate:** the 143-file set (the spec's 138 files plus 2 new on main plus 3 of this unit's files) ran at HEAD on the round-2 app bytes, in 6 chunks of at most 25 files: **3,762 passed, 0 failed**, base-failed set EMPTY. Not re-run this round, per R27: the only app change since is the `openai_service` coercion (see the CI-order set, which contains every refill-path pin file).
  - **Stale note (R22):** `.qa-s68/specs/W4_11_comm_base_failed.txt` (3 SSRF nodes) is stale; those nodes pass at HEAD under the conftest guard.
- **Lint and diff:** ruff E9,F63,F7,F82 and py_compile are clean. `git diff --stat -- app/` touches only extraction_service, prompt_personalities, openai_service, url_extraction_service, image_service and verdict_critique_service, with no whole-file diff.
- The `_proof` corpus harness cannot see prompt renders. It was not run and says nothing about this unit.

### Stated limits
- No live LLM (OpenAI and Serper are unfunded). What the TRUTH wording does to model output is modelled; what the code sends is measured byte for byte.
- Option (a): the non-tag text of a product name still reaches the SYSTEM role of the two refill prompts, on one sanitised line. Only the requester can target themselves this way.
- Product display names still reach the verdict SYSTEM message raw through `build_scores_summary` (scoring_service is out of scope).
- The routing proves the kwargs, not that a GPT-5 id then yields usable output (reasoning tokens, determinism).
- `scripts/` call sites are out of M1's scope.
- The review's 113-cons incidence is not on disk and was not re-measured.
- The rendered verdict prompt is frozen in the fixture. Any deliberate prompt edit must regenerate it with `python -m tests.w4_11_prompt_digest_recorder` in the same PR, with the diff explained (R13). W4-14's locale line will need this.
- The `[VERDICT_TRUTH]` counter sits inside `generate_comparison`'s try. Its non-string and falsy guards are pinned, but it is not isolated in its own try (flag ON only).

### Follow-ups
- **PO-PROMPTS-02b:** display names reaching the SYSTEM message through `build_scores_summary` (scoring_service), plus moving the appended quote/YouTube blocks and the self-critique payload inside a region.
- **PO-PROMPTS-05b:** the data-gap cons scrubber half (`text_sanitize` plus a `response_builder` filter). It is deferred because no cons corpus is on disk to measure over-rejection.
- **W4-9 follow-up 05c:** the `str(e)` still at `extract_specs`, `extract_price` and `extract_price_from_training_data`.

### Order
W4-11 lands BEFORE W4-14 (both touch the verdict prompt). W4-8 also edits `extraction_service.py`, in different functions: whichever lands second rebases and re-runs its unit files.

### CLAUDE.md corrections for the docs PR
- Add the two flag rows above.
- Correct the "prompt trust boundary ... Known residual" sentence: `extract_specs_targeted` is now fenced, and so are the url and image prompts.
- Note that all 15 LLM sites route through model_config, and that `image_service` now goes through the W1-3 breaker.

### Orchestrator addendum (Fable, ship time 2026-09-27)
- **Pipeline:** red (52 reds / 25 pins / 40 kills at `58a86b3c`) -> Fable red-gate rulings R16-R24 -> green -> adversary r0 SOUND (8 minors) -> fix r1 -> adversary r1 SOUND (2 minors) -> fix r2 -> adversary r2 SOUND (1 minor: the unflagged name fence raised on non-string parts) -> Fable polish rulings R25-R27 -> fix r3 -> adversary r3 SOUND (2 pin gaps). Every adversary left the worktree byte-identical to the fixer's reported shas.
- **Two pin gaps from adversary r3 closed by the orchestrator (test rows only, no app change):** `tests/test_prompt_fence.py::test_name_fence_coerces_non_string_parts` gained the `name_int`, `variant_int` and `brand_list_two` rows and a new `test_name_fence_sanitises_a_coerced_list_brand` (a hostile list brand is coerced, then sanitised); `tests/test_prompt_truth.py::test_truth_cons_counter_vocabulary_per_phrase` gained `two_phrases_one_string` (two phrases in ONE cons string count once). On the final bytes the adversary's five surviving mutants now redden: E1 (name-slot coercion dropped) 2 failed, E2 (variant slot) 2 failed, E3 (per-match count) 1 failed, E4 (list joined without a space) 4 failed, E5 (list brand not sanitised) 2 failed; every restore sha-verified. Unit files: 138 passed, 1 xfailed in each of the four states, `[netguard] blocked 0`.
- **Formatting at commit time:** the repo's pre-commit black allowlist covers `app/services/prompt_personalities.py`, so it was black-formatted before the commit (26 insertions / 9 deletions, line wraps and one quote style, no string content changed; sha `d394ba84` -> `6c336ae6`); the unit files were re-run on the formatted bytes (138 passed, 1 xfailed).
- **Post-rebase ship checks** (onto main `d66444f2`; the rebase touched none of this unit's files): the four unit files and the 38-file CI-order set in ONE process per state (unset / TRUTH / MAY_DECLINE / both), the netguard ratchet, the T-G1 digest gate, ruff E9,F63,F7,F82 and py_compile - results in the PR's first comment if they differ from the fixer's numbers above.
- **Flags on main after this merge (default OFF, read per call):** `ENABLE_VERDICT_PROMPT_TRUTH`, `ENABLE_PRICE_FALLBACK_MAY_DECLINE`. Nothing is flipped; Railway and Supabase untouched. The TRUTH flip needs Ahmed's explicit yes on zero-cons verdicts (see Activation notes).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
