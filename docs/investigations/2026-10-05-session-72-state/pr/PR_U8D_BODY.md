## U8d: Sentry no longer receives exception text or user content (closes #311)

Sentry is a processor. Before this change, exception text, request bodies, query strings, request headers, outbound URLs and INFO / WARNING log lines reached it from several channels. This unit makes the following sentence true for the launch paths (it goes into the privacy policy, unit U8):

> Sentry receives exception types, scrubbed message templates (which may include internal account and comparison identifiers), scrubbed request metadata (method, path, user agent) and the website host name of a product link you submit - not raw exception text, request bodies, credentials, or the content of your searches.

**Unflagged** (the W1-1 precedent): it changes only what leaves the process for Sentry. No route, status code or response body changes.

### What changes (`app/services/sentry_service.py`, one central policy)

| Rule | Before | After |
|---|---|---|
| R1 exception values | the raw exception text | blank, except an `HTTPException` (its value is our own literal detail) |
| R2 handled-exception text in log templates and breadcrumbs | `Cache delete error: Error 111 connecting to ...` | `Cache delete error: <ConnectionError>` (plain string replacement over the handled chain, before any pattern pass) |
| R3 request body | attached to events and transactions | never read (`max_request_body_size="never"`) plus a belt |
| R4' query strings | `[^&#]*` value pattern: a decoded `&` or `#` in a search ("Dolce & Gabbana") leaked the tail | rebuilt part by part: user-content keys redacted, bookkeeping keys kept only on their grammar, everything else dropped |
| R5 outbound HTTP spans and breadcrumbs | full URL with query (provider tokens, database filters, the user's pasted link) | scheme + host; the path stays only for our infrastructure hosts; query values `[Filtered]` |
| R6 paths | share / invite tokens and the product text of `/text/prices/{product}` | `[token]` / `[product]` in `request.url`, `extra.path` and breadcrumb `data.path` |
| R7 breadcrumbs | INFO and WARNING log lines (queries, product names, URLs) | ERROR lines only |
| R10 request headers | device fingerprint and client-IP headers verbatim | allowlist (`host`, `user-agent`, `accept*`, `content-*`, `connection`, `x-request-id`); the rest `[Filtered]` |
| R12 trace headers | `baggage` + `sentry-trace` sent to every outbound host, including a user-supplied one | off (`trace_propagation_targets=[]`) |
| OpenAI integration | prompts gated only by `send_default_pii` | `include_prompts=False` pinned, inside its own guard |

Every new rule runs through a fail-safe: an error inside it falls back to the previous scrub and never drops the event.

Also: `log_scrub.exc_summary` scrubs at most 16,384 characters (the key patterns are quadratic on long text; #321 PER-6). Seven ERROR log lines that put user content or raw exception text into an event are rewritten at the site (`structured_comparison_service.py` x5, `url_extraction_service.py`, `image_routes.py`): the query's length only (no text, no fingerprint), the link's host and the exception type only, type names for gathered exceptions.

### Consequences to know

- **Sentry regroups once**: the seven rewritten templates open new issues; f-string error sites collapse from one issue per exception text to one per site. Mark the old issues resolved after the deploy.
- **Triage**: Sentry loses exception messages, request bodies and the INFO / WARNING breadcrumb trail. The Railway log keeps them (except the seven lines above).
- Two existing pins were amended by ruling, each keeping its purpose: the U8c positive control now rides the event `extra` (R1 blanks exception values), and the #198 pin allows exactly one explicit `LoggingIntegration(` (ERROR / ERROR) instead of none.

### Verification

- Tests first: 121 RED / 110 PIN nodes written and gated before any code (orchestrator re-run at base: 121 failed, 131 passed, netguard 0).
- `tests/test_sentry_channels_u8d.py` (child process: the real app, the real `init_sentry()`, an in-memory transport, a socket guard with an empty attempt list) and `tests/test_sentry_channels_u8d_unit.py`: **272 passed**; the child file green five times in a row.
- Kill set (14 files): **681 passed**, netguard 0 (orchestrator run on the final bytes).
- Module-reference regression set (207 test files, base `845ece15` vs head, chunks of 25): the FAILED sets are equal (the five known baseline nodes); nothing new.
- Mutation: 26 GREEN mutants, 39 + 15 adversary mutants; every survivor got a node that kills it.
- Three adversaries: privacy (coverage-driven, through the real app), engineering (39 own mutants, found three unpinned behaviours, all fixed test-first), and a final one on the exact bytes written after the first two.
- Measured on the pinned `sentry-sdk` 2.68.1: integration list unchanged (14 names), breadcrumb and event level ERROR, no `baggage` / `sentry-trace` on outbound requests.

### Stated limits

- OpenAI spans ship as separate envelope items that bypass the hooks: model name and integer token counts only (prompts are off twice over).
- The paths of unmatched routes (internet scanners) are kept verbatim.
- The `redis://` fallback client would put cache keys into breadcrumbs; production uses the REST client.
- R2 matches whole text forms of exceptions in the handled chain; transformed text (`str(e)[:100]`) or text logged outside the except arm at ERROR is not matched (follow-up).
- A chain of ten exceptions with 20,000-character JWT-shaped texts costs about 1.6 s in the hooks; the root cause is #286.

Follow-up: #324 (#286, #293, the Railway half of #301, #226, #287, the remaining pins).

Owner action after merge (not code): enable "Prevent Storing of IP Addresses" on both Sentry projects.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
