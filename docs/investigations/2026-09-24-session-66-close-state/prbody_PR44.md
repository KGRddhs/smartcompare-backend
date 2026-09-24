## fix(llm): OPENAI_BASE_URL fails CLOSED on a bad value, never falls back to api.openai.com

**Rescue of PR #44** (`fix/llm-base-url-failsafe`, opened 2026-08-18, CI red on the old baseline). This branch carries the original commit rebased onto `b203cfcc` (#166) plus the fix its adversarial review demanded. Supersedes #44; close that one when this merges.

### Defect
`app/services/llm_provider.py` validates `OPENAI_BASE_URL` for every `AsyncOpenAI` factory: `extraction_service.get_client`, `url_extraction_service.get_client`, and `openai_service.get_client` in both its shared and dedicated forms. On origin/main it has three problems:
- A malformed value makes `provider_base_url()` return `None`. The SDK then re-reads the variable itself (openai 3.3.1 `_client.py`: `if base_url is None: base_url = os.environ.get("OPENAI_BASE_URL")`), so the value the module rejected is used anyway. Meanwhile the module logs "using stock OpenAI" and `describe_provider()` says `openai`.
- A blank or whitespace-only value reaches the SDK as `''`, `'%20%20%20/'`, or (for `'\t'`) an `InvalidURL` raised at construction. It is not treated as unset.
- The scheme check is case-sensitive. `HTTPS://UPPER.test/v1` is called malformed even though it works.

The PR's first cut replaced `None` with the stock URL. That made a malformed value fail OPEN. Measured with the network blocked: `api.gateway.test/v1`, the most likely typo (a gateway URL missing its scheme), sent the configured key and the users' prompts to api.openai.com. origin/main failed closed on it, by accident.

### Fix
- Unset, blank or whitespace-only: `provider_base_url()` returns the EXPLICIT stock URL `https://api.openai.com/v1`, never `None`.
- An `http://` or `https://` URL with a non-empty host: returned with the scheme lower-cased. The scheme match ignores case, and surrounding whitespace is stripped.
- Anything else is non-blank and malformed, and it FAILS CLOSED:
  - The raw value (stripped) is returned unchanged, so every client is built against it and every request fails at request time with `openai.APIConnectionError`.
  - Each call logs one `logger.error` that names `OPENAI_BASE_URL`. The value is redacted to its length and first 8 characters, because the raw value may carry userinfo.
  - Measured on openai 3.3.1 / httpx 0.28.1, there are three failure classes, and none reaches api.openai.com or the intended gateway:
    - No http(s) scheme (`not-a-url`, `api.gateway.test/v1`, `//proto`, `ftp://x`, `junk value`): `UnsupportedProtocol`, raised before any DNS lookup or connect.
    - An http(s) scheme but no host (`https://`, `http://`, `https:/gw.test/v1`, `HTTPS:/gw.test/v1`, `http:gw.test/v1`, `https:\\gw.test\v1`): one resolution attempt on an EMPTY host, then `ConnectError`.
    - An unparseable authority (`https://[gw.test/v1`): one resolution attempt on `%5bgw.test`, then `ConnectError`.
- `is_custom_provider()`: True only for a valid, non-stock URL. Every spelling of the stock URL (scheme and host case, trailing slash) counts as stock. A query string or fragment on api.openai.com/v1 makes it not stock.
- `describe_provider()`:
  - It returns `openai`, `openai-compatible@<url>`, or `misconfigured:OPENAI_BASE_URL`. A malformed value is never echoed.
  - The URL it shows has userinfo, query and fragment stripped. When an unencoded `/`, `?` or `#` in the password makes urlsplit cut the authority early, the whole location is shown as `<redacted>`.
  - It computes `provider_base_url()` once per call, so one call gives one error line.
- Stale docstrings and the unused `Optional` import are removed. The docstrings state the contract above.

### Evidence (all local, pinned venv: fastapi 0.141.1 / pydantic 2.13.4 / openai 3.3.1 / httpx 0.28.1 / pytest 9.1.1)
- **Unit file** `tests/test_llm_provider_base_url.py`: 74 passed. Every test uses an autouse guard that blocks non-loopback getaddrinfo/connect and fails the test on any attempt it does not explicitly take. The DESTINATION tests drive a real `AsyncOpenAI` request and read which host the SDK tried to resolve.
- **Same file against other versions of the module:**

  | Module | Result |
  |---|---|
  | origin/main | 44 failed / 30 passed, no ImportError (new names are resolved with getattr fallbacks) |
  | PR first cut | 49 failed / 25 passed / 6 errors |
  | Previous fix round | 6 failed |

- **Mutations:** 24 mutants on the final code, applied from a sha-verified byte snapshot and restored after each run. 23 were killed. The 1 survivor removes a redundant `.lower()` in `_is_stock`, whose input is already lower-cased, so it is an equivalent mutant.
  - The fail-open mutant (malformed → stock) is killed by 40 nodes.
  - Dropping the error log is killed by 11.
  - Logging the raw value is killed by 1.
  - Keeping userinfo in the label is killed by 9.
