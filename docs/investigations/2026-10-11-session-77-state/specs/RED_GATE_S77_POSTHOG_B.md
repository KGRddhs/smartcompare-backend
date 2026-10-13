# Orchestrator RED gate: unit S77 POSTHOG part B (2026-10-12 03:14)

## RED files
- `tests/test_s77_posthog_server.py` (sha256 488e75a6..., 118 nodes, ASCII).
- `tests/test_shutdown_drain.py` (sha256 91ad84ae..., +54 lines, CRLF kept, one new node).

Orchestrator re-run: `[pyt] tag=ph-redgate` 14 s, FAIL rc=1, 104 failed and 35 passed:
- 103 new nodes plus the new drain node fail;
- 15 pins plus the 20 base drain nodes pass.

No collection errors. A satisfiability prototype passed 139 of 139, and 24 mutants were killed.

**GATE: APPROVED.** The answers below bind GREEN and add to RULINGS_S77_POSTHOG.md (PH1-PH11).

## Answers to the RED questions
- **PG1 (Q1).** The flag readers use the repo default-OFF idiom `.strip().lower() in ("true","1","yes","on")`, as pinned.
- **PG2 (Q2, T7a/T7b).** Use the U8 machinery's own gate:
  - Add `ENABLE_POSTHOG_SERVER_CAPTURE` as an eighth fill-in flag.
    - Append it to the `SEVEN_FLAGS` tuple in both `scripts/fill_in_legal.py` and `tests/test_legal_docs_u8.py`.
    - Keep the tuple's name and add a one-line comment that it now holds eight.
    - Update every pin that counts exactly seven.
  - Record it `"off"` in `tests/fixtures/legal_fill_in_u8.json`.
  - Add a `processors.json` row:
    - id `posthog`, name_en `PostHog`, name_ar `PostHog`;
    - kind: one of the allowed kinds, measured; prefer an existing processor kind;
    - personal_data true, module `["app/services/product_analytics_service.py"]`, hosts `["posthog.com"]`, gate_flag `ENABLE_POSTHOG_SERVER_CAPTURE`.
  - With the gate "off", T7a does not require the policy to name PostHog, and T7b maps the module's hosts.
  - The real fill-in run must stay byte-identical on every legal file, and `render_legal_landing.py --check` must return rc 0.
  - Unit L later flips the value to "on" and adds the text in the same PR.
  - The activation precondition (stated in the flag row): the fill-in value is "on" and the PostHog text is live before `ENABLE_POSTHOG_SERVER_CAPTURE` is set on web.
- **PG3 (Q3).**
  - `preferences=` on the capture functions and `_reset_state_for_tests()` are accepted.
  - Thread the route's preferences through `track_after_persist` (new optional kwarg `preferences=None`) at the three direct call sites ONLY IF the route's object is the raw `users.preferences` JSON. Measure this.
  - If it is anything else (merged, cohort-seeded, or only set when `preferences_completed`), do not thread it; the capture reads through `asyncio.to_thread` plus the 300 s cache.
  - Report which case applied.
- **PG4 (d).** A failed preference read fails closed (no capture). Accepted, because it protects privacy.
- **PG5 (e).** Use the documented PostHog path for `persons/bulk_delete`, with or without the trailing slash as the PostHog API docs show it (WebFetch posthog.com docs, or context7). Cite the source.
- **PG6 (f).** The toggles route invalidates that user's preference-cache entry when `analytics_enabled` is in the body.
- **PG7 (g).** Add `POSTHOG_PROJECT_API_KEY` and `POSTHOG_PERSONAL_API_KEY` to the credential-bearing names `tests/_env_safety.py` neutralises. Pin it.
- **PG8 (h).** The user is marked deleted only with B2 ON, as pinned. PH4 already requires B2 ON before server capture.
- **PG9 (constraints).**
  - Keep the toggles response byte-identical for every body without `analytics_enabled`; `test_auth_preference_toggles_w314.py:157-161` stays green unmodified. When `analytics_enabled` is present, the response adds that key.
  - Docstrings follow `test_u3b_sharing_branch_removed.py` B5: no "opt-out" or "PDPL"; say "analytics preference".
- **PG10 (error_class).** The mapping keyed on the real user-facing sentences is accepted, with timeout / content_unavailable / insufficient_data / other.
  - It must be total, with unknown mapping to `other`.
  - It must never emit the raw message: `error_message` is never a property.
- **PG11 (b7).** GREEN measures the capture cost on the event loop with the real 7.60.1 client in `sync_mode=False`, using a non-sending stub transport (monkeypatch only). It reports p50/p99 over 1000 captures; the target is p99 < 2 ms.
- **PG12.** Write the CLAUDE.md flag rows into the Environment Variables section (PH11) for `ENABLE_POSTHOG_SERVER_CAPTURE`, `ENABLE_POSTHOG_PERSON_DELETE` and their knobs. Each row has effect ON, flag OFF, preconditions (PH4, PG2, PR4), canary and rollback. Edit in place with no appended corrections.
