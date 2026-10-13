# Orchestrator rulings: unit S77 POSTHOG (spec 17c53315..., review 984e68a3... APPROVE_WITH_RULINGS)

Orchestrator: Opus 5.5, 2026-10-12. These rulings are BINDING and supersede the spec where they differ. main = 18121839 (PR #351 legal disclosure merged and live).

## Adopted verbatim
PR1-PR19 of POSTHOG_SPEC_REVIEW.md are adopted verbatim, with the amendments below.

## Owner decisions taken with the recommended defaults (the owner may override before activation)
- **PH1 (O-1).** PostHog EU Cloud. Ingestion host `https://eu.i.posthog.com`; private API host `https://eu.posthog.com`. Policy s7 names the EU (Germany) for PostHog.
- **PH2 (O-3).** The in-app switch is built: "Share usage analytics", default ON, stored per spec 2.6. PR16 applies (`analytics_enabled` alone is a valid preference-toggles body).
- **PH3 (O-4).** Policy s8 states PostHog keeps analytics events "for up to 1 year". Activation precondition: the project is on the free plan, or the text changes first.
- **PH4 (O-5).** B2 automated person deletion is built.
  - It sits behind `ENABLE_POSTHOG_PERSON_DELETE` (default OFF, read per call), with `POSTHOG_PERSONAL_API_KEY` (person:write only), `POSTHOG_PROJECT_ID` and `POSTHOG_API_HOST` (default `https://eu.posthog.com`).
  - The PR2 ordering and wording apply.
  - Activation precondition: B2 is ON before `ENABLE_POSTHOG_SERVER_CAPTURE`, and before the client OTA.
- **PH5 (O-6).** The effective date is decided when unit L merges:
  - **L merges before the app is released:** keep 2026-10-11 (the RL1 rationale and note).
  - **L merges after release:** bump all twelve anchors (RL1's first-post-release rule), including `consent.ts` TERMS_VERSION, which then rides the OTA.
  - The L spec carries both variants. The orchestrator picks one at L time.
- **PH6 (PR8a).** Disclose. The text a user types or the link they paste (shortened) is sent to PostHog with the comparison record; the owner explicitly asked to see comparisons and responses. Do not drop `query`.
- **PH7 (O-8).** Session replay is out of scope. It needs a new binary.

## Units and order (PR7)
- **B — backend.**
  - Branch `feature/s77-posthog-server`, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s77-posthog`. That worktree's branch `feature/s77-posthog` is renamed by the orchestrator.
  - Pin `posthog==7.60.1`. It is the newest release at least 14 days old (2026-09-25); the PR15 rule is applied to the backend too.
  - Measured on the installed 7.60.1: `Posthog.flush(self, timeout_seconds=10)` exists; the constructor accepts `disable_geoip`, `sync_mode`, `before_send`, `enable_exception_autocapture` and `on_error`.
  - The orchestrator installed 7.60.1 into the shared venv before RED.
- **A — client.** Its own worktree with its own real node_modules (PR15; no junction), after B merges.
- **L — legal.** After A merges.
- One workflow at a time: the weekly budget is at 85 %.

## B amendments
- **PH8.** The server client is constructed with all of these:
  - `disable_geoip=True`;
  - `enable_exception_autocapture=False`, passed explicitly;
  - `sync_mode=False`;
  - `on_error` logging by type only (PR14);
  - a `before_send` that drops any `$ip` property;
  - properties that never carry the email, name or display name.
  - `distinct_id` is the Supabase user id string.
- **PH9.** Event names and properties are exactly the spec's (4.3), with these amendments:
  - `query` is truncated to 200 characters;
  - a URL query or link is reduced to scheme + host + path (no query or fragment);
  - the product names and winner name are capped at 120 characters each.
- **PH10.** No capture for anonymous callers. No `user_id` means no event.
- **PH11.** The flag row for CLAUDE.md is written at GREEN.
  - It states that every new env name is read per call except the client construction knobs, which apply at the first construction and need a restart (PR19).

## Gates for B
- RED fails for the right reason: every new node fails because the module or hook is absent, or it is a pin that passes at base. No collection errors.
- Comm set at base and head with `branch-only-NEW` empty:
  - the module-reference set for `feedback_service`, `database_service`, `main`, `auth_routes` and `text_routes`;
  - unioned with the source-scanning pins: `tests/test_model_config*.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command*.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, the W1-6 drain pins (`grep -l drainingSeconds tests/`), and `test_events_allowlist_superset.py`.
- Flag-OFF byte-identity: with every new flag unset, `track_after_persist`, `log_search` and the deletion route make no new call and construct no client (pinned).
- `uv pip compile` for both locks. CI's lock-is-current step must pass.
