Follow-up of U8d (#311). U8d closed the Sentry channels that carry exception text or user content on the launch paths. These items were measured during its spec, review and adversary rounds and ruled out of that unit (rulings SR2, UF4, UF8 in `docs/investigations/2026-10-05-session-72-state/specs/`). None is launch-blocking.

## Scope

1. **#286** - `sentry_service` pattern set: nine credential shapes the patterns miss, and the quadratic JWT anchor (`_scrub_string`: 10,000 chars 0.03 s, 100,000 chars 2.9 s). After U8d, exception-derived text is replaced before the patterns run, so the exposure is long non-exception strings and the R2 forms below.
2. **R2 cost per hook call (adversary B5).** The handled-text forms are capped per exception (16,384 characters) but not per call: a chain of ten exceptions with 20,000-character JWT-shaped texts costs about 1.6 s in the hooks. Fixing item 1 removes the cause.
3. **#321 COM-7** - one `_scrub_text` shared by `safe_exc` and `exc_summary`.
4. **#293** - `cache_service.delete_cached` logs at ERROR on a Redis outage (five lines per account deletion). Privacy is closed by U8d (the text is replaced by the type name); this is alerting noise: WARNING, type only.
5. **#301, Railway half** - raw query and URL text at INFO in `text_routes` / `url_routes` no longer reaches Sentry (breadcrumb level is ERROR), but it is still in the Railway log: length and host instead.
6. **#226** - `str(e)` in the `error` fields of `extract_specs`, `extract_price`, `extract_price_from_training_data` (a database / client channel, not Sentry).
7. **#287** - the model-router Redis read on the event loop and its empty-message logs.
8. **Transformed exception text** - R2 matches whole `str` / `repr` / `safe_exc` / `exc_summary` forms of exceptions in the handled chain. `str(e)[:100]`, `e.args[0]`, `.message` or text logged outside the except arm at ERROR are not matched. Add an AST ratchet over ERROR lines that rejects those shapes.
9. **Request-id tag** - tag every event with the RequestID middleware's id so Sentry joins to the Railway log now that Sentry carries less text.
10. **Redis breadcrumbs (adversary A6)** - the `redis://` fallback client would put cache keys (user queries) into breadcrumbs and `db.redis` spans. Production uses the Upstash REST client, so this is unreachable today.
11. **Userinfo over-scrub (adversary A8)** - an outbound URL with userinfo becomes `[Filtered]` entirely (fails closed; costs triage only).
12. **Small test pins the final adversary left as minors:** the `re.DOTALL` flag of the prices-path rule (a product text with a decoded newline); the breadcrumb `data.path` rule's own fail-safe; a `DidNotEnable` raised in `OpenAIIntegration.setup_once` (no pinned SDK version has that path); a stale docstring line in `tests/test_auth_error_log_hygiene.py` (it says the amended node is green at base).
13. **Legacy branch** - `_scrub_query_string` for a string with `=` and no `?` keeps the old value pattern (unreachable for SDK `request.url`).

## Not in scope

Anything that changes a response body or a status code; the Google sign-in diagnostic in the social-login response (`auth_service.py`, owner's call with the conditional U-GOOGLE unit).
