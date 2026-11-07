# S81-G9 FOLLOWUPS - group unit spec (S81-16c + D17c + S81-22d + S81-23b)

Spec writer: Opus 5.5 (claude-opus-5-5), 2026-11-07 09:52-10:40 AST. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g9`, detached at the base `39ac80ba437760d1a77eaac9670faeea505f08f4` (origin/main after #394); `git status --short` empty before and after every probe (only this gitignored `.qa-s80/` file is new; `git check-ignore .qa-s80/x` = ignored). Branch for RED / GREEN: `feature/s81-g9-followups` (the RED re-points to the then-main; section 12.7). Measurement scripts, logs and digests: `<scratchpad>/g9spec/` (scratchpad = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/8723f7aa-4b51-496c-9ed1-d602ed517c8b/scratchpad`). Binding inputs read: `scripts/s81-common.txt` (LC-1..LC-9, the MOVING MAIN lines :99-109), `specs/S81_G9_BRIEF.md` (in full, twice), `specs/RULINGS_S81_16C.md` (R-S16C-0..8), the ops brief `WIKIDATA_SPARQL_EXEMPTION_BRIEF.md` (the relay's notes folder), the filed `docs/policies/2026-11-07-wdqs-robots-exemption.md` (docs branch `docs/session-81-state` at 7db4f457; 3,986 bytes, LF, 0 bytes > 127, sha256 `9613f9feb7161b0ff899b8ddfedb9082da17557408c6b97629d27f1e814cb7dd`), the worked group spec `specs/S81_G8_UNIT_SPEC.md`, PLAN_S80 section 0 + R-A1 / R-A13 and `runs/research/contract_freeze.json` (re-read before every section 2), `specs/RULINGS_FIX1_S81_22.md` F1-7 (L-I2I6), the ledger to its newest line (10:12 box time; the ops stamps run about an hour ahead, ledger.md:355). Personal-data rule: synthetic hosts (`store-a.example.com`, `h000.example.com`), no person; the only names are public (Wikidata, Upstash, Scrape.do). No production probe, no Wikidata / Upstash / Scrape.do request (the SDK is driven through `httpx.MockTransport`).

Production state (newest dated lines only): `ENABLE_KB_BRANDS` unset (the brand script runs only by hand; nothing in kb_brands, ledger.md:318); `ENABLE_KB_COVERAGE_ROLLUP=apply` on the kb-coverage service since the 11:20 ops line (ledger.md:356; first apply pass 01:20Z 2026-11-08) - so D17c is NOT dark on that service, see 12.6; `ENABLE_COMPARE_RUN_LEDGER` unset; `SCRAPEDO_SUPER` unset on web and price-warmer since 09:02 (ledger.md:333) and `ENABLE_SCRAPEDO_SUPER` never set; Apple approval on the owner's word 09:02 (ledger.md:330) - both S81-23b preconditions (the unset line AND approval, CLAUDE.md:540 "Stated post-approval change") are MET.

## 0. The group

| Unit | What | Flag | Files (non-test) | RED file |
|---|---|---|---|---|
| S81-16c WDQS-EXEMPTION | the exact-rule-set exemption for the ONE SPARQL URL in `_run`, the refusal line names the check, ONE bounded retry on 429 / 503 | none new: rides `ENABLE_KB_BRANDS` (unset in production) | `scripts/seed_kb_brands_wikidata.py`; docs: NEW `docs/policies/2026-11-07-wdqs-robots-exemption.md` (the filed bytes), one pointer line in `docs/policies/2026-08-31-robots-unreadable-ruling.md` | `tests/test_s81_s16c_wdqs_exemption.py` |
| D17c COVERAGE-EMPTY-HOSTS | the hosts family: 0 hosts = a counted skip with NO pipeline call; a failed pipeline counts the family in `not_built` with one constants-only WARNING; (+ D17d process-exit PIN rows, ruled into the lane at 10:05) | none new: rides `ENABLE_KB_COVERAGE_ROLLUP` (apply on kb-coverage) | `scripts/cron_kb_coverage.py` | `tests/test_s81_d17c_coverage_hosts.py` |
| S81-22d LEDGER-PINS-FLAG-SAFE | the S81-03 isolation rows i2 / i6-off delete `ENABLE_COMPARE_RUN_LEDGER` explicitly (green exported and unset) | none (test-only) | none (E-row EK1 on `tests/test_s81_s03_llm_ledger_v2.py`) | `tests/test_s81_s22d_ledger_pins.py` |
| S81-23b SCRAPEDO-SUPER-RETIRE | delete the legacy `SCRAPEDO_SUPER` branch of `scrapedo_super_enabled` (unset `ENABLE_SCRAPEDO_SUPER` = OFF); drop the legacy write in `scripts/ab_render_providers.py` | none (unflagged under R-A1 (c)) | `app/services/scrapedo_service.py`, `scripts/ab_render_providers.py` | `tests/test_s81_s23b_scrapedo_super_retire.py` |

Change list per unit, in the GREEN order (byte copies first, `shutil.copyfile`, sha256 recorded):
1. S81-22d: EK1 (two added lines in the frozen S81-03 file, 22d.3) - first because it is test-only and its gate reads the untouched app.
2. S81-23b: `scrapedo_service.py` (the reader, its docstring + the transition comment), `ab_render_providers.py` (one line deleted + one comment), E-rows EK2 (`tests/test_s81_s23_bypass_retire.py`) and EK3 (`tests/test_fragrance_content_quality.py`).
3. D17c: `cron_kb_coverage.py` (the skip, the counter, the label).
4. S81-16c: `seed_kb_brands_wikidata.py`, then the two docs files.
5. CLAUDE.md last (section 12.5).

Files two units share: ONLY `CLAUDE.md` (the G9 block, the :341 clause, five in-place edits from three units; section 12.5). Every other file belongs to one unit. `scripts/kb_seed_common.py` is deliberately NOT edited (it is in the watch patterns of `railway.kbcoverage.json` and `railway.kbenrich.json`; S81-16c reaches the injected sleep without it, 16c.2). No migration, no `SmartCompareApp/`, no `.github/`, no `.githooks/`, no requirements, no railway config, no app/ file other than `scrapedo_service.py`.

Line endings (`git ls-files --eol`): every edited tracked file is index LF / working copy CRLF (`seed_kb_brands_wikidata.py`, `cron_kb_coverage.py`, `scrapedo_service.py`, `ab_render_providers.py`, the three E-row test files, `CLAUDE.md`, `docs/policies/2026-08-31-robots-unreadable-ruling.md`; `core.autocrlf=true`, no `.gitattributes`). The Edit tool keeps CRLF; a whole-file diff in `git diff --stat` is a defect. New files (the four RED files) are pure ASCII + LF; the new policy doc is copied as the exact docs-branch bytes (LF, the sha above; a CRLF working copy after checkout is the autocrlf rendering, the blob is what is pinned). The frozen-file shas are recorded as LF blob shas (`git show HEAD:<path> | sha256sum`), never the CRLF working copy.

Base pass state of the files the group touches (bounded runner, this run, box clean - no foreign pytest by the process list at each launch):
- `[pyt] tag=g9spec-base-pins start=2026-11-07 10:14:52 end=2026-11-07 10:15:23 elapsed=31s bound=1200s status=FAIL rc=1` - 1114 passed, 7 failed, all the known CRLF working-copy class (`test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[x5]`, `test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene`, `test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf`; each assertion is `b'\r' not in <bytes>`); files: test_s81_s16_kb_seed, test_s81_s16b_kb_brands, test_robots_unreadable_ruling, test_s81_d17_coverage, test_s81_d17b_coverage_paging, test_s81_kb_schema, test_s81_s22_compare_runs, test_s81_s22_gate_rows, test_s81_d14_live_robots.
- `[pyt] tag=g9spec-s03-unset start=2026-11-07 09:57:12 end=2026-11-07 09:57:25 elapsed=13s bound=1200s status=OK rc=0` - 215 passed (`tests/test_s81_s03_llm_ledger_v2.py`).
- `[pyt] tag=g9spec-s03-exported start=2026-11-07 09:56:50 end=2026-11-07 09:57:06 elapsed=15s bound=1200s status=FAIL rc=1` - with `ENABLE_COMPARE_RUN_LEDGER=true` in the runner call only: 4 failed / 211 passed (22d.1).
- `[pyt] tag=g9spec-s23b-base start=2026-11-07 09:58:30 end=2026-11-07 10:00:14 elapsed=104s bound=1200s status=FAIL rc=1` - the 23-file super-gate set (`<scratchpad>/g9spec/s23b_set.txt`): 924 passed, 1 failed (`test_s81_s19_gap_queue.py::test_r15_hygiene`, the CRLF class).
- `[pyt] tag=g9spec-s23b-proto2 start=2026-11-07 10:02:47 end=2026-11-07 10:04:33 elapsed=106s bound=1200s status=FAIL rc=1` - the same set with the post-change reader patched in at `pytest_runtest_call` (plugin `<scratchpad>/g9spec/plugins/g9_s23b_proto.py`, no file edited): 12 failed (23b.4).

---

## Unit S81-16c WDQS-EXEMPTION

### 1. Base state (measured at 39ac80ba)

| # | Site | Measured |
|---|---|---|
| 1.1 | `scripts/seed_kb_brands_wikidata.py:227-266` `_run` | reads kb_merchants (:230-235), `fetcher = common.PoliteFetcher()` (:236), robots GET `ROBOTS_URL` gate=False timeout 20 (:237); 2xx -> body, 404 / 410 -> "" (fail open by the RFC), else INFO `"%s robots unreadable; nothing read"` + return 0 (:238-244); `url = sparql_url()` (:245); the gate (:246-248) `if not (re_.can_fetch(body, re_.QARENBOT_UA, url) and re_.can_fetch(body, "*", url))` -> INFO `"%s robots disallow the query endpoint; nothing read"` + return 0; the ONE SPARQL GET timeout 60 (:249); non-2xx -> INFO `"%s query failed status=%d"` + return 0 (:250-252); json bindings (:253-257); derive + optional write + report + counts (:258-266). Constants `ROBOTS_URL` :35, `SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"` :36, `SPARQL_LIMIT` 2000 :37, `MAX_BRAND_HOSTS` 300 :51. |
| 1.2 | flag idiom | `main` (:269-281): `common.run_mode("ENABLE_KB_BRANDS")` FIRST (OFF = one INFO line naming both flags, return before any I/O); `cli_mode` (--dry-run downgrades apply); `resolve_client`; `asyncio.run(_run(...))`. Script runs only by hand (no railway startCommand names it, pinned by `test_s16b_pin5`). |
| 1.3 | `app/services/robots_eval.py` (243 lines, LF blob sha256 `bb584acb0539e67b53e8bc6e18a8e9280259ee5194be85a38b2648b64aff3cc2`) | `parse_groups` (:101-136) -> `[(frozenset(agents_lower), [(is_allow, pattern)])]`, comments stripped at `#`; `rules_for_agent = _rules_for_agent` (:187-214): the longest named token that occurs in the lowercased agent string wins, else every `*` group merged; `can_fetch` (:217-243) longest match, allow wins ties, fails OPEN on no groups / no rules / any error. `QARENBOT_UA = "QarenBot/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)"` (:82). No exemption, allowlist or override mechanism. |
| 1.4 | measured probe (`<scratchpad>/g9spec/probe_16c.py`) | the live-shaped body `COMMENT(44 bytes) + "User-agent: *\nDisallow: /sparql\nDisallow: /bigdata\n"` = 95 bytes: `parse_groups` = `[({'*'}, [(False,'/sparql'), (False,'/bigdata')])]`; `rules_for_agent(g, QARENBOT_UA)` = `rules_for_agent(g, "*")` = that list; `can_fetch` False / False. + "Disallow: /" -> 3 rules (False/False). + a `User-agent: QarenBot` group with the SAME two rules -> groups 2, both rule lists still EQUAL the pair (so a rule-set comparison alone cannot see the named group: a separate named-group check is required). + a `User-agent: Googlebot / Disallow: /` group -> QarenBot / '*' rule sets unchanged. Reordered (/bigdata first) -> the list order flips. The frozen r24 fixture `"User-agent: *\nDisallow: /sparql\n"` -> ONE rule. An empty `Disallow:` is kept as `(False, "")`. `User-agent: * / Allow: /` -> can_fetch True. |
| 1.5 | `scripts/kb_seed_common.py:303-340` `PoliteFetcher` (LF blob `afc8288e...`) | `get(url, row=None, now=None, *, gate=True, timeout=20.0, delay=None)` -> `robots_registry._fetch_following` with `self._polite` = `Politeness(sleep or asyncio.sleep)`; headers always `dict(robots_registry._REQUEST_HEADERS)` = `{"User-Agent": QARENBOT_UA, "Accept": "*/*"}` (`robots_registry.py:140`); `allow_redirects=False`; returns `FetchResult(status, headers, body[:3_000_000], url, refused, gate)`. `Politeness.before_request` (`robots_registry.py:717-732`): no wait before the first request, then `max(min(delay, 60.0), 2.0)` (`MIN_DELAY_SECONDS` 2.0 :100, `MAX_CRAWL_DELAY_SECONDS` 60.0 :101) through the injected sleep. So `delay=120` would be clamped to 60: the 429 wait cannot ride `delay`. A raising fetch -> status None (unreadable). |
| 1.6 | the Rig fake (`tests/test_s81_s16_kb_seed.py:214-275`) | patches `common.PoliteFetcher` to inject `fetch` / `validate` / `sleep` recorders; `fetch_responses` popped in order (an Exception instance is raised); `rig.fetches[i]` = {url, headers, timeout, allow_redirects}; `rig.sleeps` the waits; `FakeClient` for kb_merchants and the writes. `_merchant`, `_records`, `_mod`, `_attr` reusable by import of the module object (the S16b precedent, `tests/test_s81_s16b_kb_brands.py:33`). |
| 1.7 | frozen rows on this script | `test_s16_r23_brands_dry_and_apply` (allowed body, 2 fetches, headers == `_REQUEST_HEADERS`); `test_s16_r24_brands_robots_failclosed[403/timeout/disallow]` (1 fetch, no write, an INFO containing "robots"; the disallow fixture is the ONE-rule body); `test_s81_s16b_kb_brands.py` S01-S12 + PIN1-6, incl. `s02` OFF inert (0 fetches / sleeps), `s11` (no label / host / "SELECT" / "rdfs:label" / "wikidata.org/entity" in any log record), `s12` script hygiene: CRLF-normalised bytes ASCII, NO literal `"QarenBot"` and no `"NAMED_AGENT"` in the script, no "impersonate", no "claude-" / "/v1/messages", no logger.error outside an except arm, no `.table("...")` literal, the docstring names `ENABLE_KB_BRANDS` and not "DRY-ONLY" / "writes NOTHING". No frozen row gives the SPARQL GET a 429 / 503. |
| 1.8 | libraries | `.venv-qaren` Python 3.12.9; nothing new imported (`re`, `asyncio` already imported in the script). |
| 1.9 | docs | `docs/policies/2026-08-31-robots-unreadable-ruling.md`: 240 lines, LF blob, contains non-ASCII (em dashes; the Edit tool keeps them); no test reads its bytes (`tests/test_robots_unreadable_ruling.py` names it in a docstring only, :3). The new doc is absent from main (`git ls-files` 0). No docs/ walker reads docs/policies (the docs walkers test_be_harness / test_ci_gates / test_migration_043 / test_retro_w1_2d / test_s81_d16_operator_ingest / _retro_r_mig_sql read migrations / workflows / their own paths: measured by grep). |
| 1.10 | base pass state | inside `g9spec-base-pins` (section 0): test_s81_s16_kb_seed (r27 x5 CRLF-red), test_s81_s16b_kb_brands (all green), test_robots_unreadable_ruling (green). |

### 2. Contract

- Flag: `ENABLE_KB_BRANDS` (existing; OFF = byte-identical, the run never reaches `_run`). No new flag, no knob (R-S16C-0).
- New module constants (names carry no gitleaks keyword, R-S16C-4; no `QarenBot` literal, s12):
  - `WDQS_EXEMPT_RULES = ((False, "/sparql"), (False, "/bigdata"))` (the `(is_allow, pattern)` form of `robots_eval.parse_groups`).
  - `WDQS_RULING_DATE = "2026-11-07"`, `WDQS_RULING_DOC = "docs/policies/2026-11-07-wdqs-robots-exemption.md"`.
  - `WDQS_RETRY_STATUSES = (429, 503)`, `WDQS_RETRY_CAP_SECONDS = 120.0`, `_RETRY_IN_RE = re.compile(r"retry in (\d{1,6}) seconds?", re.I)`.
- New pure helper `wdqs_exemption_check(robots_body: str, url: str) -> Optional[str]`: None = exempt; else the name of the FIRST check that refused, in order: `"url"` (`urlsplit(url)` scheme / host / path != `("https", "query.wikidata.org", "/sparql")`, or a fragment, or user info / port present), `"named_group"` (any parsed group token other than `*` occurs in `QARENBOT_UA.lower()`: the same token rule `rules_for_agent` applies, so a `QarenBot` group refuses even when its rules equal the pair), `"rule_set"` (`tuple(rules_for_agent(groups, QARENBOT_UA)) != WDQS_EXEMPT_RULES` or `tuple(rules_for_agent(groups, "*")) != WDQS_EXEMPT_RULES`, order-sensitive tuple equality: an extra rule, `Disallow: /`, an empty `Disallow:`, an Allow, a missing rule or a reorder refuses). Any exception -> `"rule_set"` (fail closed). Groups for other agents (e.g. Googlebot) do not affect the verdict (R-S16C-1 names QarenBot and '*' only).
- `_run` after the change: the robots read and the unreadable branch are UNCHANGED (fail closed); the existing can_fetch gate stays the first test; ONLY when it refuses: `check = wdqs_exemption_check(body, url)`; check not None -> INFO `"%s robots disallow the query endpoint; nothing read check=%s"` + return 0 (the base text + one suffix, so r24's "robots" assertion holds); check None -> ONE INFO `"%s robots exemption applied ruling=%s doc=%s"` (constants only) and proceed. An ALLOWED body never logs the exemption line (byte-identical to base).
- The SPARQL GET with ONE bounded retry (R-S16C-2): `res = await fetcher.get(url, gate=False, timeout=60.0)`; if `res.status in WDQS_RETRY_STATUSES`: `wait = _retry_wait(res)` = the `Retry-After` header when it is 1-6 ASCII digits, else `_RETRY_IN_RE` on the first 2,000 chars of the body, else the cap; `wait = min(float(n), WDQS_RETRY_CAP_SECONDS)`; ONE INFO `"%s query status=%d; one retry after %ds"`; `await _pause(fetcher, wait)`; ONE more `fetcher.get` (same URL, timeout); still not 2xx -> INFO `"%s query failed status=%d retries=1"` + return 0 (nothing written, the run stops with the logged count). A non-retry status keeps the base line `"%s query failed status=%d"` exactly. Never a loop: at most 3 fetches per run.
- `_pause(fetcher, seconds)`: awaits the fetcher's injected sleep (`fetcher._polite._sleep`, through `robots_registry._maybe_await`), so the Rig records the wait and production uses `asyncio.sleep`; the retry GET itself then waits the Politeness 2.0 s as every non-first request does. Measured consequence for the Rig: an allowed body + 429 + 200 records `sleeps == [2.0, wait, 2.0]`.
- The agent (R-S16C-3): unchanged - every fetch carries `robots_registry._REQUEST_HEADERS` (`QARENBOT_UA`, the project URL and `contact:` mailbox name); pinned, not edited.
- Flag-OFF identity (main invariant): OFF -> zero fetches / sleeps / client calls (s02, P6). ON with any body `can_fetch` allows and a 2xx answer -> byte-identical requests, report, writes and log lines (r23, s03, s04, P4). Changes only on (a) a disallowing body that is exactly the exempt rule set, (b) a 429 / 503 on the SPARQL GET, (c) the refusal line's ` check=<name>` suffix.
- Failure table:

| Input | Base | After |
|---|---|---|
| OFF | one INFO, no I/O | unchanged |
| robots 403 / 5xx / timeout | 1 fetch, "robots unreadable" | unchanged |
| robots 404 / 410 | body "" -> allowed -> GET | unchanged |
| live 95-byte body (the exempt pair for '*') | 1 fetch, refusal | 2 fetches, ONE exemption INFO, report written |
| live + `Disallow: /` / + empty `Disallow:` / reordered / one rule only (r24) | refusal | refusal `check=rule_set` |
| live + `User-agent: QarenBot` group | refusal | refusal `check=named_group` |
| another host or path (helper) | n/a | `"url"` |
| allowed body, SPARQL 429 then 200 | 2 fetches, "query failed status=429" | 3 fetches, one retry INFO, report written |
| allowed body, 429 then 429 (or 503 then 503) | 2 fetches | 3 fetches, "query failed status=429 retries=1", nothing written |
| Retry-After 30 / 999 / HTTP-date | n/a | wait 30 / 120 / the body hint else 120 |
| SPARQL 500 | "query failed status=500" | unchanged (no retry) |

- Seams: `PoliteFetcher` (the Rig), `robots_eval.parse_groups` / `rules_for_agent` / `can_fetch` (read, never patched), the injected sleep.
- Contract freeze: no response, route, stored row or client-read key is touched (an off-clock script); R-A1 n/a (flag-gated); never a bare 503 (no HTTP surface).

### 3. Change list

1. `scripts/seed_kb_brands_wikidata.py`: the constants of 2 after `MAX_BRAND_HOSTS` (with a comment naming the ruling doc and the owner's words "Document exemption"); `wdqs_exemption_check` (pure, after `sparql_url`); `_retry_wait(res)` and `async _pause(fetcher, seconds)`; in `_run` the two hunks of 2 (the gate at :246-248 and the GET at :249-252); one docstring sentence ("S81-16c: the WDQS SPARQL URL is exempt from the query service's robots Disallow only for the exact rule set ruled in docs/policies/2026-11-07-wdqs-robots-exemption.md; one bounded retry on 429 / 503"). Keep: ASCII, no `QarenBot` / `NAMED_AGENT` literal, `ENABLE_KB_BRANDS` in the docstring.
2. NEW `docs/policies/2026-11-07-wdqs-robots-exemption.md` = the docs-branch bytes (sha `9613f9fe...`; copy with `git show docs/session-81-state:<path>` bytes, never retyped).
3. `docs/policies/2026-08-31-robots-unreadable-ruling.md`: ONE line appended at the end (after the "Enforcement surfaces" section, one blank line before): `Exemption (owner ruling 2026-11-07): docs/policies/2026-11-07-wdqs-robots-exemption.md carves out the Wikidata Query Service SPARQL endpoint for scripts/seed_kb_brands_wikidata.py only, under an exact robots rule set; every other host and path keeps this ruling.` (no other edit, R-S16C-6).
4. New `tests/test_s81_s16c_wdqs_exemption.py` (section 5).

### 4. Existing pins

4.1 Deliberate changes: NONE (0 E-rows, R-S16C-1 / R-S16C-5). Measured: r24[disallow]'s fixture is the ONE-rule body (refused by `rule_set`; its assertions - 1 fetch, no write, an INFO with "robots" - hold with the suffix); r24[403] / [timeout] never reach the check.
4.2 Must stay green: `tests/test_s81_s16_kb_seed.py` (r23, r24 x3, r27 hygiene on CI's LF bytes), `tests/test_s81_s16b_kb_brands.py` (S01-S12, PIN1-6; s12 is the constraint list of 1.7), `tests/test_robots_unreadable_ruling.py`, `tests/test_s81_d14_live_robots.py` / `tests/test_s81_s15_registry_robots.py` (robots_eval / robots_registry, untouched), `tests/test_secret_scan_static.py`, `tests/test_hermeticity_pins.py`.

### 5. RED tests: `tests/test_s81_s16c_wdqs_exemption.py`

Hermetic: `import app.main` FIRST in an autouse fixture (the dotenv hazard), `ENABLE_KB_BRANDS` / `ENABLE_KB_SEED` / `KB_BRANDS_MAX` deleted then set per row; the S16 harness by import of the module object (`from tests import test_s81_s16_kb_seed as s16`: `s16.Rig`, `s16._merchant`, `s16._records`, `s16._mod`, `s16._attr`, `s16._brand_bindings`); missing symbols through `s16._attr` (AssertionError, never AttributeError / ImportError); `LIVE_ROBOTS = COMMENT + "User-agent: *\nDisallow: /sparql\nDisallow: /bigdata\n"` with `COMMENT` a synthetic 44-byte ASCII comment line, `assert len(LIVE_ROBOTS.encode()) == 95`; `ALLOWED = "User-agent: *\nAllow: /\n"`; the 429 body `"Too many requests; retry in 120 seconds"`; netguard on; no network; pure ASCII, LF; about 100-130 lines.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_live_body_exempt_two_fetches` | DRY, `[(200,{},LIVE_ROBOTS),(200,{},bindings)]`: rc 0; `len(rig.fetches) == 2` (robots, then the sparql URL); the report has hosts; exactly ONE INFO containing `"robots exemption applied ruling=2026-11-07"` and `WDQS_RULING_DOC`; no write | AssertionError (1 fetch) | 3.1 |
| R2 | `test_r2_slash_and_extra_rules_refuse` | parametrized `LIVE+"Disallow: /\n"`, `LIVE+"Disallow:\n"`, `LIVE+"Allow: /x\n"`: 1 fetch, no write, an INFO ending `check=rule_set` | AssertionError (no `check=`) | 3.1 |
| R3 | `test_r3_qarenbot_group_refuses` | `LIVE + "\nUser-agent: " + rr.NAMED_AGENT + "\nDisallow: /sparql\nDisallow: /bigdata\n"` (the agent name read from the module at run time): 1 fetch, INFO `check=named_group` | AssertionError | 3.1 |
| R4 | `test_r4_helper_url_and_rules` | `wdqs_exemption_check(LIVE, sparql_url())` is None; `(LIVE, "https://www.wikidata.org/w/api.php?action=query")` == "url"; `(LIVE, "https://query.wikidata.org/bigdata/namespace/wdq/sparql")` == "url"; `(LIVE, "http://query.wikidata.org/sparql")` == "url"; `(LIVE with /bigdata first, sparql_url())` == "rule_set"; `(r24 one-rule body, ...)` == "rule_set" | AssertionError (`_attr` missing) | 3.1 |
| R5 | `test_r5_429_then_200_one_retry` | ALLOWED robots, SPARQL `(429, {}, RETRY_BODY)` then `(200,{},bindings)`: 3 fetches (the last two the same URL); `rig.sleeps == [2.0, 120.0, 2.0]`; report written; one INFO `"one retry after 120s"` | AssertionError (2 fetches) | 3.1 |
| R6 | `test_r6_429_twice_gives_up` | `(429,..)` twice: 3 fetches, nothing written, no report file, one INFO `"query failed status=429 retries=1"`, rc 0 | AssertionError | 3.1 |
| R7 | `test_r7_retry_after_header_and_cap` | parametrized (503, `{"Retry-After": "30"}`) -> wait 30.0; (429, `{"Retry-After": "999"}`) -> 120.0; (429, `{"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}`, RETRY_BODY "retry in 45 seconds") -> 45.0: `rig.sleeps[1]` equals the wait | AssertionError | 3.1 |
| R8 | `test_r8_exemption_only_in_this_script` | the marker `WDQS_RULING_DOC`'s file name appears in exactly ONE file under app/ + scripts/ (`scripts/seed_kb_brands_wikidata.py`, CRLF-normalised read); `git`-free: the LF-normalised sha256 of `app/services/robots_eval.py` == `bb584acb...` and of `scripts/kb_seed_common.py` == `afc8288e...`; the script source has no `"QarenBot"` literal (s12 restated) | AssertionError (0 files) | 3.1 |
| P1 | `test_p1_r24_shapes_still_refuse` | the three r24 first responses: 1 fetch, no write, an INFO with "robots" | green | base |
| P2 | `test_p2_reordered_and_named_bodies_refuse` | LIVE reordered; LIVE + QarenBot group: 1 fetch, no write (no `check=` assertion) | green | base |
| P3 | `test_p3_unreadable_fail_closed` | robots 403 / 500 / TimeoutError: 1 fetch, "robots unreadable" INFO | green | base |
| P4 | `test_p4_allowed_body_byte_identical` | ALLOWED + 200: 2 fetches, `sleeps == [2.0]`, every fetch `headers == rr._REQUEST_HEADERS` with `rr.QARENBOT_UA` in the User-Agent and "contact:" in it, `allow_redirects is False`; no INFO containing "exemption" or "retry" | green | base |
| P5 | `test_p5_non_retry_failure_line` | ALLOWED + SPARQL 500: 2 fetches, exactly one INFO `"[KB_BRANDS] query failed status=500"` (no `retries=`) | green | base |
| P6 | `test_p6_off_inert` | each OFF spelling (`None, "", "false", "0", "off", "dry"`): 0 fetches / sleeps / client factory calls | green | base |

Counts: RED 8 (12 nodes), PIN 6.

### 6. Mutation table (byte copies, `.qa-mutation.lock`, `pyt.py -k`, bound 600 each)

| M | Mutation | Killed by |
|---|---|---|
| M1 | the url check removed (any URL exempt) | R4 |
| M2 | the named-group check removed | R3 |
| M3 | rule-set equality relaxed to "every rule is in the pair" | R2 (`Disallow:` / missing rule cases via R4 one-rule body) |
| M4 | order-insensitive comparison | R4 (reordered == "rule_set") |
| M5 | only the QarenBot rule set compared (not '*') | R4 (a body with a `*` Allow added still refused? the R2 `Allow: /x` row) |
| M6 | no retry | R5 |
| M7 | two retries (a loop) | R6 (3 fetches) |
| M8 | the cap removed | R7 (999) |
| M9 | Retry-After ignored | R7 (30) |
| M10 | retry on 500 too | P5 |
| M11 | the exemption line logged on an allowed body | P4 |
| M12 | the refusal suffix dropped | R2 / R3 |

### 7. Comm set
The group's (section 12.1). 16c's own reach: the importers of `scripts.seed_kb_brands_wikidata` (`test_s81_s16_kb_seed`, `test_s81_s16b_kb_brands`), the scripts/ walkers and the source-scanning pins (`test_secret_scan_static`, `test_hermeticity_pins`, `test_s81_kb_schema`), all inside 12.1. No client fence reads the script, robots_eval's bytes (they read robots_eval by NAME only, the G8 measurement) or docs/policies.

### 8. CLAUDE.md row and owner steps
Row (inside the G9 block): `- S81-16c WDQS-EXEMPTION (no new flag; rides ENABLE_KB_BRANDS, unset in production): scripts/seed_kb_brands_wikidata.py proceeds past the query service's robots Disallow ONLY for its one SPARQL URL and ONLY when the parsed rule sets for the named agent and '*' are exactly (Disallow /sparql, Disallow /bigdata) with no named group (wdqs_exemption_check; any other rule, Disallow: /, a named group or another URL refuses, the INFO line names the check; an unreadable robots.txt stays fail-closed); ONE bounded retry on 429 / 503 (Retry-After, else the body's "retry in N seconds", capped at 120 s, never a loop); the ruling doc docs/policies/2026-11-07-wdqs-robots-exemption.md (the owner's "Document exemption", 2026-11-07); robots_eval.py untouched. RED tests/test_s81_s16c_wdqs_exemption.py.`
In place: CLAUDE.md:550 (the G2 block's brand-script sentence, which is where the S81-16b brand text lives at base; there is no separate S81-16b heading) gains after "it reads the query service's robots.txt" the clause "(the SPARQL URL is exempt from its Disallow only under the exact rule set of docs/policies/2026-11-07-wdqs-robots-exemption.md, S81-G9 S81-16c)".
Owner steps (names only): after the merge, the owner-approved DRY run (`ENABLE_KB_BRANDS=true` in the command's own environment through railway run; expect about 342 brands, bindings about 430, hosts capped at 300), then `ENABLE_KB_BRANDS=apply`, then the kb_brands count (R-S16C-8).

### 9. Stated limits
- L-S16c-1 (R-S16C-7): Arabic labels cover 38 of 342 brands; 379 hosts exceed `MAX_BRAND_HOSTS = 300` (the cap trims; a cap change is its own ruling); gzip Accept-Encoding is absent from `_REQUEST_HEADERS` (a separate app/ item).
- L-S16c-2: the exact live robots bytes are not in the repo; the RED body is a synthetic 95-byte shape (the comment text is irrelevant to the parser, which strips comments); a live file that adds any rule refuses until a new ruling.
- L-S16c-3: the retry wait rides the fetcher's private `_polite._sleep` (no kb_seed_common edit, its watch patterns); a refactor of PoliteFetcher must keep it or the RED R5 / R7 rows go red (they would, loudly).
- L-S16c-4: the retry adds the Politeness 2 s before the second GET (total wait = hint + 2 s).
- L-S16c-5: the QarenBot UA's 429 behaviour at WDQS is unmeasured (only Python-urllib was observed: a first-request 429 with "retry in 120 seconds"); no live request is made by this unit (R-S16C-8).

### 10. Out of scope
Any robots_eval / robots_registry / kb_seed_common change; the Action API path (rejected by the owner's pick); a cap change; gzip; www.wikidata.org.

### 11. Open questions
- Q-16c-1: order-sensitive rule comparison (default YES: a reorder refuses, fail closed) or order-insensitive (P2 / R4 / M4 flip)?
- Q-16c-2: with neither Retry-After nor a body hint, wait the cap (default) or give up without a retry?
- Q-16c-3: a hint above the cap: wait the cap and retry (default, the ruling's "the wait capped") or give up?

---

## Unit D17c COVERAGE-EMPTY-HOSTS

### 1. Base state (measured at 39ac80ba)

| # | Site | Measured |
|---|---|---|
| 1.1 | `scripts/cron_kb_coverage.py:281-320` `_Rollup._hosts` | `if self.redis is None: return` (:282-283); the registry read guarded as family "registry" (:284-286); `hosts = sorted({host for live / blocked rows})[:max_hosts()]` (:287-288, `KB_COVERAGE_MAX_HOSTS` 500 clamped 1..5000, :57-59); `read()` (:291-298) builds `pipe = self.redis.pipeline()`, one `pipe.hgetall("kbh:" + YYYYMMDD + ":" + host)` per host, then `run = getattr(pipe, "exec", None) or getattr(pipe, "execute")` (the D17b fallback) and `list(run() or [])`; `result = self.guarded("hosts", read)` (:300); None -> return (:301-302); `self.redis_read = 1` (:303); per host an empty / non-dict hash emits nothing (:304-306), else `host.robots_skip:<host>` / `host.challenge:<host>` (:319-320). NO empty-list guard: 0 hosts still builds and runs a pipeline. |
| 1.2 | `:145-151` `guarded(label, fn)` | any exception -> ONE `logger.warning("%s family=%s read failed (%s)", PREFIX, label, type(exc).__name__)`, returns None; no exc_info, no traceback. Nothing counts the failure. |
| 1.3 | `:343-389` `main` | mode FIRST (`common.run_mode("ENABLE_KB_COVERAGE_ROLLUP")`), argparse, day, client, `redis = _default_redis()` (`cache_service.redis_client`, :334-340), `rollup.run()`, one INFO per metric, `not_built` = builder refusals only, `_write_report`, APPLY = ONE upsert, then `"%s totals rows=%d not_built=%d skipped_long=%d redis=%d"` (:387-388). Frozen regex `TOTALS_LINE = ^\[KB_COVERAGE\] totals rows=\d+ not_built=\d+ skipped_long=\d+ redis=[01]$` (`tests/test_s81_d17_coverage.py:49`): no new totals field may be added. |
| 1.4 | upstash-redis 1.7.0 (`requirements.txt:202`; `.venv-qaren/Lib/site-packages/upstash_redis/`) | `Redis.pipeline()` (`client.py:149-160`) -> `Pipeline` with `self._url = f"{url}/{multi_exec}"` = `<url>/pipeline` (:186); `hgetall(key)` (`commands.py:1718`) -> `execute(["HGETALL", key])`, which on a Pipeline only QUEUES and returns the pipeline (`client.py:200-208`); `exec()` (:210-228) posts the stack through `SyncHttpClient.execute(..., from_pipeline=True)`; `http.py:70` `self._client.post(url, json=command)` with `httpx.Client(timeout=None)` (:54), `response = r.json()` (:75) WITHOUT a status check, then `[format_response(sub) for sub in response]` (:93-94); `format_response` (:183-195) does `response.get("error")` (:191). So a whole-request error body (a JSON OBJECT such as `{"error": "..."}`, which is what a 400 carries) is iterated key by key and `str.get` raises `AttributeError: 'str' object has no attribute 'get'` at `http.py:191`. An absent hash answers `{"result": []}` -> `to_dict([])` -> `{}` (`format.py:15-20`). |
| 1.5 | measured probe (`<scratchpad>/g9spec/probe_d17c.py`: the real `Redis(url="https://fake-upstash.invalid", token="t", rest_retries=0)` with `_http._client` replaced by `httpx.Client(transport=httpx.MockTransport(...))`, the real `_Rollup._hosts`) | 0 hosts: ONE POST to `<url>/pipeline`, body `[]` (2 bytes). 1 host: body `[["HGETALL","kbh:20261106:h000.example.com"]]` (45 bytes), headers authorization / upstash-encoding / upstash-sync-token / telemetry (names only). 318 hosts: 13,993 bytes; 410 hosts: 18,041 bytes; one POST each, commands in sorted host order. Every case with a 400 `{"error": ...}` answer: `WARNING [KB_COVERAGE] family=hosts read failed (AttributeError)`, `redis_read 0`, no metric - EXACTLY the production log. With a 200 list answer: `redis_read 1`. |
| 1.6 | the root cause (measured + the ledger timestamps) | The SDK posts an empty stack unconditionally; the request the script builds for 0 hosts is the empty pipeline `[]`; Upstash rejects that whole request (the 400; its reason text is unmeasured offline) and the SDK turns the error object into the AttributeError of 1.4. BOTH failing production runs had 0 hosts: the 21:05 run (kb_merchants empty, ledger.md:307) and the scheduled 01:20Z run of 2026-11-07, which ran BEFORE the seed apply (the seed is stamped 06:24 by the ops clock, ledger.md:317, and the ops stamps are AST = Z+3 by the robots cron's own pair "06:27:33" / "03:27:33Z", ledger.md OWNER_OPS:89 / :119, i.e. about 03:24Z): the "with the 410 seeded merchants" reading of the 09:00 line (ledger.md:335) contradicts the timestamps. The first run WITH hosts (the 07:04Z redeploy, 318 live + blocked hosts) read the family cleanly (`redis=1`, ledger.md:355). So the failure is deterministic on an empty host list, not transient (the 10:09 note's "transient" premise, ledger.md:357, is the open question Q-D17c-1). A non-empty body is the SDK's documented shape (1.5); no size limit is implied by the measurement (500 hosts at most, about 22 KB). |
| 1.7 | D17d / D16c (the 10:05 widening: the processes not exiting) | measured (`<scratchpad>/g9spec/probe_exit.py`, `python -I`, every UPSTASH / SUPABASE / ENABLE_ name removed, a chain fake client): `cron_kb_coverage.main` DRY with the SDK client on a 400 transport -> the WARNING + `totals rows=10 not_built=0 skipped_long=0 redis=0` (the production line), rc 0, 1.59 s, threads alive besides MainThread `[]`; with `redis=None` (cache_service, no Upstash env) rc 0, `[]`; `cron_kb_enrich.main` DRY rc 0, 0.09 s, `[]`; every process exited (bounded by `timeout 120`). Also measured: `cron_kb_enrich.main` DRY returns after `dry_run` WITHOUT any totals line by design (`scripts/cron_kb_enrich.py:661-666`; the totals line is APPLY-only, :676), so "no `[KB_ENRICH] totals` line" (ledger.md:351) is not evidence of a hang; and the 01:20Z coverage run logged the proxy metrics (ledger.md:335), which come AFTER the hints metrics in `rollup.out`, so the "log ends after the kb.hints metrics" reading is a log-ingestion artefact. No non-daemon thread or executor is left by either script locally. |
| 1.8 | frozen rows | `tests/test_s81_d17_coverage.py` (R1-R9; R5: one `("pipeline",)` call with hosts present; R8: a raising read -> WARNINGs with the type name, `TOTALS_LINE`; R9 hygiene) and `tests/test_s81_d17b_coverage_paging.py` (R3 redis-py execute; P1 upstash exec once, the one-argument execute never). No frozen row runs the hosts family with 0 hosts and a present Redis, and none asserts `not_built` on a family failure. |
| 1.9 | flag / libraries | mode idiom read FIRST per call (`common.run_mode`); `.venv-qaren` upstash-redis 1.7.0, httpx (MockTransport is in the installed httpx). |
| 1.10 | base pass state | inside `g9spec-base-pins`: test_s81_d17_coverage (r9 CRLF-red only), test_s81_d17b_coverage_paging (green), test_s81_kb_schema (green). |

### 2. Contract

- Flag: `ENABLE_KB_COVERAGE_ROLLUP` (existing). OFF byte-identical (one env read, one INFO, return). NOTE: `apply` on kb-coverage in production since the 11:20 ops line, so this unit changes the NEXT scheduled run's behaviour on that service (only on the two edge paths below); the owner's 2026-11-08 01:20Z apply pass will be the first live read.
- 0 hosts (Redis present, the registry read ok, no live / blocked host): NO `pipeline()` call, no POST; ONE INFO `"%s family=hosts skipped hosts=0"`; `redis_read` stays 0; `not_built` unchanged (a skip is not a failure); no host metric.
- N >= 1 hosts: unchanged request (one pipeline, the sorted HGETALL list, exec-then-execute); unchanged metrics.
- The error path: when the hosts family's read raises, `self.families_not_built += 1` (a new int attribute, 0 at construction) and `main` adds it to `not_built` before the totals line (the totals line keeps its frozen shape; `not_built` now = builder refusals + failed hosts family); the WARNING keeps its template `"%s family=hosts read failed (%s)"`, with the label `pipeline_refused` (constant `PIPELINE_REFUSED`) when the raise is the SDK's AttributeError from the exec call (the measured signature of a whole-request error, 1.4), else the exception type name as today. Never raised, never exc_info / a traceback.
- Other families (products / offers / variants / images / specs / reviews / gaps / proxy / registry): unchanged (WARNING only, not counted) unless Q-D17c-2 rules all families.
- D17d: no code change (1.7); two PIN rows hold the exit guarantee.
- Flag-OFF identity: OFF unchanged. ON with N >= 1 hosts and a healthy answer: byte-identical lines, report and upsert (R5, P1-P3 of D17, P1 of D17b).
- Failure table:

| Input | Base | After |
|---|---|---|
| OFF | one INFO | unchanged |
| Redis None | no host family, redis=0 | unchanged |
| 0 hosts, Redis present | 1 POST `[]`, 400, WARNING (AttributeError), not_built 0 | 0 POST, INFO skipped hosts=0, not_built 0, no WARNING |
| N hosts, 200 | metrics, redis=1 | unchanged |
| N hosts, 400 error object | WARNING (AttributeError), not_built 0 | WARNING (pipeline_refused), not_built +1 |
| N hosts, exec raises RuntimeError | WARNING (RuntimeError), not_built 0 | WARNING (RuntimeError), not_built +1 |
| registry read raises | WARNING family=registry | unchanged |

- Seams: the Redis object passed to `main(redis=...)` (the SDK on MockTransport, or the D17 `_Redis` fake), the client fake.
- Contract freeze: no API surface; the kb_coverage_daily rows are built by `build_coverage_row` as before.

### 3. Change list

1. `scripts/cron_kb_coverage.py`: `PIPELINE_REFUSED = "pipeline_refused"` after `SHARE_PLACES`; `_Rollup.__init__` gains `self.families_not_built = 0`; `_hosts`: after `hosts = ...` the 0-host skip (INFO + return before `read`); `read()` wraps only the `run()` call: `except AttributeError as exc: raise _PipelineRefused() from None` (a module-private `class _PipelineRefused(RuntimeError)` whose WARNING label is `PIPELINE_REFUSED`); the guarded call for "hosts" increments `families_not_built` on a None result from a raise (a small `guarded(..., count=True)` keyword or an explicit try in `_hosts`; the GREEN picks the narrower); `main`: `not_built += rollup.families_not_built` before the totals line; one docstring sentence ("D17c: 0 live / blocked hosts skip the pipeline (an empty pipeline is a whole-request error at the REST endpoint); a failed hosts read counts as not_built").
2. New `tests/test_s81_d17c_coverage_hosts.py` (section 5).

### 4. Existing pins
4.1 Deliberate changes: none (R8 asserts only `TOTALS_LINE` and type names on the specs family, unaffected; R5 has hosts).
4.2 Must stay green: `tests/test_s81_d17_coverage.py`, `tests/test_s81_d17b_coverage_paging.py`, `tests/test_s81_kb_schema.py`, `tests/test_s81_d22_nightly_learning.py`, `tests/test_s81_d16_operator_ingest.py`, `tests/test_s81_s17_kb_ingest.py` (coverage readers), `tests/test_s81_s19_gap_queue.py` (the enrich script, untouched).

### 5. RED tests: `tests/test_s81_d17c_coverage_hosts.py`

Hermetic: `import app.main` first; the D17 harness by module import (`from tests import test_s81_d17_coverage as d17`: `d17._Client`, `d17._tables`, `d17._merchant`, `d17._Redis`, `d17.TOTALS_LINE`, `d17.FLAG`, `d17.HOST_A`); the real `upstash_redis.Redis` with a `MockTransport` recorder (url, json body) - no socket (netguard on); synthetic hosts; pure ASCII, LF.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_zero_hosts_no_pipeline_sdk` | DRY, kb_merchants = one candidate row, the SDK client whose transport answers 400 `{"error":"ERR synthetic"}`: 0 POSTs; ONE INFO `"[KB_COVERAGE] family=hosts skipped hosts=0"`; no WARNING; totals `redis=0` and `not_built=0`; rc 0 | AssertionError (1 POST) | 3.1 |
| R2 | `test_r2_zero_hosts_no_pipeline_fake` | the D17 `_Redis` fake, kb_merchants empty: no `("pipeline",)` call | AssertionError | 3.1 |
| R3 | `test_r3_400_counts_the_family` | one live host, transport 400: ONE WARNING `"family=hosts read failed (pipeline_refused)"`; totals `not_built=1`; no host metric; no record with exc_info; rc 0 | AssertionError (not_built=0) | 3.1 |
| R4 | `test_r4_exec_raise_counts_the_family` | a fake pipeline whose `exec` raises RuntimeError: WARNING `(RuntimeError)`, `not_built=1` | AssertionError | 3.1 |
| P1 | `test_p1_one_host_body_shape` | one host, transport 200 `[{"result": []}]`: exactly 1 POST, url ends `/pipeline`, json body `[["HGETALL","kbh:20261101:" + host]]`; no host metric (absent hash); `redis=1` | green | base |
| P2 | `test_p2_410_hosts_one_pipeline` | 410 synthetic live hosts (`h000..h409.example.com`), 200 answer with one non-empty hash for `h000` (`["curl:robots_skip","3","curl:fetch","5"]` base64-free with `rest_encoding=None`): ONE POST of 410 sorted HGETALL commands; `host.robots_skip:h000.example.com` value 3 n 8; `redis=1` | green | base |
| P3 | `test_p3_report_and_totals_shape` | the seeded D17 run: `TOTALS_LINE` matches, the report header `| metric | value | n |` | green | base |
| P4 | `test_p4_coverage_process_exits` | `subprocess.run([sys.executable, "-I", "-c", <driver>], timeout=60)` with a scrubbed env (no UPSTASH / SUPABASE / ENABLE_ names, the flag "true"): the driver runs `cron_kb_coverage.main` with a chain fake client and the SDK on a 400 MockTransport and prints the non-main thread names: rc 0, output `threads=[]` | green | base |
| P5 | `test_p5_enrich_process_exits` | the same for `cron_kb_enrich.main` DRY with the chain fake: rc 0, `threads=[]` | green | base |

Counts: RED 4, PIN 5.

### 6. Mutation table

| M | Mutation | Killed by |
|---|---|---|
| M1 | the 0-host guard removed | R1, R2 |
| M2 | guard `len(hosts) <= 1` | P1 |
| M3 | the family not counted | R3, R4 |
| M4 | counted per host (`+= len(hosts)`) | P2 run with a 400? -> R3 (exactly 1 with one host) and a two-host variant of R3 (param) |
| M5 | the skip counts as not_built | R1 (`not_built=0`) |
| M6 | the label applied to every exception | R4 (`RuntimeError`) |
| M7 | skip line omitted | R1 |

### 7. Comm set: the group's (12.1); D17c's own reach = the cron_kb_coverage importers + the coverage readers of 4.2.

### 8. CLAUDE.md row
`- D17c COVERAGE-EMPTY-HOSTS (no new flag; rides ENABLE_KB_COVERAGE_ROLLUP): scripts/cron_kb_coverage.py skips the hosts family when the registry holds no live / blocked host (one INFO "family=hosts skipped hosts=0", no pipeline: the empty pipeline [] the pinned upstash-redis 1.7.0 posted is rejected by the REST endpoint and the SDK raises AttributeError on the error object, http.py:191), and a failed hosts read now counts in the totals not_built with one constants-only WARNING (pipeline_refused for that SDK signature); a non-empty host pipeline is unchanged. D17d / D16c: both cron scripts exit with no thread left (PIN rows; the 'running' Railway bookings are not reproduced locally). RED tests/test_s81_d17c_coverage_hosts.py.`
In place: CLAUDE.md:562 (the D17 row) after "read with ONE HGETALL pipeline" adds "(skipped with zero hosts since S81-G9 D17c)".
Owner steps: none to merge; the next scheduled kb-coverage pass (apply since the 11:20 ops line) reads `redis=1` with the 318 hosts; watch `not_built` in its totals line.

### 9. Stated limits
- L-D17c-1: proven against the pinned SDK's request shape and the recorded production lines, not against Upstash itself (its 400 reason text is unmeasured); the next scheduled run is the live read.
- L-D17c-2: the SDK still reads a non-2xx body without a status check; any other whole-request error (auth, quota) also surfaces as `pipeline_refused`.
- L-D17c-3: no chunking: at most `KB_COVERAGE_MAX_HOSTS` (500) commands, about 22 KB; a larger registry needs the knob or a chunk unit.
- L-D17c-4 (D17d): the stuck Railway bookings are not reproduced; the PIN rows prove the scripts exit locally with fakes, not the platform bookkeeping.

### 10. Out of scope: the SDK, cache_service, kb_seed_common, the enrich script's code, the other families' counting (unless Q-D17c-2).

### 11. Open questions
- Q-D17c-1: the 10:09 note calls the 400 transient; the timestamps put both failing runs at 0 hosts (1.6). Rule the root cause as the empty pipeline (default) and keep the error-path counting as the second half?
- Q-D17c-2: count every failed family in `not_built` (one line in `guarded`; R8 still matches) or the hosts family only (default, the brief's text)?
- Q-D17c-3: the `pipeline_refused` label (default) or keep the type name `AttributeError` unchanged?

---

## Unit S81-22d LEDGER-PINS-FLAG-SAFE

### 1. Base state (measured at 39ac80ba)

| # | Site | Measured |
|---|---|---|
| 1.1 | `tests/test_s81_s03_llm_ledger_v2.py` (2,881 lines; LF blob sha256 `7732fa24c9047a0faf78d608cc97902ee6575d3c21661691eb7f56c12d4d4f5b`; working copy CRLF `106c7fcb...`) | `UNIT_ENV` (:102-120) is deleted by the autouse `_unit_env` (:218-223) and does NOT name `ENABLE_COMPARE_RUN_LEDGER`; `_leaf_recorders` (:260-275) wraps every function defined in `app.services.llm_pricing` except the flag reader; `_called` (:278-279); `_prime_leaf_state` (:334-348); `_isolated` (:304-307). |
| 1.2 | the rows | `test_i2_camera_flag_off_no_metadata_llm[false/None]` (:2438-2453; `assert not _called(calls)` at :2451) and `test_i6_off_camera_real_compare_total_cost_is_base[None/false]` (:2726-2742; :2741). `test_i6_camera_real_compare_total_cost_and_llm_mirror_openai` (:2702-2724, ledger V2 ON) does not count leaf calls. |
| 1.3 | measured, the whole file with `ENABLE_COMPARE_RUN_LEDGER=true` in the runner call | exactly 4 nodes fail, all AssertionError on `_called`: i2 x2 `{'_count_ok': 9, 'price_call': 1, 'current_openai_ledger': 1, 'current_llm_records': 1, ...}`, i6-off x2 `{'_count_ok': 108, 'price_call': 12, ...}` (compare_runs reads the ledger through `llm_pricing`: `app/services/compare_runs.py:253-273`). No sibling row of the 18 `_leaf_recorders` users fails. i1 / i3 / i4 / i5 log neutralized `supabase.invalid` connects (the compare_runs row write, netguard) and pass. Unset: 215 passed. |
| 1.4 | the flag | `compare_runs.compare_run_ledger_enabled()` (:82) reads `ENABLE_COMPARE_RUN_LEDGER` per call (the house truthy set); unset / "false" = OFF. |
| 1.5 | other pins on the file | `test_l1_fy25_unit_env_carries_the_flag` (:2522) reads another file's UNIT_ENV; nothing reads this file's source; no test imports it (grep). |
| 1.10 | base pass state | `g9spec-s03-unset` 215 passed; `g9spec-s03-exported` 4 failed / 211 passed (section 0). |

### 2. Contract
- No flag, no app/ change, no knob. The two rows delete `ENABLE_COMPARE_RUN_LEDGER` at their start (the ambient-environment rule), so their counted-leaf assertion is evaluated with the ledger OFF whatever the runner exports; every other row byte-identical.
- Flag-OFF identity: n/a (test-only); the CI state (flag unset) is unchanged.

### 3. Change list
1. EK1 (deliberate, ruled here; the narrowest edit): in `test_i2_camera_flag_off_no_metadata_llm` and in `test_i6_off_camera_real_compare_total_cost_is_base`, ONE added line each as the first statement of the test function (before `def body():`): `monkeypatch.delenv("ENABLE_COMPARE_RUN_LEDGER", raising=False)  # S81-22d: the ledger row reads llm_pricing; these OFF pins count leaf calls`. Two lines added, 0 removed; CRLF kept; the new LF blob sha recorded in the GREEN report.
2. New `tests/test_s81_s22d_ledger_pins.py`.

### 4. Existing pins
4.1 Deliberate: EK1 above (2 rows, 4 nodes). The S81-22 frozen files (`tests/test_s81_s22_compare_runs.py`, `test_s81_s22_judge.py`, `test_s81_s22_gate_rows.py`) untouched.
4.2 Must stay green: the whole S03 file in both runner states; `tests/test_s81_s22_*`; `tests/test_s75_fanout_identity.py`.

### 5. RED tests: `tests/test_s81_s22d_ledger_pins.py`
Hermetic: `from tests import test_s81_s03_llm_ledger_v2 as s03` (module object; its rows are not collected twice); an autouse fixture replays `s03._unit_env` (delete `s03.UNIT_ENV`, `s03.limiter.enabled = False` through monkeypatch); `LEDGER_FLAG = "ENABLE_COMPARE_RUN_LEDGER"`; pure ASCII, LF.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_rows_name_the_flag` | AST of the S03 source (CRLF-normalised): the bodies of `test_i2_camera_flag_off_no_metadata_llm` and `test_i6_off_camera_real_compare_total_cost_is_base` each contain a `monkeypatch.delenv` (or `setenv(..., "false")`) call whose first argument is the literal `ENABLE_COMPARE_RUN_LEDGER`, before any other statement that reads the env | AssertionError | EK1 |
| R2 | `test_r2_rows_green_with_flag_exported` | parametrized over the 4 nodes: `monkeypatch.setenv(LEDGER_FLAG, "true")`, then call the S03 row function directly (`s03.test_i2_camera_flag_off_no_metadata_llm(monkeypatch, flag)` / the i6-off one) | AssertionError (raised inside the row by `_called`) | EK1 |
| R3 | `test_r3_flag_named_only_in_the_two_rows` | the literal `ENABLE_COMPARE_RUN_LEDGER` occurs exactly twice in the S03 file, both inside those two functions | AssertionError (0) | EK1 |
| P1 | `test_p1_rows_green_with_flag_unset` | the 4 nodes with the flag deleted | green | base |
| P2 | `test_p2_s22_frozen_files_unchanged` | the LF-normalised sha256 of `tests/test_s81_s22_compare_runs.py`, `test_s81_s22_judge.py`, `test_s81_s22_gate_rows.py` equal their base values (recorded by the RED agent from `git show <base>:<path>`) | green | base |

Gate: the RED file and the S03 file through pyt.py twice, unset and with `ENABLE_COMPARE_RUN_LEDGER=true` in the runner call only (both 0 failed at GREEN).

### 6. Mutation table
| M | Mutation | Killed by |
|---|---|---|
| M1 | EK1 in i2 only | R1, R2 (i6-off nodes) |
| M2 | the flag added to `UNIT_ENV` instead | R1, R3 |
| M3 | `setenv(LEDGER_FLAG, "true")` in the rows | P1 |

### 7. Comm set: the group's; 22d's reach = the S03 file + the RED file (no importer of the S03 module).

### 8. CLAUDE.md row
`- S81-22d LEDGER-PINS-FLAG-SAFE (no flag; test-only): the S81-03 isolation rows test_i2_camera_flag_off_no_metadata_llm and test_i6_off_camera_real_compare_total_cost_is_base delete ENABLE_COMPARE_RUN_LEDGER at their start (E-row EK1), so they are green with the flag exported or unset; a flip precondition of ENABLE_COMPARE_RUN_LEDGER is MET. RED tests/test_s81_s22d_ledger_pins.py.`
In place: the S81-22 block's L-I2I6 sentence (CLAUDE.md:605) becomes "L-I2I6: closed by S81-G9 S81-22d (the two rows delete the flag; green in both states)."; the S81-22 owner step naming S81-22d as a precondition (CLAUDE.md:608, the clause naming S81-22d) gains "(met, S81-G9)".
Owner steps: none.

### 9. Stated limits
- L-S22d-1: the rows prove the OFF ledger's leaf silence only; the ON ledger's own reads are pinned by the S81-22 files.

### 10. Out of scope: app/, the S81-22 files, the other 16 `_leaf_recorders` rows (measured green exported).

### 11. Open questions
- Q-22d-1: siblings: none found by measurement (1.3); confirm no widening.

---

## Unit S81-23b SCRAPEDO-SUPER-RETIRE

### 1. Base state (measured at 39ac80ba)

| # | Site | Measured |
|---|---|---|
| 1.1 | `app/services/scrapedo_service.py` (221 lines; LF blob sha via the GREEN) | module docstring :1-8 names the legacy transition; the comment :42-57; `_SUPER_FLAGS = None` :55; `_SCRAPEDO_SUPER_TRUTHY` :57; `scrapedo_super_enabled()` :60-71: `raw = os.getenv("ENABLE_SCRAPEDO_SUPER")`; `if raw is None: return os.environ.get("SCRAPEDO_SUPER", "false").lower() == "true"` (:69-70, THE legacy branch); else `raw.strip().lower() in _SCRAPEDO_SUPER_TRUTHY`; `_super_params()` :74-83 (`{}` or `{"super":"true","geoCode": SCRAPEDO_GEOCODE or "bh"}`); `_super_enabled()` :86-91 delegates; `reset_super_flags_cache()` :94-98 (no-op hook). Callers: `render_page` / `render_page_with_status` through `_super_params`; `app/services/source_router.py:807-818` `_super_routing_enabled` -> `_super_enabled` (gates the lone `requires_super` row, sephora.me, :843). |
| 1.2 | the grep of the legacy name over app/ and scripts/ (and the tracked tree) | code readers: ONLY `scrapedo_service.py:70`. Writers: `scripts/ab_render_providers.py:18` `os.environ["SCRAPEDO_SUPER"] = "true"` (+ the comment :33; a manual off-clock A/B, no test reads it) and the tracked `.qa-bias-rerun/_sephora_provider_test.py:64` (outside app/ and scripts/; `tests/test_sephora_provider_test_classify.py:159` pins only that the harness import sets it in its own process). Comments / docs only: `source_router.py:63, :203, :207, :809, :837`, `structured_comparison_service.py:130`, `docs/contracts/bahrain-source-matrix.md`, the 2026-06 plans, CLAUDE.md :141 / :540 / :541. |
| 1.3 | measured prototype (the post-change reader patched in per test, `g9spec-s23b-proto2`) | 12 of 925 nodes red: `tests/test_fragrance_content_quality.py::test_scrapedo_super_on_adds_super_and_geocode`, `::test_scrapedo_super_on_render_page_also_gated`, `::test_g2_super_sources_routed_render_only_when_flag_on`, `::test_wave4_sephora_me_on_state_routed_render_only_all_categories`; `tests/test_s81_s23_bypass_retire.py::test_s23_r3_per_call_no_reset`, `::test_s23_p1_unset_matches_base_params[true]`, `[TRUE]`, `::test_s23_p2_unset_matches_base_routing[true]`, `[TRUE]`, `::test_s23_p3_reset_hook_callable`, `::test_s23_p4_geocode_default`; plus the base CRLF `test_s81_s19_gap_queue.py::test_r15_hygiene`. Measured too: `::test_g2_off_state_equals_on_state_minus_super_sources` (:1004-1015), `::test_wave4_sephora_me_off_equals_on_minus_super_each_category` (:1091-1105) and `::test_g2_boutiqaat_routed_super_independent_after_reverify` (:1018-1046, `for flag in ({}, {"SCRAPEDO_SUPER": "true"})` at :1025) stay GREEN but become vacuous (their "ON" state sets only the legacy name). |
| 1.4 | the corpus gate at base (`scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP`, the pinned venv, 10:05:10-10:12:21) | `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c` (`<scratchpad>/g9spec/corpus_base.{txt,json}`). Prototype HEAD (the same run through `<scratchpad>/g9spec/corpus_proto.py`, the post-change reader patched in with a call counter, no file edited): the SAME digest `cce256e1...`, reader calls = 0. So EQUAL, and the gate never reaches the reader (`extract_price_from_html` does not call it): the gate proves no collateral change of the extraction spine; the behaviour is proven by the RED / PIN rows. |
| 1.5 | production | both names unset on web and price-warmer since 09:02 (ledger.md:333; 0 occurrences by name); the other services carry only Supabase / Upstash references. So in production the reader returns False before AND after: byte-identical (R-A1 (c)). |
| 1.10 | base pass state | `g9spec-s23b-base` 924 passed / 1 CRLF failure. |

### 2. Contract
- No flag (R-A1 (c): byte-identical on every response and row in the production state, proven by the corpus gate EQUAL + P2 + the measured production state). `ENABLE_SCRAPEDO_SUPER` keeps its semantics when SET (house idiom); UNSET now means OFF for every value of the legacy name.
- `scrapedo_super_enabled()` after: `raw = os.getenv("ENABLE_SCRAPEDO_SUPER"); if raw is None: return False; return raw.strip().lower() in _SCRAPEDO_SUPER_TRUTHY`. The legacy name is read nowhere in app/ or scripts/. `_super_params`, `_super_enabled`, `reset_super_flags_cache`, `_SUPER_FLAGS` unchanged.
- Failure table:

| Input (ENABLE_SCRAPEDO_SUPER / SCRAPEDO_SUPER) | Base | After |
|---|---|---|
| unset / unset (production) | OFF | OFF |
| unset / "true" or "TRUE" | ON | OFF |
| "true" / any | ON | ON |
| "false" / "true" | OFF | OFF |

- Flag-OFF identity: the production row of the table; the request params stay `{token, url, render:"true"}` and the routing the base "off" lists.
- Contract freeze: no response key; Scrape.do request params and the routed source list in the production state unchanged.

### 3. Change list
1. `app/services/scrapedo_service.py`: delete the `if raw is None:` legacy return (:69-70) and return False; rewrite the docstring sentence :4-7 ("it runs only when ENABLE_SCRAPEDO_SUPER is true; an unset name means OFF (S81-23b; the legacy name is no longer read)") and the transition comment :48-54 in place (names only; no "anti-bot bypass" phrase, S23 R9).
2. `scripts/ab_render_providers.py`: delete line 18 (`os.environ["SCRAPEDO_SUPER"] = "true"`) and reword the :33 comment ("re-read geoCode set above"); the script does NOT set `ENABLE_SCRAPEDO_SUPER` (the super mode is retired under the robots policy; re-arming it from a script needs its own ruling, Q-23b-2); the docstring line naming "super+geoCode=bh" becomes "plain render (super retired, S81-23b)".
3. E-rows EK2 / EK3 (4.1).
4. New `tests/test_s81_s23b_scrapedo_super_retire.py`.

### 4. Existing pins
4.1 Deliberate changes (EK, the narrowest edits; the new LF blob shas recorded in the GREEN report; base LF blob shas `6cf8c6d3...` for the S23 file, `76a00ea5...` for the fragrance file):
- EK2 `tests/test_s81_s23_bypass_retire.py` (the G1 S81-23 rows that pinned the legacy read): `P1_CASES` (:335-336) super_on False for `"true"` and `"TRUE"` (the P1 / P2 rows then pin "new name unset -> OFF for every legacy value"; their docstrings reworded in place); `test_s23_r3_per_call_no_reset` (:179-190) starts from `NEW_FLAG` "true" instead of `LEGACY` "true"; `test_s23_p3_reset_hook_callable` (:418-427) and `test_s23_p4_geocode_default` (:430-434) set `NEW_FLAG` "true" instead of `LEGACY`. 7 nodes; the module docstring's transition sentence (:3-8) reworded. R8 (the G1 block names `ENABLE_SCRAPEDO_SUPER` and the robots doc) and R9 stay as they are.
- EK3 `tests/test_fragrance_content_quality.py`: the env key `"SCRAPEDO_SUPER"` -> `"ENABLE_SCRAPEDO_SUPER"` at :899, :919, :995, :1077 (the 4 red rows) and at :1008, :1025, :1097 (the 3 rows that would pass vacuously; Q-23b-1), docstrings naming the legacy flag in those rows reworded. 7 one-token edits.
4.2 Must stay green: the 23-file set of section 0 (incl. `test_scrapedo_service.py`, `test_source_usage_field.py`, `test_cascade_order_regression_qa.py`, `test_bahrain_source_matrix_coverage.py`, `test_s81_s15_registry_robots.py` (it deletes the legacy name, :71), `test_sephora_provider_test_classify.py` (the harness env side effect only)), `test_s81_g1_gate_rows.py`, the CLAUDE.md readers (S23 R8 and the forbidden phrases :290-296).

### 5. RED tests: `tests/test_s81_s23b_scrapedo_super_retire.py`
Hermetic: an autouse fixture deletes `ENABLE_SCRAPEDO_SUPER`, `SCRAPEDO_SUPER`, `SCRAPEDO_GEOCODE`, sets a run-time-built `SCRAPEDO_API_TOKEN`, pins `source_router.SOURCE_REGISTRY` to `_LITERAL_ROWS` and `_ROUTABLE_MEMO` None (the S23 fixture form); the S23 helpers by module import (`from tests import test_s81_s23_bypass_retire as s23`: `_render_params`, `_base_params`, `_routed_bahrain`, `SEPHORA`, `CATEGORIES`, `P2_ROUTED`); a recording `os` stand-in for the reader; pure ASCII, LF.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_legacy_alone_is_off` | parametrized legacy `"true"`, `"TRUE"`: `scrapedo_super_enabled() is False`, `_super_params() == {}`, `_super_enabled() is False` | AssertionError | 3.1 |
| R2 | `test_r2_legacy_name_never_read` | `monkeypatch.setattr(sd, "os", RecOs)` where `RecOs.getenv` / `RecOs.environ.get` / `__getitem__` record every name: `_super_params()`, `_super_enabled()`, both render functions and `get_sources_for_category("makeup")` -> `"SCRAPEDO_SUPER" not in recorded` | AssertionError | 3.1 |
| R3 | `test_r3_legacy_alone_routes_no_super_row` | legacy "true", new unset: SEPHORA not routed for makeup / skincare / fragrances; equals `P2_ROUTED["off"]` | AssertionError | 3.1 |
| R4 | `test_r4_legacy_alone_render_params_plain` | legacy "true": `_render_params == [_base_params(False)] * 2` | AssertionError | 3.1 |
| R5 | `test_r5_no_code_names_the_legacy` | AST over every `.py` under app/ and scripts/: no `ast.Constant` equal to `"SCRAPEDO_SUPER"` | AssertionError (`scrapedo_service.py`, `ab_render_providers.py`) | 3.1 + 3.2 |
| P1 | `test_p1_new_name_truthy_on` | `"true"`, `"1"`, `"yes"`, `" ON "`: ON (params + sephora routed) | green | base |
| P2 | `test_p2_production_state_off_identity` | both unset, and new `"false"`/`"0"`/`""` with legacy unset: params exactly `{token, url, render}` for both functions; routing == `P2_ROUTED["off"]` for every category | green | base |
| P3 | `test_p3_new_false_kills_regardless` | new "false" + legacy "true": OFF | green | base |
| P4 | `test_p4_reset_hook_and_geocode` | `reset_super_flags_cache() is None`; new "true" with GEO unset -> geoCode "bh" | green | base |

Counts: RED 5 (6 nodes), PIN 4.

### 6. Mutation table
| M | Mutation | Killed by |
|---|---|---|
| M1 | the legacy branch kept | R1-R5 |
| M2 | unset -> True | P2 |
| M3 | the legacy read moved to `os.getenv` | R2, R5 |
| M4 | the strip dropped | P1 (" ON ") |
| M5 | `_super_enabled` stops delegating (returns False) | P1 routing |

### 7. Comm set: the group's (12.1); 23b's reach: every importer of scrapedo_service (the closure reaches app.main, so the whole route surface).

### 8. CLAUDE.md row
`- S81-23b SCRAPEDO-SUPER-RETIRE (no flag; unflagged under R-A1 (c)): app/services/scrapedo_service.scrapedo_super_enabled no longer reads the legacy SCRAPEDO_SUPER: an unset ENABLE_SCRAPEDO_SUPER means OFF for every legacy value (production carries neither name since 2026-11-07 09:02, so byte-identical there; the corpus gate EQUAL cce256e1... at base and HEAD); scripts/ab_render_providers.py no longer sets the legacy name. E-rows EK2 (tests/test_s81_s23_bypass_retire.py P1 / P2 cases, r3, p3, p4) and EK3 (tests/test_fragrance_content_quality.py, the ON-state env key). RED tests/test_s81_s23b_scrapedo_super_retire.py.`
In place: CLAUDE.md:141 "its super / residential mode runs only under `ENABLE_SCRAPEDO_SUPER`, or, while that name is unset, the legacy `SCRAPEDO_SUPER=true`, which the owner unsets; see the S81-G1 block" -> "its super / residential mode runs only under `ENABLE_SCRAPEDO_SUPER` (unset = OFF since S81-G9 S81-23b; the legacy name is no longer read; see the S81-G1 block)"; CLAUDE.md:540: the "Transition semantics (R-G1-6)" sentence and the "Stated post-approval change (S81-23b)" sentence rewritten in place to the after-state (names only), L1 / L4 / L5 reworded (L1: the owner's unset landed 2026-11-07 09:02; L4: the A/B script no longer sets the legacy name; the `.qa-bias-rerun` harness still does and is inert); CLAUDE.md:541 owner step (1) -> "(1) done 2026-11-07 09:02 (SCRAPEDO_SUPER unset on web and price-warmer); never set `ENABLE_SCRAPEDO_SUPER=true`". The G1 block keeps naming `ENABLE_SCRAPEDO_SUPER` and `2026-08-31-robots-unreadable-ruling.md` (S23 R8); none of the five forbidden phrases.
Owner steps: none (both preconditions met).

### 9. Stated limits
- L-S23b-1: a box that still carries `SCRAPEDO_SUPER` loses the super tier unless `ENABLE_SCRAPEDO_SUPER` is set (production carries neither since 09:02).
- L-S23b-2: the tracked `.qa-bias-rerun/_sephora_provider_test.py` still sets the legacy name (outside app/ and scripts/); after this unit it is inert for super mode.
- L-S23b-3: the corpus gate cannot reach the reader (reader calls 0 in the gate); the behaviour proof is the RED / PIN rows.
- L-S23b-4: docs/contracts and the 2026-06 plans keep the legacy name as history.

### 10. Out of scope: source_router comments (history; Q-23b-3), `.qa-bias-rerun/`, `_SUPER_FLAGS` / the reset hook removal.

### 11. Open questions
- Q-23b-1: EK3 for the 3 vacuous rows too (default YES, 7 edits) or only the 4 red rows?
- Q-23b-2: `ab_render_providers.py` drops the legacy write without setting the new name (default; the super mode stays retired) or sets `ENABLE_SCRAPEDO_SUPER="true"` in its own process?
- Q-23b-3: rewrite the source_router / structured_comparison_service comments naming `SCRAPEDO_SUPER` (5 + 1 comment lines in app/, wider footprint) or leave them (default)?

---

## 12. The group

### 12.1 Combined comm set (the union rule, derived at 39ac80ba)
Derivation (`<scratchpad>/g9spec/comm.py`, read-only, AST): (a) the transitive importer closure of the three edited modules `app.services.scrapedo_service`, `scripts.seed_kb_brands_wikidata`, `scripts.cron_kb_coverage` inside app/ and scripts/ (105 modules incl. `app.main`, `<scratchpad>/g9spec/closure.txt`) and every test naming a closure module (dotted, or the stem with its package); (b) every `app.main` / `TestClient` user; (c) the symbol references (`scrapedo_super_enabled`, `_super_params`, `_super_enabled`, `reset_super_flags_cache`, `_super_routing_enabled`, `requires_super`, `SCRAPEDO_SUPER`, the three flags + `ENABLE_COMPARE_RUN_LEDGER`, `verify_flag_byte_identity`, `can_fetch`, `QARENBOT_UA`, `PoliteFetcher`, `kbh:`, `upstash`, the edited test modules' names); (d) the forced source-scanning pins (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_sentry_channels_u8d, test_secret_scan_static, test_hermeticity_pins, test_s81_kb_schema, test_robots_unreadable_ruling) and every test combining a source read (`inspect.getsource`, `ast.parse`, `find_spec`, `__file__`, `read_text`, `read_bytes`, glob / listdir / scandir) with an app / scripts / docs / data / SmartCompareApp / .github / railway path; (e) the CLAUDE.md readers (38, incl. test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_*, test_s81_s23_bypass_retire); (f) the docs/ readers: none read docs/policies bytes (1.9 of 16c); (g) the edited test files and their importers (the S03, S23 and fragrance files; no importer); MINUS the four hook files (`test_precommit_hook.py`, `_round2`, `_phase_b`, `_phase_b_round2`; no .githooks change). Result: **669 files** (`<scratchpad>/g9spec/COMM_SET_G9.txt`, sorted LF list sha256 `150685c6680ade7718d05007f9163c8f1d2079f7cc578f55211faf8cd03fcb2b`; reason counts closure 625, app.main 140, source_scan 144, symbol 51, claude_md 38, forced 16), plus the four RED files at GREEN (HEAD-only).

Base record (LC-6 / GC-9, the 09:41 MOVING MAIN line): no record is stored at 39ac80ba. 665 of the 669 are members of the stored daf86d32 record `ea0d2f1b...` (712); the other 4 are the G8 files new on main (`test_s81_b1b_url_telemetry.py`, `test_s81_g8_gate_rows.py`, `test_s81_s11b_result_aggregates.py`, `test_s81_s18b_store_label.py`). A first split by names (`<scratchpad>/g9spec/rerun_at_base.txt`): 365 members name a #394 stem (result_gate / sentry_service / compare_runs / kb_serve / response_builder / structured_comparison_service / store_labels / merchant_labels), CLAUDE.md, app.main / TestClient or a walker -> RUN at the RED base in chunks of <= 25 (bound 1200, one pytest at a time); 304 candidates for per-file reuse, each only after the RED agent checks its bytes unchanged daf86d32 -> then-main. The stored base FAILED set's known environmental ids (24 at daf86d32: auth_interceptor x2, page_scraping x2, personalization_bundle_c x2, prompt_truth tiktoken x2, the CRLF class d16 r10 / d17 r9 / s16 r27 x5 / s19 r15 / s10 r06 / d22c p1 x5, s22 b02 / j01) carry over. GREEN runs the set + 4 at HEAD; `comm -13` of the sorted FAILED sets must be EMPTY. The S03 file and the RED 22d file run a second time with `ENABLE_COMPARE_RUN_LEDGER=true` in the runner call only.

CI-order set (one call, bound 1200, flags unset): the four RED files + test_s81_s16_kb_seed, test_s81_s16b_kb_brands, test_s81_d17_coverage, test_s81_d17b_coverage_paging, test_s81_s03_llm_ledger_v2, test_s81_s22_compare_runs, test_s81_s22_gate_rows, test_s81_s23_bypass_retire, test_fragrance_content_quality, test_scrapedo_service, test_source_usage_field, test_cascade_order_regression_qa, test_bahrain_source_matrix_coverage, test_s81_g1_gate_rows, test_s81_kb_schema, test_ci_gates, test_hermeticity_pins, test_secret_scan_static.

Client fences: the fourteen (brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout) + b3a/nativeStrings, BY PATH through the junction the orchestrator creates at GREEN (an app/ and a CLAUDE.md edit). Measured: no `SmartCompareApp/__tests__` file reads scrapedo_service.py, the two scripts, the S03 / S23 / fragrance test files, docs/policies or CLAUDE.md (the ten files that name CLAUDE.md do so in comments only). Expected green, unchanged. FULL jest once in the final round (LC-7).

Corpus gate: `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP`: base `cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c`; prototype HEAD the same (23b.1.4); GREEN re-runs it at HEAD (SCRAPEDO_SUPER unset): EQUAL expected.

Other gates: ruff `--select E9,F63,F7,F82` + `py_compile` on the three edited Python files and the four RED files; bytes > 127 = 0 in every new file; `git diff --stat` shows no whole-file diff; the added-line sweep (no 64-hex literal in one piece beside a keyword-named constant; the new constant names `WDQS_EXEMPT_RULES`, `WDQS_RULING_DATE`, `WDQS_RULING_DOC`, `WDQS_RETRY_STATUSES`, `WDQS_RETRY_CAP_SECONDS`, `PIPELINE_REFUSED`, `LEDGER_FLAG` carry no gitleaks keyword; the RED files' sha pins use names like `ROBOTS_EVAL_LF_SHA`, never `*_KEY`); the policy doc byte-equal to the docs-branch blob.

### 12.2 Combined footprint
app/: `app/services/scrapedo_service.py`. scripts/: `scripts/seed_kb_brands_wikidata.py`, `scripts/cron_kb_coverage.py`, `scripts/ab_render_providers.py`. docs/: NEW `docs/policies/2026-11-07-wdqs-robots-exemption.md`, `docs/policies/2026-08-31-robots-unreadable-ruling.md` (one line). tests/: four new RED files; E-rows in `tests/test_s81_s03_llm_ledger_v2.py` (EK1), `tests/test_s81_s23_bypass_retire.py` (EK2), `tests/test_fragrance_content_quality.py` (EK3). CLAUDE.md. Deploy note: the `cron_kb_coverage.py` edit matches `railway.kbcoverage.json`'s watch pattern (a push redeploys that service; a cron redeploy does not execute the job, ledger.md:351); no other service's watch pattern matches (kb_seed_common untouched).

### 12.3 Shared-file plan
Only CLAUDE.md is shared (12.5); every other file has one unit; GREEN applies the units in the section 0 order, CLAUDE.md last.

### 12.4 PR plan
ONE PR `feature/s81-g9-followups` -> main, body <= 25,600 bytes measured with python: a summary; one short section per unit (S81-16c, D17c (+ D17d PINs), S81-22d, S81-23b: what, flag, RED file, counts); the E-rows table (EK1 S03 2 rows / 4 nodes; EK2 S23 7 nodes; EK3 fragrance 7 rows, with base and new LF blob shas); the comm result (669 + 4, branch-only-new EMPTY; the S03 pair exported / unset); the corpus gate line (EQUAL `cce256e1...`); the fences and the full-jest figure; the stated limits by id; the owner steps names-only (16c: the DRY then apply runs; D17c: watch the next kb-coverage totals; 22d none; 23b none); the ruling doc named. Mutation tables and per-row evidence go to specs/ files in the state folder.

### 12.5 CLAUDE.md
- ONE block after the NEWEST block at the final round (at base: after the S81-G8 owner-steps bullet CLAUDE.md:614, one blank line, before `## Tests` :616; if the S81-24 block lands first, after it), heading `**SESSION 81 units (S81-G9 FOLLOWUPS: S81-16c WDQS-EXEMPTION + D17c COVERAGE-EMPTY-HOSTS + S81-22d LEDGER-PINS-FLAG-SAFE + S81-23b SCRAPEDO-SUPER-RETIRE, 2026-11-07; NO new flag: S81-16c rides ENABLE_KB_BRANDS, D17c rides ENABLE_KB_COVERAGE_ROLLUP, S81-22d is test-only, S81-23b is unflagged under R-A1 (c); the eighth SAFE group under LC-9; spec .qa-s80/S81-G9_UNIT_SPEC.md, rulings specs/RULINGS_S81_G9.md):**` followed by the four rows of the sections 8 and one owner-steps bullet.
- The :341 pointer clause gains, after the S81-G8 sentence (and the S81-24 one if merged first): `` S81-G9 FOLLOWUPS adds no flag (S81-16c and D17c ride `ENABLE_KB_BRANDS` / `ENABLE_KB_COVERAGE_ROLLUP`; S81-23b retires the legacy `SCRAPEDO_SUPER` read): the rows of the **SESSION 81 units (S81-G9 FOLLOWUPS, ...)** block. ``
- In place: :141, :540, :541 (23b), :550 (16c), :562 (D17c), :605 / :608 (22d), as in the sections 8.
- Conditional (the 09:10 / 09:50 S87 notes assign them to the S81-24 final round or the G9 GREEN, whichever lands first): the :92 apply record (045, 047, 050, 052 applied; 046 / 048 / 049 written NOT applied) and the S81-08b row (`ENABLE_LEGACY_FINGERPRINT_READER` ON on web since 2026-11-07, deployment cffeb4eb), each rewritten in place with the dated ledger line, ONLY if S81-24 has not merged them first (Q-G9-2).
- Text constraints: no line with both `scoring_method` and `enum`; none of the five S23 forbidden phrases; the G1 block keeps `ENABLE_SCRAPEDO_SUPER` + `2026-08-31-robots-unreadable-ruling.md`; ASCII in the added text.
DEFECT_LEDGER ids (names only; the orchestrator files them): `S81-16c WDQS-EXEMPTION` (RULINGS_S81_16C), `D17c COVERAGE-EMPTY-HOSTS` (+ the D17d / D16c candidate as PIN-only), `S81-22d LEDGER-PINS-FLAG-SAFE` (closes S81-22 L-I2I6), `S81-23b SCRAPEDO-SUPER-RETIRE` (closes the S81-23 transition, R-G1-6).

### 12.6 SAFE check (FOCUS surfaces)
| Surface | Touched? | Evidence |
|---|---|---|
| auth / tokens / sessions | no | no auth file; the RED files build a fake token at run time only |
| quota / billing / refunds | no | no usage / refund path; Scrape.do credits: 23b only removes a way to enable the more expensive super mode |
| legal or privacy text | no | no app/legal / landing / privacy file; the new docs/policies file is an internal robots-policy record (not user-facing), its bytes ruled by the owner and filed by the orchestrator |
| consent path | no | none |
| security middleware | no | none (scrapedo_service is a provider wrapper; the SSRF / robots fetcher is read, not edited) |
| migrations | no | none |
| Redis / Lua scripts | no Lua; one Redis READ path | D17c changes WHEN the off-clock script issues its existing read-only HGETALL pipeline (never with 0 hosts) and how a failure is counted; no write, no Lua, no key shape, no app/ Redis code (cache_service untouched) - classified SAFE (a read-path guard in an off-clock script, the D17b precedent) |
| App-Review-visible client surface | no | no client file; no response key |
| secrets or key handling | no | no credential name added; the RED files carry no key-shaped literal |
Result: **no FOCUS surface; every unit stays in the group** (focus_surfaces_found empty). Recorded for the orchestrator: D17c is the only unit whose flag is ON in production (apply on kb-coverage since the 11:20 ops line), so its merge changes the next scheduled pass on its two edge paths (0 hosts, a failed read); S81-23b is unflagged but byte-identical in the production state.

### 12.7 Known rebases (the RED re-point)
- The S81-24 branch (auth_routes / auth_throttle / request_id / _env_safety / CLAUDE.md; its fix round adds tests/test_s81_s24_fix1_rows.py + test_s81_s24_gate_rows.py): disjoint from this group except CLAUDE.md (its block after the G8 block, the :341 clause, the :92 record and the S81-08b row in place); if it merges first, G9's block goes after it and the two conditional edits drop. `tests/_env_safety.py` is a test-support helper: if S81-24 merges first, its importers join the comm set by (g) and the base record re-derives them.
- `specs/RULINGS_S81_G9.md` (not yet filed at spec time) may fold D17d into D17c (the 10:05 note); this spec measured it (D17c 1.7) and carries it as PIN rows P4 / P5.

### 12.8 Open questions for the orchestrator (group)
- Q-G9-1: D17c's root cause = the empty pipeline (measured; the "410 merchants" and "transient" readings contradict the timestamps) - confirm (Q-D17c-1).
- Q-G9-2: the two conditional CLAUDE.md rewrites (:92, S81-08b) in G9 if S81-24 has not landed them?
- Q-G9-3: does the policy doc need a docs/ reader pin? Default: NO new pin beyond R8 of 16c (the script names the doc; R8 asserts the doc path constant appears in exactly one code file); a byte pin on the doc would make a later owner amendment an E-row.
- Q-G9-4: S81-23b E-row scope (Q-23b-1) and the A/B script (Q-23b-2).

Not done in this spec: the RED files, the mutation runs, the base record at the then-main, any production probe.
