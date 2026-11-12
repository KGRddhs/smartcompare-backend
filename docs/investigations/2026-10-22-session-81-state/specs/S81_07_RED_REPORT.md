# S81-07 MEAS-CLAUDE-GATE: RED REPORT (Opus 5.5, 2026-11-12)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s07, HEAD 6b909e0a92067d6b3562eee325e4956c116441f7 (verified), git status --short empty at start; at end: `?? tests/test_s81_s07_meas_harness.py` only (the amendments file sits under the gitignored .qa-s80/).

## Files written
- .qa-s80/S81-07_SPEC_AMENDMENTS.md 35062 bytes sha256 8ccfecc4... (ASCII, LF)
- tests/test_s81_s07_meas_harness.py 70941 bytes sha256 447ef4da... (0 bytes > 127, 0 CR; py_compile OK; ruff E9,F63,F7,F82,F401 clean)
- scratch only: probe_red.py + probe_red.json, notes.md, the logs, failed_ids.txt (109 node ids).

## Runs ([pyt] lines)
Base pass record of spec 1.10, each file ALONE:
- [pyt] tag=s07r-base-test_conftest_env_safety start=2026-11-12 03:15:21 end=2026-11-12 03:15:50 elapsed=29s bound=600s status=OK rc=0 (24 passed, 1 skipped, 2 deselected; netguard blocked 0)
- [pyt] tag=s07r-base-test_hermeticity_pins start=2026-11-12 03:15:51 end=2026-11-12 03:17:00 elapsed=69s bound=600s status=OK rc=0 (103 passed; netguard blocked 22 attempts from 21 nodes = the self-tests' deliberate 192.0.2.1 / example.com:80 blocks)
- [pyt] tag=s07r-base-test_model_config start=2026-11-12 03:17:01 end=2026-11-12 03:17:07 elapsed=6s bound=600s status=OK rc=0 (34 passed)
- [pyt] tag=s07r-base-test_model_config_enforced start=2026-11-12 03:17:09 end=2026-11-12 03:17:14 elapsed=6s bound=600s status=OK rc=0 (25 passed)
- [pyt] tag=s07r-base-test_shadow_experiments start=2026-11-12 03:17:15 end=2026-11-12 03:17:18 elapsed=3s bound=600s status=OK rc=0 (78 passed)
Sum 264 passed, 1 skipped, 2 deselected = the spec's 1.10 record, confirmed.
RED file at base:
- [pyt] tag=s07r-unit-base start=2026-11-12 03:27:26 end=2026-11-12 03:27:43 elapsed=17s bound=600s status=FAIL rc=1 (38 failed, 11 passed, 71 ERRORS: the hx fixture asserted in setup; fixed with a lazy harness built in the test body)
- [pyt] tag=s07r-unit-base2 start=2026-11-12 03:28:02 end=2026-11-12 03:28:18 elapsed=15s bound=600s status=FAIL rc=1 (109 failed, 11 passed; 108 AssertionError + 1 FileNotFoundError in R11; fixed: R11 calls _mod() first)
- [pyt] tag=s07r-unit-base3 start=2026-11-12 03:29:11 end=2026-11-12 03:29:23 elapsed=12s bound=600s status=FAIL rc=1 = FINAL: 109 failed, 11 passed, 0 errors, 0 skipped; every failure an AssertionError (109 of 109 'E  AssertionError' lines, no other class); [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 120 test(s).

## Measurements of step 3 (probe_red.py, httpx2.MockTransport, 0 sockets, no ANTHROPIC_* name set)
- Streams (R-S07-14 (d)): events message_start (RawMessageStartEvent, message.usage class Usage), content_block_start, content_block_delta, content_block_stop, message_delta (usage class MessageDeltaUsage: cache_creation_input_tokens, cache_read_input_tokens, input_tokens, output_tokens (the only required field), output_tokens_details, server_tool_use), message_stop. A stream truncated after content_block_delta ENDS WITHOUT RAISING: the harness must check message_stop itself. A transport ReadError -> APIConnectionError. Pinned P07.
- Exceptions (R-S07-14 (b)): 400 BadRequestError, 401 AuthenticationError, 403 PermissionDeniedError, 404 NotFoundError, 409 ConflictError, 413 RequestTooLargeError, 422 UnprocessableEntityError, 429 RateLimitError, 500 / 502 / 503 / 504 InternalServerError, 529 OverloadedError (all APIStatusError; status_code set; retry-after readable at exc.response.headers; max_retries=0 -> 1 request each); ReadTimeout / ConnectTimeout -> APITimeoutError (a subclass of APIConnectionError, fixed message text); ConnectError / ReadError / RemoteProtocolError -> APIConnectionError ("Connection error."). The SDK also defines ServiceUnavailableError and DeadlineExceededError, produced by no status measured. Pinned P08.
- Web-search tool types (R-S07-29): WebSearchTool20250305Param (web_search_20250305), WebSearchTool20260209Param (web_search_20260209), WebSearchTool20260318Param (web_search_20260318). Stage W measures 20250305 (S81-21, PLAN_S81.md:165) and 20260318 (found, so kept as W3 / W4). Pinned P09.
- Credential resolution (R-S07-33): with api_key explicit, anthropic._client.default_credentials is called 0 times, x-api-key is sent and NO authorization header, with a fake user_oauth profile under APPDATA / HOME / USERPROFILE / XDG_CONFIG_HOME = tmp. Control without a key: default_credentials called once and the profile token IS sent as authorization (the folder is live). Conclusion: a profile on disk cannot add or replace the auth header when the key is explicit; NO folder refusal is needed. Pinned P05 (explicit clause) + P10 (control).

## Row table (R = red at base on an AssertionError only; P = green at base)
| row | class | pins |
|---|---|---|
| R01 module, entry, public surface, exit codes | R | spec 2.1 / 2.15, amendments A0 |
| R02 name, ceilings, defaults, constants | R | R-S07-3 (a), R-S07-4, spec 2.1 |
| R03 x16 each ANTHROPIC_* name refuses (variable set) | R | R-S07-3 (b), 16 (a), 26 (b) |
| R04 x5 import-time + suite credential names refuse | R | spec 2.3 step 3, 26 (b) |
| R05 x3 key missing / empty / blank | R | spec 2.3 step 4 |
| R06 --out inside the repo | R | spec 2.2 |
| R07 client explicit, retries 0, trust_env False, no redirects, 0 mounts, proxy names | R | spec 2.3 step 10, Q7 |
| R08 canary absent on success (4-char window) | R | R-S07-3 (c), 18 (a) |
| R09 canary absent on an SDK error; no message field | R | R-S07-3 (c), spec 2.5 |
| R10 crash line exact, canary absent | R | spec 2.12, 13 (b) |
| R11 AST + dynamic: no read of the production key | R | R-S07-3 (e), 16 (b) |
| R12 SDK loggers pinned | R | spec 2.3 step 5 |
| R13 dry-run: no client, no key read; the 622 plan; stage caps | R | R-S07-10, 17, 22 |
| R14 every sent request is a to_claude_request result (spy); model and cap | R | R-S07-8 |
| R15 Sonnet between_tools = _escalation_request | R | spec 2.6 A3 |
| R16 pricing from usage, long context, search, unpriced | R | R-S07-4, 14 (b) |
| R17 worst-case stop (the output term; budget exit 6) | R | R-S07-4, 14 (a) |
| R18 unit ceiling 11.50 -> 4; 10.99 starts | R | spec 2.3 step 9 |
| R19 x6 --max-usd lower-only and bad values | R | spec 2.2, 25 |
| R20 intent + done per call, closed key sets, 2 fsync, fsync before each create | R | 14 (c) |
| R21 resume: ok ids not re-sent, the transient re-sent as attempt 2 | R | 14 (c), spec 2.7 |
| R22 --max-calls 7 -> 7 creates | R | spec 2.5 |
| R23 x2 401 / 403 stop at once, exit 5 | R | R-S07-5 |
| R24 x2 three consecutive transients; reset on success | R | R-S07-5 |
| R25 x3 429 retry-after 2 / missing 5 / 999 -> 60; the setting stops; the next runs | R | R-S07-5 |
| R26 wall clock | R | R-S07-5 |
| R27 interrupt 130, PARTIAL | R | R-S07-5, 13 (b) |
| R28 vision / web_search NOT RUNNABLE, owner inputs listed | R | R-S07-2 |
| R29 GO_THRESHOLDS as ruled, report rows, knob names, tail words | R | R-S07-31, 20 |
| R30 raw without headers | R | spec 2.5 (f) |
| R31 no model literal | R | R-S07-8 |
| R32 moderation production path, patch restored | R | spec 2.8 |
| R33 A6 = 120, one mismatch counted | R | spec 2.6, 24 |
| R34 count_tokens x20 without max_tokens, retrieve ids, usd 0 | R | spec 2.6 |
| R35 fixtures: exist, counts, Arabic >= 30, no person keys, LF, gold keys | R | spec 2.9, 21, 24 |
| R36 dotenv guard + post-import re-scan | R | spec 2.3 steps 6-8 |
| R37 E1: the name in CREDENTIALS_UNSET | R | R-S07-32 OQ-1 |
| R38 stream=True, ttft, booked usd from the stream usage | R | 14 (d) |
| R39 stage M 401 at case 3: 3 creates, exit 5, not_run tail | R | 13 (c)(d) |
| R40 stage M budget stop: no unavailable, exit 6 | R | 13 (c)(d) |
| R41 StageStop(BaseException), STOP_REASONS, str = reason | R | 13 (a) |
| R42 last-resort BaseException arm | R | 13 (b) |
| R43 four concurrent sends, a cap for three -> three creates, one budget stop | R | 14 (a) |
| R44 the booking table | R | 14 (b) |
| R45 sent / done pairs with call_id + attempt | R | 14 (c) |
| R46 unmatched intent booked at worst and re-sent as attempt 2 | R | 14 (c) |
| R47 x3 corrupt ledger refuses, file + line only | R | 14 (c) |
| R48 stream_usage merge; R48b a truncated stream books worst | R | 14 (d) |
| R49 the lock refuses and is kept; removed after a run | R | 14 (e) |
| R50 the long-context row in the bound | R | 14 (f) |
| R51 dotenv bindings, OPENAI_API_KEY, ENABLE_* restored | R | 16 (d) |
| R52 canary in a text block -> [redacted], redactions 1 | R | 18 (b) |
| R53 closed results keys, env_var_name, the one REPORT name line | R | 18 (c) |
| R54 x3 key stripped (CR LF, space, tab); R54b x3 malformed refuses | R | 18 (d) |
| R55 nearest-rank percentiles, +inf timeouts, ceil_half, proposals | R | 19, 20 |
| R56 A1_ROUND_ORDER; R56b tail_span_ms per round | R | 17, 20 |
| R57 moderation set shape | R | 21 |
| R58 100-photo vision plan, Sonnet on v2 only, <= 5.00 | R | 22 |
| R59 x5 lower-only max-calls / max-minutes / reps | R | 25 |
| R60 host_allowed + the live host guard (host_refused) + guard removed | R | 26 (a) |
| R61 refused-name coverage of the suite lists; no tests import | R | 26 (b) |
| R62 ENABLE_* removed + the flags file applied / refused | R | 27 |
| R63 web-search tool types + W1..W4 settings | R | 29 |
| R64 the A6 sentence, the folder sentence, out_dir | R | 28, 30 |
| R65 the 429 give-up stops the setting only | R | 13 (a), spec 2.14 |
| P06 gold labels recompute (fixture existence asserted) | R at base, P after GREEN | 16 (c), 24 |
| P01 app never names the harness | P | spec 2.13 (c) |
| P02 SITES contract, to_claude_request keys | P | spec 1.1 |
| P03 twelve builders capture offline (full flag configuration) | P | spec 1.2 |
| P04 price rows | P | spec 1.4 |
| P05 SDK hazards + the explicit-key credential clause | P | spec 1.3, 33 |
| P07 stream events / usage classes / truncated stream | P | 14 (d) measured |
| P08 exception class map | P | 14 (b) measured |
| P09 web-search type names | P | 29 measured |
| P10 profile control | P | 33 measured |
| P11 scripts client allowlist | P | 30 |
| P12 suite credential lists | P | 26 (b) |
Counts: 80 test functions, 120 nodes = 109 RED nodes (69 functions incl. P06) + 11 PIN nodes.

## Mutation table as amended (ids + one line; the next agent runs it)
M01 prefix narrowed to ANTHROPIC_API (R03); M02 env scan after the client build (R03); M03 OPENAI_API_KEY dropped (R04); M04 blank key accepted (R05); M05 --out check removed (R06); M06 max_retries from model_config (R07); M07 trust_env True (R07); M08 follow_redirects True (R07); M09 ledger records str(exc) (R09); M10 crash line repr(exc) (R10); M11 fallback read of the production name (R11); M12 logger pins removed (R12); M13 dry-run builds the client (R13); M14 capture sent without to_claude_request (R14); M15 escalation = a model swap only (R15); M16 cache_read not priced (R16); M17 unpriced books 0 (R16); M18 worst-case check removed (R17); M19 output term 0 (R17); M20 unit ceiling 150 (R18); M21 --max-usd above the default accepted (R19); M22 fsync removed (R20); M23 resume ignores completed ids (R21 / R46); M24 resume skips transient (R21 / R46); M25 max-calls off by one (R22); M26 401 classed transient (R23); M27 counter not reset (R24); M28 transient stop 4 (R24); M29 rate-limit retries 4 (R25); M30 retry-after ignored (R25); M31 the 60 s clamp removed (R25); M32 wall clock removed (R26); M33 KeyboardInterrupt arm removed (R27); M34 vision without --set (R28); M35 web_search without --owner-line (R28); M36 tail x1.0 (R29 / R55); M37 len(value) in the report (R53); M38 raw stores headers (R30); M39 moderation copy with max_tokens 128 (R32); M40 patch not restored (R32); M41 dotenv guard call removed (R36); M42 post-import re-scan removed (R36); M43 stream=True dropped (R38); M44 scrub not applied (R52); M45 reserve ignores reserved (R43); M46 a timeout books 0 (R44); M47 intent written after the send (R45); M48 lock skipped (R49); M49 flat Haiku row above 100k (R50); M50 StageStop subclasses Exception (R39 / R41); M51 a stopped case recorded unavailable (R40); M52 dotenv not restored (R51); M53 stream_usage ignores message_delta (R48); M54 a truncated stream priced from its partial usage (R48b); M55 key not stripped (R54); M56 any port-443 host allowed (R60); M57 SUPABASE_URL dropped from REFUSED_ENV_NAMES (R61 / R04); M58 ENABLE_* removal skipped (R62); M59 web_search_20250305 dropped (R63); M60 the 429 give-up stops the stage (R65); M61 percentile drops timeouts (R55). Expected 61 / 61 KILLED.

## Deviations (stated, never silent)
- D1 the canary body: secrets.token_hex(16) mapped to the letters G..V before use (amendments A9): the ruled 4-character window over a raw hex body collides with the harness's legitimate hex call ids; the randomness and the window are kept.
- D2 R-S07-14 (a)'s concurrency row runs at the Dispatcher level (four concurrent Dispatcher.send calls on one Budget), not through a whole A1 phase (the per-call worst cases of a phase differ, so "a cap that fits three" is exact only at one request shape).
- D3 the spec's ledger key `retry` is DEAD, replaced by `attempt` (amendments R-S07-14 (c)); the spec's refusal text "refused: unit ceiling" becomes the code `unit_ceiling`.
- D4 REFUSED_ENV_NAMES widened to the suite's CREDENTIALS_UNSET + CREDENTIAL_PLACEHOLDERS (ruling 26 (b)), so every R row's fixture deletes all of them (incl. the conftest's SUPABASE_* / YOUTUBE_API_KEY placeholders), beyond 16 (a)'s OPENAI_API_KEY.
- D5 409 ConflictError is booked at worst (not in the ruled unbilled list) and counted non-transient for resume (stated limit L14).
- D6 R14 is one row checking all twelve sites of one A1 round through a spy on llm_router.to_claude_request (not a parametrization over sites); R03 gained ANTHROPIC_CONFIG_DIR (the SDK's config-dir variable, measured in the credential chain).
- D7 R13's stage-V dry-run uses a 1-photo set; the 100-photo plan check is its own row R58.
- D8 P06 recomputes with compute_scores(pair) + build_scores_summary(dedup_brand_name names) and asserts BOTH the stored winner and the stored scores_summary (the shadow_experiments pattern); GREEN's generator must produce exactly those.
- D9 the amendments add a public surface (amendments A0 / A6 / A7 / A8: Budget, Dispatcher, the pure functions, the results / plan shapes, the refusal codes) that the rulings left to the RED; GREEN must expose it.

## Open questions for the gate
- Q1 Accept D1 (the canary alphabet) as satisfying R-S07-18 (a)?
- Q2 Accept D2 (the reservation row at the Dispatcher level)?
- Q3 R10 forces the crash by subclassing Dispatcher.send (an exception from the fake client is a booked SDK-path error, not a crash); acceptable?
- Q4 R60 calls socket.getaddrinfo from inside the fake create, so the harness guard must wrap socket.getaddrinfo above the netguard plugin; confirm this layering in the unit file.
- Q5 Confirm the A0 surface as the contract (D9).

## NOT MEASURED
- The comm set and the client fences (GREEN's gates); the mutation table (the next agent); every server-side acceptance (stage findings by construction).