- **Round-2 adversary: SOUND**, with three minors recorded here, none a defect: (1) three classification branches have no pin of their own and their mutants survive 74/74 (`_is_http_url` using `netloc` instead of `hostname`, so `https://user@/v1` and `https://:443/v1` count as valid; `_is_stock` accepting `http://api.openai.com/v1` as stock; `_is_stock` ignoring the `/v1` path); (2) the `except ValueError` branch in `_without_credentials` is unreachable (`_is_http_url` has already parsed the same string), so its mutant is equivalent; (3) the list of nodes that also pass on main is 30, not the 24 the first body named (the six extra are `test_unset_or_blank_requests_go_to_stock_openai[None]`, the three `test_no_log_line_for_unset_or_valid` nodes and `test_explicit_stock_url_is_labelled_openai[HTTPS://API.OPENAI.COM/v1]`); all 30 do go red under the relevant mutants or against the PR's first cut, so they are regression guards, not dead tests.
- **Neighbours:** the 88 test files that reference the provider or its factories. Run with `-m "not (live_unit or live_db or integration)"`: 5 failed / 1964 passed / 3 skipped / 35 xfailed.
  - 3 failures are the known `test_camera_vision::TestIdentifyProductsMocked` MagicMock>int nodes, the same as on base.
  - 2 are `test_openai_breaker::test_flag_off_{compare,streaming}_never_short_circuits`, which timed out a 15 s price race under box load. Re-run alone they gave 18/18 passed, and they do not touch `OPENAI_BASE_URL`.
  - The rebaser's base run of this set was 3 failed / 1907 passed (the camera trio only).
- **Lint:** ruff `E9,F63,F7,F82` (plus `F401,F841`) clean; `py_compile` clean.
- **Commit-time verification (2026-09-24):** the fake key literal in the unit test was shortened (the 26-character `sk-…-do-not-log` literal -> `sk-fake-do-not-log`, every occurrence) so the repo's pre-commit secrets guard (`\bsk-[A-Za-z0-9_-]{20,}`) does not fire on test data; the test still asserts the value never reaches a log line. On the pinned venv the unit file plus `test_openai_breaker.py` gave 92 passed, 0 failed; ruff + py_compile clean.
- **Base:** this branch sits on `b203cfcc` (#166). The `git fetch` before the commit-time rebase failed on the box's TLS path, so the branch was NOT rebased onto the current main (`4eeb18aa` at the time of writing). `git diff b203cfcc origin/main` over `llm_provider.py`, `openai_service.py`, `extraction_service.py`, `url_extraction_service.py` and the unit test file was empty at `7368f862`; **re-check at merge and rebase if GitHub reports a conflict.**

### Env / flag state
There is no feature flag; the only lever is `OPENAI_BASE_URL`, read fresh per call.
- **Unset:** every factory gets `client.base_url == 'https://api.openai.com/v1/'`, identical to the SDK default. The only object difference is the SDK's private `_base_url_was_default` (False here, True for the SDK default). openai 3.3.1 reads it only in copy()/with_options when the workload-identity mode changes, and this app configures no workload identity, so it has no effect.
- **Prod:** "OPENAI_BASE_URL is unset on both Railway services, so prod behaviour is unchanged" is **UNVERIFIED**. Railway was not read for this PR.

### Honest limits
- **Tests that prove nothing new.** 30 of the 74 nodes also pass on origin/main (listed above). Main already failed closed on malformed values by accident, so they cannot show this fix as red.
- **Resolver calls remain.** Empty-host and unparseable http(s) values still make one resolver call on an empty or mangled name. Removing that would mean returning something other than the raw value, which the fail-closed design rules out. The empty-host destination test asserts that the attempted hosts are a subset of `{""}` rather than exactly one attempt, so CI on Linux tolerates a platform that makes zero attempts.
- **Space after the scheme.** `https:// gw.test/v1` is still accepted as valid (hostname ` gw.test`). The request tries `%20gw.test` and the label shows the space. It is not a credential leak.
- **Over-redaction.** The label redaction is conservative: a legitimate `@` in a base-URL path or query also redacts the label. This affects the label only, not routing.
- **Construction-time failures.** A password containing an unencoded `?`, `#` or `/` makes the SDK raise `httpx.InvalidURL` at client construction, on main and here alike. It is loud and makes no network attempt.
- **No callers yet.** `describe_provider()` and `is_custom_provider()` have no app callers today, only tests.
- **How the unit tests were run.** They ran in-process after pre-importing openai: a cold import takes 2-5 minutes on the test box and trips the per-test timeout. One matrix launch died with a Windows access violation during an import (environmental). It was relaunched from a sha-verified restore and completed cleanly.

### Follow-ups (not in this PR)
- **Pre-existing key-tail log line:** `app/services/extraction_service.py:51` `get_client` logs the last 10 characters of `OPENAI_API_KEY` at INFO. A probe found the sentinel's 10-char tail in logs on both base and head. It needs its own issue (log the presence and length only).
- Pin the three unpinned classification branches named by the round-2 adversary.
- Optionally reject whitespace inside the authority, e.g. `https:// gw.test`.
- Confirm on CI that `test_conftest_env_safety.py::test_app_main_still_imports_under_the_sentinels` passes. It timed out only on the loaded box.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
