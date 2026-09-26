# FABLE REVIEW RULINGS W4-11 (binding, 2026-09-26, session 68) - these OVERRIDE the spec body and the adversarial review where they differ

Verdict: APPROVED WITH THE CORRECTIONS BELOW. Base 61585c58 (re-anchor by symbol). Order: W4-11 lands BEFORE W4-14 (both touch the verdict prompt); W4-8 and W4-11 both edit extraction_service.py in different functions - rebase whichever lands second and re-run its unit files before its last adversary.

R1 (flag for PO-05/-06/-10) - YES: ENABLE_VERDICT_PROMPT_TRUTH, default OFF, exactly as the spec proposes; the review row's "unflagged" is overruled (prose changes on every compare; reverses a pinned Bundle C hot-fix; needs a same-deploy A/B and a deploy-free rollback).

R2 (PO-13) - stays in this unit under ENABLE_PRICE_FALLBACK_MAY_DECLINE with correction C6: amount coercion = bool -> None; int/float/str -> float(), kept only if finite and > 0; P3 gains NaN, Infinity, -5, 0, "0". The no-negcache spend consequence of a declined estimate is stated as the flag's activation note.

R3 (name in the refill prompts) - option (a): sanitized, whitespace-collapsed, in the system sentence (keeps the D1 byte pin). `brand=None` renders '' instead of the literal 'None' - stated (an improvement, not byte-identical on that input).

R4 (COMPARISON_SYSTEM guard sentence) - omitted, as the spec says; neutralize on the dumped product payload closes the hole byte-identically. Extend fix B to `concern` and `region` (the same `neutralize_prompt_tags` on both strings before interpolation - byte-identical unless a literal tag is present; pin one hostile concern and a `</USER_INPUT>` region); product display names reaching the SYSTEM message via `build_scores_summary` are OUT (scoring_service, W4-6a's file) - record as follow-up PO-PROMPTS-02b.

R5 (PO-05 data-gap scrubber half) - deferred to PO-PROMPTS-05b, as the spec says; pr_text says why (no cons corpus on disk to measure over-rejection).

R6 (T-S1 end state) - the `xfail(strict=True)` pin comes off when ENABLE_SPECS_NO_FABRICATION becomes the CODE default, which is the planned end state after the Railway flip is proven (retire the flag = default ON). The 'x' is not permanent; say so in the test's reason string.

R7 (image_service.py:173) - fold the switch to `guarded_llm_create` into this unit (byte-identical with the breaker flag OFF); it is one of the 12 routed sites anyway, and M2/M3 cover all 12 (C7).

R8 (PO-PROMPTS-02 severity) - re-rate to P1 in pr_text (the one-hop Serper carrier through `price.retailer` is measured in both exact-gate states); fix B is what closes it.

R9 (C1, the TRUTH :77 contradiction) - REWRITE :77 so that scores FIX the winner, facts JUSTIFY it, and scores are never output text; T-D1 renders through `generate_comparison` with a real `build_scores_summary` block and asserts both the new sentence and the scores block's consistency sentence coexist without contradiction.

R10 (C2) - the '2-4 cons' quota becomes 'up to 4 cons' via a count-checked swap; T-D2 asserts '2-4 cons' absent; mutation M-D6.

R11 (C3, loudness) - the TRUTH constants are derived with an explicit count check that raises RuntimeError at IMPORT of extraction_service (a bad prompt edit must fail the deploy, never silently drop the personality block); plus a pin that imports prompt_personalities directly and diffs each TRUTH object against its OFF twin. `import os` in prompt_personalities (C4). The reader is called through the module attribute in both places (C5) so T-D7's patch reaches build_verdict_prompt.

R12 (the rest of the corrections, ADOPTED) - C8 hostile string parametrized over brand, name and variant; C9 F9 + M-B3 for the appended quote / YouTube blocks (or drop that edit - keep it); C10 one INFO counter under the TRUTH flag for empty or data-gap cons (`[VERDICT_TRUTH] cons empty=%d data_gap=%d`), the manual rubric named as the other instrument; C11 gate 4's expected-red set is EMPTY and every OFF pin `delenv`s the flags; C12 the session command is 120 s, CI's is 60 s; C13 the two excluded wrapper pass-throughs named.

R13 (missing items) - the two unfenced third-party prompts are FOLDED IN (same class, both files in the touch list): `extract_with_ai` (URL_EXTRACTION_PROMPT: page title + text through `sanitize_untrusted_block` inside a `<SEARCH_RESULTS>`-style region with the guard sentence) and `extract_image_via_gpt` (_TIER3_PROMPT: link + snippet likewise) - unflagged security controls, pinned with a hostile page/snippet; fixture ownership: the committed generator regenerates the 90-render fixture, and ANY deliberate prompt edit regenerates it in the same PR with the diff explained (W4-14's locale line will); new tests import extraction_service at module top (the lazy-import `.env` side effect); the ENABLE_SELF_CRITIQUE interaction goes in the TRUTH activation notes; the A/B sentence says the two arms share code, not a process.

R14 (gates) - the render-digest fixture (recorded twice, identical) is the byte-identity gate: head with all flags unset equals it on every key except `targeted_system` / `targeted_user` (+ the two new fences of R13 - list their keys) and `resolved_models()` equal; base2 via a detached scratch worktree; the 138-file comm set (+ the 4 new files) base vs head, `comm -13` empty against the baseline + the 3 guard-caused SSRF nodes; the CI-order pin set in one invocation per flag state; ruff + py_compile.

R15 (files) - app/services/extraction_service.py, app/services/openai_service.py, app/services/prompt_personalities.py, app/services/image_service.py, app/services/url_extraction_service.py (the fence only - its W0-4f offload hunk belongs to the unit in flight; rebase after it merges), app/services/verdict_critique_service.py (kwargs routing only); tests + the fixture + generator. Must-not-touch stands: prompt_sanitizer, model_config, structured_comparison_service, response_builder, text_sanitize, price_service, client, migrations.
