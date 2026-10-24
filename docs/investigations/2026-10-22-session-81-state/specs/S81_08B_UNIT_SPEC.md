# S81-08b LEGACY-FINGERPRINT-READER: unit spec (measured at ea3aef15)

- Unit: S81-08b LEGACY-FINGERPRINT-READER (lane B backend, additive). PLAN_S81 client lane companion of
  S81-08 CLIENT-FIRST-OTA; DEFECT_LEDGER row S81-08b (the OTA precondition of RULINGS_S81_08 R-S08-4).
- Flag: `ENABLE_LEGACY_FINGERPRINT_READER` (NEW name, default OFF, read PER CALL with the house idiom
  `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`). No knob. No credential.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b (detached at the base). Branch for GREEN:
  `feature/s81-s08b-legacy-fingerprint-reader`.
- Base sha: ea3aef15bb234bc7fe3776858556f4782ac40e49 (main = + #372 S81-04). `git status --short` of the
  worktree: EMPTY before and after every probe of this spec (the probes ran in a detached scratch
  worktree under the notes folder, removed afterwards and verified absent from `git worktree list`).
- Main moved during this spec: 86d5a24d = + #373 S81-14 KB-SCHEMA (2026-10-24 17:54). Known rebase
  items, measured with `git show 86d5a24d:<path>` from the worktree's object store: (1) CLAUDE.md gains
  the S81-14 row at :497 (anchor union: this unit's row goes AFTER it at rebase); (2)
  `tests/test_s81_kb_schema.py:412-428` pins the LF sha256 of `tests/test_s75_fanout_identity.py`
  (IDENTITY_NODES), so this unit must NOT edit the FY25 file (section 4.2 E-none). No other S81-14 file
  is touched by this unit.
- Evidence (notes folder `<scratchpad>/s81-08b/`): `notes.txt`; `base_A.log`, `base_B.log` (1.10);
  `probe_out.json` + `probe.log` (the base call shapes of 1.3-1.7, run in the scratch worktree);
  `probe_test_copy.py.txt` (the probe source); `probe_postgrest_in.py` (offline filter rendering);
  `comm_files.txt` + `comm_chunk_00..08` (section 7).
- Contracts consumed: S81-05 (merged #371): `app/utils/request_context.py` owns the one compiled
  `DEVICE_FINGERPRINT_RE` that `auth_routes` re-imports (:35); S81-05 does not parse the legacy header
  (RULINGS_S81_05 R-S05-1; the S81-08 spec 1.5). S81-08 (client, RULINGS_S81_08): R-S08-4 (the legacy
  header rides ONLY register, both social sign-ins and the share path; runtime cutoff
  2027-03-31T21:00:00Z), R-S08-5 (no legacy header on compares / usage / camera / SSE), R-S08-7 (the
  NEW value = SHA-256 of the SecureStore `device_fp_nonce`; the legacy value = today's composition byte
  for byte), R-S08-12 (client Sentry redaction). W3-3 (`ENABLE_SOCIAL_DEVICE_FINGERPRINT`, PR #166).
- Sister units: S81-08c (removes this reader and the flag after the cutoff); S81-09 DEVICE-QUOTA (drops
  the stored-hash step; never needs the legacy value: PLAN_S81 VERIFY "Quota, auth, refusal").
- Production flag state (newest dated ledger line only; R-A15): the session-81 ledger names neither
  `ENABLE_SOCIAL_DEVICE_FINGERPRINT` nor `ENABLE_REFERRAL_SYSTEM` nor `ENABLE_ANON_USAGE_GATE`; the
  session-80 ledger names none of them. All three are UNKNOWN: this spec designs for both states.
  `ENABLE_REQUEST_CONTEXT_HEADERS` is OFF (S81-05 merge line, ledger :59). The new flag is unset by
  construction (a new name).
- Personal-data rule: the repo is public. Every fingerprint in tests is built at run time
  (`hashlib.sha256(b"s81-08b-new").hexdigest()` and `...(b"s81-08b-legacy")`), every id is a synthetic
  nil-shaped uuid, every email ends in `.invalid` or `example.com`. No log line, fixture or report
  carries a fingerprint value.

-----------------------------------------------------------------------------------------------------

## 0. What the unit does

After the S81-08 OTA, `X-Device-Fingerprint` carries the NEW stable-id hash, and register, both social
sign-ins and the share call also send `X-Device-Fingerprint-Legacy` (today's composition, 64 lower-case
hex) until 2027-03-31T21:00Z. Every `users.device_fingerprint_hash` row written before the OTA holds the
LEGACY composition, so without this unit a post-OTA re-signup on an existing device inherits nothing.

Measured at base, exactly TWO request-time matches against stored rows exist, both in
`app/api/auth_routes.py`: the register inheritance and the W3-3 social apply (both through
`_inherit_device_counter`). Under the flag, when the request carries a valid legacy header that differs
from the NEW value, those two matches select over `device_fingerprint_hash IN (NEW, LEGACY)` instead of
`= NEW`, and the row that is written still stores the NEW value. Nothing else changes.

Measured, and NOT changed by this unit (section 1.5): the share path stores the body value and matches
nothing; the invite / quiz routes read no fingerprint; the SAME_DEVICE check and the referral device
lifetime cap compare STORED values with STORED values on the invitee's first compare, a request that
carries no legacy header (R-S08-5), so no header reader can reach them; and SAME_DEVICE is unreachable in
production at base (`_load_invitee` never selects the hash).

Flag OFF: byte-identical (no header read beyond the flag read; the same DB calls, the same log lines).
Flag ON with no legacy header (build 3), or with an invalid or NEW-equal one: byte-identical to OFF
(the build-3 identity, pinned with literal call lists recorded at base).

-----------------------------------------------------------------------------------------------------

## 1. Base state (MEASURED at ea3aef15)

### 1.1 Every reader of a fingerprint in app/ (grep -rn -i fingerprint app/ --include=*.py)

| File | Count | What it is |
|---|---|---|
| app/api/auth_routes.py | 29 | the register / social reader, inheritance and apply (1.2, 1.3) |
| app/utils/request_context.py | 23 | S81-05 leaf: `DEVICE_FINGERPRINT_RE` (:93), `parse_device_fingerprint` (fullmatch, :132-136), ContextVar; no stored-row match |
| app/services/usage_service.py | 16 | `_DEVICE_FINGERPRINT_RE` (:23), `valid_device_fingerprint` (:37-42), the anon gate keyed `anon:{fp}` in Redis (:45-136, `ENABLE_ANON_USAGE_GATE`): a Redis counter, not a stored-row match; compares carry no legacy header (R-S08-5) |
| app/services/referral_service.py | 11 | `create_invite` stores the body value (:242-340, payload :318-324); `_find_unredeemed_invite_for_invitee` selects it (:715-740); `_referrer_device_lifetime_count` stored-vs-stored (:772-812) |
| app/services/abuse_detection_service.py | 7 | SAME_DEVICE stored-vs-stored (:116-148, :239-251) |
| app/api/image_routes.py / text_routes.py | 4 / 4 | `valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` for the anon gate (image :227, text :1405) |
| app/api/referral_routes.py | 3 | `ShareRequest.device_fingerprint_hash` Pydantic pattern (:117-119), passed to `create_invite` (:209) |
| app/middleware/request_context.py | 1 | docstring |
| app/services/sentry_service.py | 1 | comment at :180 (the header allowlist) |
| app/services/structured_comparison_service.py | 1 | unrelated ("Akamai Bot-Manager fingerprints") |
| app/services/auth_service.py | 0 | measured: no fingerprint reference (the brief's "auth_service" site does not exist) |

`grep -rn "LEGACY_FINGERPRINT\|Fingerprint-Legacy\|fingerprint-legacy\|fingerprint_legacy"` over app/,
tests/, scripts/, .github: 0 hits; CLAUDE.md: 1 (the S81-05 row at :492). The flag name is new.

### 1.2 The register site (app/api/auth_routes.py)

| What | Line | Fact |
|---|---|---|
| regex | 35 | `from app.utils.request_context import DEVICE_FINGERPRINT_RE as _DEVICE_FINGERPRINT_RE` |
| reader | 478-496 | `_read_valid_device_fingerprint(request)`: `request.headers.get("X-Device-Fingerprint")` (:489); `.match` (so a value + trailing `\n` PASSES, pinned by `test_s05_p06_fp_readers_unchanged`); invalid -> INFO `device-fp header rejected: invalid format (expected 64-char hex), len=%d` and None; empty string returned as "" (falsy) |
| inheritance | 499-537 | `_inherit_device_counter(admin_client, fp, user_id, *, floor=0)`: SELECT `lifetime_comparisons_used` `.eq("device_fingerprint_hash", fp)` `.order(..., desc=True)` `.limit(1)`; inherited = max(floor, top or 0); UPDATE `{device_fingerprint_hash: fp, lifetime_comparisons_used: inherited}` `.eq("id", user_id)`. The ONLY row written is the caller's own (`.eq("id", user_id)`): no sibling row is ever written |
| register route | 582-684 | `@router.post("/register", response_model=AuthResponse)` `@limiter.limit("3/minute")`; consent :609-611; `register_user` :613; fp read :624; `if fp and new_user_id:` -> try `_inherit_device_counter(get_admin_supabase_client(), fp, new_user_id)` (:627) / except WARNING `device-fp inheritance failed (silent): {exc}` (:629, an f-string with `str(exc)`, pre-existing) |
| social flag | 395-418 | `social_device_fingerprint_enabled()` = `ENABLE_SOCIAL_DEVICE_FINGERPRINT`, the house idiom |

Base call list, MEASURED (probe `register/*`, a recording admin client, prior row `{lifetime_comparisons_used: 3}`;
identical with and without an `X-Device-Fingerprint-Legacy` header and with any value of the new flag
name, which nothing reads at base):

```
REG_BASE = [
  ["table", ["users"]], ["select", ["lifetime_comparisons_used"]],
  ["eq", ["device_fingerprint_hash", NEW]], ["order", ["lifetime_comparisons_used"], {"desc": True}],
  ["limit", [1]], ["execute", []],
  ["table", ["users"]], ["update", [{"device_fingerprint_hash": NEW, "lifetime_comparisons_used": 3}]],
  ["eq", ["id", UID]], ["execute", []],
]
```
Legacy header only (no `X-Device-Fingerprint`): ZERO table calls. No headers: ZERO table calls. Status 200
in every case.

### 1.3 The social site (W3-3)

| What | Line | Fact |
|---|---|---|
| route | 1158-1172 | `social_login`; after the 401 / consent raises: `if social_device_fingerprint_enabled(): _apply_social_device_fingerprint(request, (result.get("user") or {}).get("id"))` (:1171-1172); then the B3-B Apple block; returns `result` unchanged |
| apply | 540-579 | fp via the same reader (:553); `if not fp or not user_id: return`; own row SELECT `device_fingerprint_hash, lifetime_comparisons_used` `.eq("id", user_id)` `.limit(1)`; `if row.get("device_fingerprint_hash"): return` (:566, first-device binding: the docstring :544-548 names the attack an overwrite would open: reinstall to move a hash off a saturated device); else `_inherit_device_counter(admin, fp, user_id, floor=own)`; except -> WARNING `device-fp social apply failed (silent): %s` type name |

Base call lists, MEASURED (W3-3 ON, both headers sent): own hash NULL -> 15 calls (`SOCIAL_BASE_NULL`:
own select/eq id/limit/execute, then the 6-call device read with `.eq("device_fingerprint_hash", NEW)`,
then the 4-call update writing NEW and max(own, device)); own hash already set (to the LEGACY value) ->
5 calls (`SOCIAL_BASE_OWNED`: the own read only, early return). Both literals are in `probe_out.json`.

### 1.4 The share / invite path (open question c)

| What | Line | Fact |
|---|---|---|
| router gate | referral_routes.py:51-80 | router-level `Depends(_require_referral_enabled)` (`ENABLE_REFERRAL_SYSTEM == "true"` after strip/lower; else 503 FEATURE_DISABLED before auth and body validation) |
| body field | referral_routes.py:117-119 | `device_fingerprint_hash: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")`: an invalid BODY value is a 422 (measured: upper-case -> 422), never dropped |
| route | referral_routes.py:176-232 | `share_comparison` passes `device_fingerprint_hash=body.device_fingerprint_hash` (:209) to `create_invite`; reads no header |
| store | referral_service.py:242-340 | `create_invite` inserts `referral_invites.device_fingerprint_hash` = the body value (:318-324); NO comparison with any stored value |
| invite / quiz | referral_routes.py GET `/invite/{share_token}` (:256), POST `/invite/{share_token}/quiz` (:288-318); referral_service `resolve_invite` :386, `run_invitee_quiz` :463 | no fingerprint read or match (grep: referral_routes has 3 fingerprint references, all ShareRequest / :209) |

Measured (probe `share`): POST `/api/v1/referrals/share` with body NEW and header LEGACY -> 201,
`create_invite` kwargs `{comparison_id, device_fingerprint_hash: NEW, referrer_user_id, share_target,
show_name, show_reasons, show_result}`; the legacy header is ignored. Conclusion for (c): the body value
(NEW after the OTA) is what is stored, the legacy header at share has NO consumer anywhere at base or in
this unit, and the share route stays untouched in both flag states (PIN P8). S81-08 may keep sending it
(harmless) or drop it at share (a client simplification; open question Q3).

### 1.5 SAME_DEVICE and the device lifetime cap (stored-vs-stored; out of reach of any header)

| What | Line | Fact |
|---|---|---|
| trigger | referral_service.py:628-713 | `try_trigger_loop2(invitee_user_id, comparison_id)` runs from `save_comparison_and_track_cohort` on the invitee's FIRST saved compare: a compare request, which carries no legacy header (R-S08-5) |
| invitee load | referral_service.py:758-770 | `_load_invitee` selects `"id, email, subscription_tier, display_name"` (:762): NO `device_fingerprint_hash` |
| SAME_DEVICE | abuse_detection_service.py:239-251, :116-129 | `invitee_device_hash = invitee.get("device_fingerprint_hash")` (:249) is therefore ALWAYS None on the production path; `is_same_device` returns False at :124-125 before `_get_referrer_device_hash` (:131-148, the referrer's latest `referral_invites` hash) is read |
| device cap | referral_service.py:772-812 | `_referrer_device_lifetime_count`: the referrer's STORED `users.device_fingerprint_hash`, then SUM over users rows `.eq(` that value `)`; no request value involved |

Measured (probe `same_device`, the real `_load_invitee` and the real `evaluate_invite` over a recording
client whose referrer invite hash equals the invitee's device): select = `id, email, subscription_tier,
display_name`; loaded keys = display_name/email/id/subscription_tier; `evaluate_invite` -> `{passed:
True}`; `_get_referrer_device_hash` reads = 0. SAME_DEVICE is dead code in production at base (the same
class as U3c-13's display_name finding). Existing pins drive it only by mocking `_load_invitee` or by
calling `evaluate_invite` with a hand-built invitee dict (test_abuse_detection.py:228-292,
test_referral_loop2.py:145-176). This unit does not touch it (reviving it changes flag-OFF behaviour in
production and is a separate defect: open question Q1). Under any revival, the comparison stays
stored-vs-stored, so the legacy HEADER can never reach it; only a dual-stored value (a migration) or a
rewrite of stored rows could (Q2).

### 1.6 Migration 021 and the indexes

`migrations/021_device_fingerprint_users.sql`: `ADD COLUMN IF NOT EXISTS device_fingerprint_hash TEXT`,
partial index `idx_users_device_fp ON users(device_fingerprint_hash) WHERE device_fingerprint_hash IS
NOT NULL`, a COMMENT naming bundle id + osBuildId + nonce. There is NO CHECK constraint and no regex in
any migration: the 64-hex rule lives only in code (auth_routes :35 via the leaf, usage_service :23,
ShareRequest :118). 023 adds `idx_users_device_fingerprint_active` (same column, same predicate); 032
drops the duplicate 021 index and keeps 023's (032 comment :38-43; the apply record in CLAUDE.md lists
010-032 applied). 014 adds `referral_invites.device_fingerprint_hash TEXT` (no index). 025 / 043 NULL the
column in the deletion cascade.

Partial-index implication (stated, not measured live: no database is touched by any agent): the new
read `device_fingerprint_hash IN (NEW, LEGACY)` with two non-null constants implies `IS NOT NULL` (a
strict operator over non-null constants; PostgreSQL's predicate proof accepts it), so the 023 partial
index serves it like today's `=`; it is one indexed lookup of two keys per register / social apply. With
NO upgrade-on-match (2.4) no existing row's indexed value changes, so the index sees exactly today's
writes (one row per register / social apply, the caller's own).

postgrest 2.31.0 rendering, MEASURED offline (`probe_postgrest_in.py`, no network): `.eq(...)` ->
`device_fingerprint_hash=eq.<NEW>`; `.in_("device_fingerprint_hash", [NEW, LEGACY])` ->
`device_fingerprint_hash=in.(<NEW>,<LEGACY>)`; `.select("lifetime_comparisons_used,
device_fingerprint_hash")` -> `select=lifetime_comparisons_used,device_fingerprint_hash`. `in_` exists on
the pinned builder (`postgrest/base_request_builder.py:452-455`, values through `sanitize_param`; hex
needs no quoting).

### 1.7 The S81-05 middleware (open question a)

`app/middleware/request_context.py` (39 lines) binds three headers through the leaf's
`bind_from_headers` (`app/utils/request_context.py:218-252`), atomic over exactly three names
(`_HEADERS` :79-83, the 3-tuple `_HEADER_STATES` :107-109, `header_state` :190-216). It runs only under
`ENABLE_REQUEST_CONTEXT_HEADERS`. Source-scanning pins in `tests/test_s81_s05_request_context.py` that a
middleware or leaf change would move: `test_s05_r08_one_regex_object` (:527-553: auth_routes imports
EXACTLY `[("DEVICE_FINGERPRINT_RE", "_DEVICE_FINGERPRINT_RE")]` from the leaf and assigns no
`_DEVICE_FINGERPRINT_RE`), `test_s05_p01_no_consumer_in_app` (:1325-1379: only the four allowed files
may contain the text `request_context`; auth_routes' leaf import set must equal
`{"DEVICE_FINGERPRINT_RE"}`; no other app file may import the leaf), `test_s05_p02` (no context header
in the OpenAPI), the header-state and bind rows. Decision (a): ROUTE-LEVEL read in auth_routes through
one helper, reusing the already-imported `_DEVICE_FINGERPRINT_RE` with `.fullmatch` (no new leaf import,
no `request_context` text added anywhere): zero S81-05 pins move, the reader does not depend on
`ENABLE_REQUEST_CONTEXT_HEADERS`, and the only consumers (two) both hold `request` already. A middleware
read would move r08 / p01 / the state tuple pins and couple the two flags for no consumer.

### 1.8 Sentry (backend)

`app/services/sentry_service.py:179-186` (comment :179-182, `_REQUEST_HEADER_ALLOWLIST` :183-186) (host, user-agent, accept,
accept-encoding, accept-language, content-type, content-length, connection, x-request-id);
`_scrub_request_region` :447-468: authorization / x-admin-key / cookie / x-qaren-synthetic ->
`[REDACTED]`, any other header -> `[Filtered]`, shared by `_before_send` and `_before_send_transaction`.
MEASURED (probe `sentry`): `x-device-fingerprint`, `x-device-fingerprint-legacy` and
`X-Device-Fingerprint-Legacy` all ship `[Filtered]` in both hooks. The legacy header already mirrors the
primary header's redaction by construction: NO sentry_service change (PIN P9 keeps it).

### 1.9 Libraries on the pinned venv (`.venv-qaren`, the CI lock)

fastapi 0.141.1, starlette 1.6.0 (`request.headers` is a case-insensitive immutable mapping),
pydantic 2.13.4, postgrest / supabase 2.31.0. No new dependency.

### 1.10 Base pass state of the touched files' pins (bounded runner, base, flag unset)

- Set A (8 files: test_social_login_device_fingerprint.py, test_auth_routes_invite_fingerprint.py,
  test_usage_device_inheritance.py, test_s81_s05_request_context.py, test_sentry_channels_u8d_unit.py,
  test_consent_capture_w3_16.py, test_s79_b3b_apple_revoke.py, test_security_regression.py):
  `599 passed, 63 warnings in 46.61s`;
  `[hermeticity] sentinel checked 599 test(s)`; `[netguard] blocked 14 attempt(s) from 8 node(s)`
  (pre-existing sentinel / egress lines, e.g. test_security_regression TestQueryMaxLength);
  `[pyt] tag=s08b-base-A start=2026-10-24 18:22:37 end=2026-10-24 18:23:26 elapsed=49s bound=1200s status=OK rc=0`.
- Set B (13 files: test_ci_gates.py, test_behavior_dimension_translation.py,
  test_s81_s04_spend_breaker.py, test_s71_u13_compare_auth_required.py, test_abuse_detection.py,
  test_abuse_detection_internals.py, test_referral_loop2.py, test_referral_lifetime_cap.py,
  test_referral_service.py, test_referral_share_status_lifetime.py, test_referral_e2e.py,
  test_u3c_referral_push_name.py, test_s75_fanout_identity.py): `661 passed, 1 skipped, 13 warnings in 24.97s`;
  `[hermeticity] sentinel checked 661 test(s)`; `[netguard] blocked 34 attempt(s) from 6 node(s)`;
  `[pyt] tag=s08b-base-B start=2026-10-24 18:24:36 end=2026-10-24 18:25:03 elapsed=27s bound=1200s status=OK rc=0`.
- Probe (scratch worktree at ea3aef15, 7 nodes): `7 passed`; `[netguard] blocked 0 attempt(s) from 0 node(s)`;
  `[pyt] tag=s08b-probe start=2026-10-24 18:31:28 end=2026-10-24 18:31:33 elapsed=5s bound=600s status=OK rc=0`.
- NOT MEASURED: the 222-file comm set at base (9 chunks; budget); GREEN runs base and head.

### 1.11 Guards the new code must not trip, and line endings

- `test_s05_r08` / `test_s05_p01` (1.7): no new import from the leaf, no `request_context` text in any
  other app file. `test_s05_p06_fp_readers_unchanged`: `_read_valid_device_fingerprint`,
  `usage_service.valid_device_fingerprint` and the ShareRequest pattern unchanged. `test_s05_p07`: the
  image / text header reads untouched. `test_s05_p02` + T23 `test_T23_openapi_unchanged`: the legacy
  header is read from `request.headers` and NEVER declared as a FastAPI `Header(...)` parameter (probe
  `openapi_fp_params` = []).
- `test_ci_gates.py` / `test_behavior_dimension_translation.py` / `test_s81_s04_spend_breaker.py`
  (`test_r38_claude_md_row` reads the S81-04 row from its start to the next `\n**SESSION`): the new row
  is its own `**SESSION 81 flag (...)**` paragraph after the S81-04 row (after S81-14's at rebase).
- FY25 `tests/test_s75_fanout_identity.py` + S81-14's IDENTITY_NODES sha: UNEDITED (the flag is never
  read on a compare path, so it cannot move a digest).
- No new log line carries a value: constants and type names only; ERROR never used.
- Line endings: `app/api/auth_routes.py` CRLF working copy (1,650 CRLF, 67,765 B, 61 pre-existing
  non-ASCII chars, LF sha256 5add302d...0d98be2); `CLAUDE.md` CRLF (958 lines). Every ADDED line pure
  ASCII; `git diff --stat` must show content lines only.
- Base function shas (LF, `ast.get_source_segment`): `_read_valid_device_fingerprint` (:478-496)
  06a65002947475c54d5d0a41134b2501d0152617f604fe95dfbeaebbdb9f9bec; `_inherit_device_counter`
  (:499-537) 11c4de26aaed05f39e26c2203f4267f54126887a00f32c64064c2cf66612da04 (both must stay
  byte-identical: PIN P13); `_apply_social_device_fingerprint` (:540-579)
  22e65151d77e08d56c1d52ebe2bfe27da4fa1d4dd9663764692c2ef6c7512893 (changes: 3).

-----------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag and readers

| Name | Where | Rule |
|---|---|---|
| `ENABLE_LEGACY_FINGERPRINT_READER` | `auth_routes.legacy_fingerprint_reader_enabled()` | `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, never cached |
| `X-Device-Fingerprint-Legacy` | `auth_routes._read_valid_legacy_fingerprint(request, fp)` | FIRST statement: the flag read; OFF -> return None without touching `request`. ON -> `request.headers.get("X-Device-Fingerprint-Legacy")` inside `try/except Exception -> None`; valid iff `isinstance(raw, str) and _DEVICE_FINGERPRINT_RE.fullmatch(raw)` (FULL match: a trailing newline, upper case, 63 / 65 chars, an empty value are invalid); a valid value EQUAL to `fp` -> None (nothing new to accept); else the value. Never raises, never logs, never 400 |

The helper is called ONLY after a valid NEW value is in hand (`if fp and new_user_id:` at register;
after `if not fp or not user_id: return` at social). Legacy without NEW = no inheritance, as today
(the NEW value is what gets stored; with none there is nothing to store).

### 2.2 The match under the flag (two sites)

New function `_inherit_device_counter_with_legacy(admin_client, fp, legacy, user_id, *, floor=0,
site)` beside `_inherit_device_counter` (whose body stays byte-identical, P13):

1. `admin_client.table("users").select("lifetime_comparisons_used, device_fingerprint_hash")
   .in_("device_fingerprint_hash", [fp, legacy]).order("lifetime_comparisons_used", desc=True)
   .limit(1).execute()`: the rule `stored == NEW OR stored == LEGACY` as ONE indexed read.
2. `inherited = max(floor, (prior.data[0].get("lifetime_comparisons_used", 0) or 0) if prior.data else 0)`
   (the base arithmetic).
3. `admin_client.table("users").update({"device_fingerprint_hash": fp, "lifetime_comparisons_used":
   inherited}).eq("id", user_id).execute()`: the NEW value is stored, never the legacy one; the same
   single row as today.
4. ONE INFO line: `[LEGACY-FP] site=%s top=%s` with site in {`register`, `social`} and top = `legacy`
   (the max-holding row's stored hash equals the legacy value), `new` (it equals the NEW value) or
   `none` (no row). Constants only.
5. The whole body sits in `try/except Exception as exc` -> ONE WARNING `[LEGACY-FP] site=%s inherit
   failed: %s` with `type(exc).__name__`; the function never raises (so the register except arm, which
   logs `str(exc)`, never sees an exception that could carry the legacy value in a query echo).

Call sites: register `if legacy is None: <the base call verbatim> else:
_inherit_device_counter_with_legacy(get_admin_supabase_client(), fp, legacy, new_user_id,
site="register")` inside the existing try; social `if legacy is None: <the base call verbatim, floor
unchanged> else: _inherit_device_counter_with_legacy(admin, fp, legacy, user_id, floor=<the same
floor expression>, site="social")`. The social route itself (:1171-1172) is unchanged: the legacy
reader at social is reachable only when W3-3 is ON (prod UNKNOWN; with W3-3 OFF this unit is inert
there, P6).

### 2.3 New keys and types

No response key, status, header or OpenAPI change on any route (contract freeze: PLAN_S80 section 0
items 3-5; contract_freeze.json finding 3 lists the share body and the register / social header; none
changes). New code symbols only: `legacy_fingerprint_reader_enabled() -> bool`,
`_read_valid_legacy_fingerprint(request, fp: Optional[str]) -> Optional[str]`,
`_inherit_device_counter_with_legacy(admin_client, fp: str, legacy: str, user_id: str, *, floor: int =
0, site: str) -> None`. New log templates: the INFO and WARNING of 2.2.

### 2.4 Upgrade-on-match (open question b): NONE

Measured: register writes only the caller's own row (:531-537 `.eq("id", user_id)`), never a sibling,
so rewriting a legacy-matched sibling row would be a NEW write path (forbidden by the brief). Social
writes the column only when the own row's hash is NULL (:566); rewriting an own row that already
stores the legacy value would turn the first-device binding into an overwrite driven by a client-claimed
header: a client could send legacy = its stored value and NEW = any 64-hex string and move its stored
hash, the exact attack the W3-3 docstring (:544-548) guards against (`_referrer_device_lifetime_count`
then misses that account). So: no upgrade anywhere; P5 pins `SOCIAL_BASE_OWNED` (5 calls) under the
flag. Index implication: none (1.6). Effect on the transition: the counter is still CARRIED FORWARD,
because each post-OTA registration on a device writes a NEW-hash row holding max(NEW rows, LEGACY rows);
after the cutoff the NEW chain alone carries the device's history for every device that registered
once inside the window.

### 2.5 Failure table

| Condition | Flag OFF | Flag ON |
|---|---|---|
| no legacy header (build 3) | base | base (REG_BASE / SOCIAL_BASE_*) |
| legacy invalid (case, length, trailing newline, empty, non-ASCII) | base | base, silently (no log) |
| legacy == NEW | base | base |
| legacy valid, NEW absent or invalid | base (no DB) | base (no DB) |
| legacy valid, NEW valid, register | base | dual read, store NEW, INFO line |
| legacy valid, NEW valid, social, W3-3 OFF | base (no DB) | base (no DB) |
| legacy valid, NEW valid, social, W3-3 ON, own hash NULL | base | dual read with floor, store NEW, INFO line |
| legacy valid, social, own hash set (incl. = legacy) | base (5 calls) | base (5 calls, no upgrade) |
| dual read or update raises | n/a | WARNING type name; register / social response unchanged; no inheritance write |
| `get_admin_supabase_client()` raises at register | base except arm | the same base except arm (unchanged text) |
| header read raises | n/a | helper returns None -> base |
| share with legacy header | base | base (header ignored) |

Never a 400, never a bare 503, never a new code: the routes' responses are untouched (the reader only
changes a DB filter).

### 2.6 The main invariant: flag-OFF identity (and the build-3 identity)

Flag OFF: the helper reads the flag and returns None; register and social then execute the base
statements verbatim: REG_BASE, SOCIAL_BASE_NULL, SOCIAL_BASE_OWNED, the same response bodies, the same
log lines (pinned as literal call lists, P1 / P5, under the FULL configuration: the legacy header sent
and valid, `ENABLE_SOCIAL_DEVICE_FINGERPRINT=true`, `ENABLE_REQUEST_CONTEXT_HEADERS=true`,
`ENABLE_REFERRAL_SYSTEM=true`, `DEVICE_KEY_PEPPER` synthetic (set after importing app.main), plus a
call recorder). Flag ON with no / invalid / NEW-equal legacy header: the same literals (P2, P3).

### 2.7 Test seams (production values in brackets)

`app.api.auth_routes.get_admin_supabase_client` [the service-role client], `app.api.auth_routes.register_user`
/ `sign_in_with_social` [Supabase Auth], the limiter `enabled` attribute [True], the flag env var
[unset], an in-memory `FakeUsers` table that EVALUATES `eq` / `in_` / `order` / `limit` and records
every call [PostgREST]. No new production seam.

### 2.8 No backend cutoff

The backend has no date logic: after 2027-03-31T21:00Z the client stops sending the header (S81-08
runtime cutoff) and both matches degrade to NEW-only by header absence (= the P2 identity). S81-08c
removes the helper, the dual function and the flag after the cutoff (follow-up row).

### 2.9 Open question d: is a flag needed?

Measured facts: (1) with the header absent the ON path is byte-identical (P2), and build 3 never sends
it; (2) a request that DOES carry it (any client can forge one today) changes the DB filter, so an
unflagged reader is byte-identical only by the client contract, not totally; (3) the reader is
monotone-safe (it can only RAISE the new row's inherited counter and always stores NEW), so a forged
header gains an attacker nothing; (4) R-A1 admits unflagged only allowlist widenings, log-only changes
and changes proven byte-identical. Recommendation: keep it FLAGGED (the orchestrator default): a per-call
kill switch for the transition window, total flag-OFF identity, and one more flip (ON before the first
post-approval OTA). The reader does not depend on `ENABLE_REQUEST_CONTEXT_HEADERS` (route-level read).

-----------------------------------------------------------------------------------------------------

## 3. Change list (in the order GREEN applies it)

0. Byte copies (Python `shutil.copyfile`) of `app/api/auth_routes.py` and `CLAUDE.md` with their sha256
   recorded before the first edit.
1. `app/api/auth_routes.py` (Edit tool; CRLF preserved; ASCII-only added lines):
   a. after `social_device_fingerprint_enabled` (:395-418): `legacy_fingerprint_reader_enabled()` with a
      docstring naming S81-08 R-S08-4, the cutoff, S81-08c and the default OFF.
   b. after `_read_valid_device_fingerprint` (:478-496, unchanged): `_read_valid_legacy_fingerprint` (2.1).
   c. after `_inherit_device_counter` (:499-537, unchanged): `_inherit_device_counter_with_legacy` (2.2).
   d. `_apply_social_device_fingerprint` (:540-579): `legacy = _read_valid_legacy_fingerprint(request,
      fp)` right after the `if not fp or not user_id: return` guard (outside the try; the helper is
      total); the `_inherit_device_counter(` call (:571-576) becomes the `if legacy is None:` base call
      verbatim / `else:` the dual call with the same floor and `site="social"`.
   e. register (:624-629): inside `if fp and new_user_id:`, before `try:`, `legacy =
      _read_valid_legacy_fingerprint(request, fp)`; inside the try the base call verbatim under `if legacy
      is None:`, else the dual call with `site="register"`; the except arm unchanged.
2. `CLAUDE.md`: (a) the section-8 row after the S81-04 row (:494-495; after S81-14's :497 at rebase);
   (b) the Environment Variables **Feature Flags** list (:341) gains one pointer sentence after the
   S81-04 one: "`ENABLE_LEGACY_FINGERPRINT_READER` (S81-08b LEGACY-FINGERPRINT-READER, default OFF): the
   row of the **SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, ...)** block."; (c) the Auth +
   security hardening bullet (:231) gains, in place: "Under `ENABLE_LEGACY_FINGERPRINT_READER` (S81-08b)
   register and the W3-3 social apply also accept `X-Device-Fingerprint-Legacy` (same shape, full match,
   silently dropped) as a second match key; the stored value is always `X-Device-Fingerprint`."
3. `tests/test_s81_s08b_legacy_fingerprint.py` (written at RED; GREEN does not edit it).

No other file (no migration, no client file, no sentry_service change, no middleware or leaf change,
no `tests/test_s75_fanout_identity.py` change, no `.github/black-clean-paths.txt` change).

-----------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately

NONE. Measured reasons per brief-named candidate: the W3-3 pins (`test_social_login_device_fingerprint.py`)
run with the new flag unset -> the base path, call-for-call (they assert `device.eq.assert_called_once_with
("device_fingerprint_hash", FP)`, which stays true); the register pins
(`test_auth_routes_invite_fingerprint.py`, `test_usage_device_inheritance.py`) send no legacy header;
the SAME_DEVICE / referral pins (`test_abuse_detection*`, `test_referral_*`) cover code this unit does
not touch; `tests/test_security_regression.py` contains no device / fingerprint text at all (grep 0: the
brief's "regex drop" pin there does not exist); `tests/test_s81_s05_request_context.py` is untouched
(route-level read, 1.7); FY25 `test_s75_fanout_identity.py` UNIT_ENV is NOT edited (the flag is never
read on a compare path, and S81-14's IDENTITY_NODES pins that file's sha); T23 stays (no Header param).
If GREEN finds any of these red, it is a defect in GREEN, not a pin to move.

### 4.2 Pins that must stay green and unedited

test_social_login_device_fingerprint.py, test_auth_routes_invite_fingerprint.py,
test_usage_device_inheritance.py, test_s81_s05_request_context.py (r08, p01, p02, p05, p06, p07),
test_sentry_channels_u8d_unit.py (R10), test_consent_capture_w3_16.py, test_s79_b3b_apple_revoke.py,
test_security_regression.py, test_abuse_detection.py, test_abuse_detection_internals.py,
test_referral_loop2.py, test_referral_lifetime_cap.py, test_referral_service.py,
test_referral_share_status_lifetime.py, test_referral_e2e.py, test_u3c_referral_push_name.py,
test_s71_u13_compare_auth_required.py (T23), test_s75_fanout_identity.py (FY25), test_ci_gates.py,
test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py (r38), and after rebase
test_s81_kb_schema.py (IDENTITY_NODES). All green at base (1.10).

-----------------------------------------------------------------------------------------------------

## 5. RED tests (`tests/test_s81_s08b_legacy_fingerprint.py`)

Hermetic: imports `app.main` first (autouse), disables the limiter, `monkeypatch.delenv` of the flag in
an autouse fixture, every DB through `FakeUsers` (evaluates `eq` / `in_` / `order(desc)` / `limit` over
seeded rows and records `[method, args, kwargs]` in order; `update` records the payload; an optional
`raise_on={"in_"}`), `register_user` / `sign_in_with_social` patched in the auth_routes namespace,
`get_current_user` overridden for share, `ReferralService` patched in referral_routes for share.
NEW = sha256(b"s81-08b-new"), LEG = sha256(b"s81-08b-legacy"), OTHER = sha256(b"s81-08b-other"), UID a
synthetic uuid; built at run time. Missing symbols are read with `getattr(auth_routes, name, None)` and
asserted (never an ImportError). FULL = the configuration of 2.6. OFF spellings: unset, "", "false",
"0", "off", "no", "garbage"; ON spellings: "true", "TRUE", " true ", "1", "yes", "on". Literal call lists
REG_BASE / SOCIAL_BASE_NULL / SOCIAL_BASE_OWNED are recorded in the file from `probe_out.json` (with
NEW / UID substituted at run time) and asserted equal.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | flag reader idiom | `legacy_fingerprint_reader_enabled` callable; OFF spellings -> False, ON spellings -> True, read per call (setenv between two calls flips it) | RED (missing) | 1a |
| R2 | helper truth table | ON: LEG -> LEG; LEG.upper(), LEG[:63], LEG+"0", LEG+"\n", "" , absent -> None; LEG with fp=LEG -> None; a headers mapping that raises on get -> None; OFF (every spelling): None AND a recording headers mapping saw 0 reads | RED (missing) | 1b |
| R3 | register dual read, legacy max | FULL + ON + headers NEW/LEG; FakeUsers rows {LEG:3},{NEW:1},{OTHER:9}: call list == REG_LEGACY literal (select "lifetime_comparisons_used, device_fingerprint_hash", in_ [NEW, LEG], order desc, limit 1, then update {hash: NEW, lcu: 3}, eq id UID); response == the register_user payload | RED (eq NEW; writes lcu 1) | 1c, 1e |
| R4 | register stores NEW, NEW max | rows {NEW:5},{LEG:3}: update {hash: NEW, lcu: 5}; LEG appears in no update payload in any R row | RED (base never sends in_; R4 runs the R3 list check too) | 1c |
| R5 | social dual read with floor | FULL + ON, W3-3 ON, own row NULL; parametrized: own lcu 1 + rows {LEG:4} -> update {hash: NEW, lcu: 4}; own lcu 6 + rows {LEG:4} -> lcu 6 (the floor); call list == SOCIAL_LEGACY literal (own read 5 calls, then the dual read, then the update) | RED (both params: the base call list carries `.eq(NEW)`, not `in_`; the first param also writes 1) | 1c, 1d |
| R6 | INFO line, constants only | R3 -> exactly one record `[LEGACY-FP] site=register top=legacy` at INFO; caplog at DEBUG never contains NEW, LEG or UID anywhere in R3-R9 | RED (no record) | 1c |
| R7 | social INFO line | R5 -> one `[LEGACY-FP] site=social top=legacy` | RED | 1c |
| R8 | top=new / top=none | rows {NEW:5},{LEG:3} -> `top=new`; no rows -> `top=none` AND the update is still written {hash: NEW, lcu: 0} | RED | 1c |
| R9 | dual failure is silent and typed | FakeUsers raises RuntimeError("boom " + LEG) on `in_` execute: register 200, body unchanged, one WARNING `[LEGACY-FP] site=register inherit failed: RuntimeError`, no base `device-fp inheritance failed` line, LEG not in caplog; social the same with `site=social` | RED (no warning; base never calls in_) | 1c |
| R10 | one reader in app/ | exactly one file under app/ contains `x-device-fingerprint-legacy` (case-insensitive): app/api/auth_routes.py; and `legacy_fingerprint_reader_enabled` is the first statement of `_read_valid_legacy_fingerprint` (AST) | RED (0 files) | 1a, 1b |
| R11 | CLAUDE.md row | a `**SESSION 81 flag (S81-08b` heading exists; its row (to the next `\n**SESSION`) names `ENABLE_LEGACY_FINGERPRINT_READER`, `X-Device-Fingerprint-Legacy`, `register`, `social`, `SAME_DEVICE`, `2027-03-31`, `S81-08`, `S81-08c`, `rollback`; the Feature Flags paragraph names the flag | RED | 2 |
| P1 | flag OFF identity, register | FULL + every OFF spelling + headers NEW/LEG: call list == REG_BASE; body == payload; no `[LEGACY-FP]` record | PIN | base + 1e |
| P2 | build-3 identity, register | FULL + ON + NEW only: REG_BASE | PIN | base + 1b |
| P3 | invalid / equal legacy, register | FULL + ON + NEW + each invalid legacy (R2 list) and legacy == NEW: REG_BASE | PIN | base + 1b |
| P4 | legacy without NEW | FULL, ON and OFF, legacy only: zero FakeUsers calls; get_admin_supabase_client not called | PIN | base + 1e |
| P5 | social identity, no upgrade | FULL + W3-3 ON, flag OFF: own NULL -> SOCIAL_BASE_NULL, own = LEG -> SOCIAL_BASE_OWNED; flag ON + own = LEG -> SOCIAL_BASE_OWNED (no write) | PIN | base + 1d |
| P6 | social with W3-3 OFF | FULL minus W3-3, flag ON, both headers: get_admin_supabase_client call count 0; body == SUCCESS | PIN | base |
| P7 | social build-3 identity | W3-3 ON + flag ON + NEW only: SOCIAL_BASE_NULL | PIN | base + 1b |
| P8 | share untouched | flag OFF and ON, FULL, body NEW + header LEG: 201, `create_invite` kwargs == the 1.4 literal (body NEW); upper-case body -> 422 in both states | PIN | base |
| P9 | Sentry redaction | `_before_send` and `_before_send_transaction` on headers `x-device-fingerprint-legacy` and `X-Device-Fingerprint-Legacy` = LEG -> `[Filtered]` | PIN | base |
| P10 | OpenAPI | `app.openapi()` declares no parameter whose name contains `fingerprint` (both flag states) | PIN | base |
| P11 | SAME_DEVICE untouched (scope pin) | the real `_load_invitee` select string == `"id, email, subscription_tier, display_name"`; `evaluate_invite` over the loaded invitee reads the referrer hash 0 times, both flag states (a later unit that revives SAME_DEVICE lists this node in its 4.1) | PIN | base |
| P12 | lifetime cap untouched | `_referrer_device_lifetime_count` with a recording client: select `device_fingerprint_hash` then `.eq("device_fingerprint_hash", <stored>)`, both flag states | PIN | base |
| P13 | base functions byte-identical | LF sha256 of `ast.get_source_segment` of `_read_valid_device_fingerprint` and `_inherit_device_counter` == the 1.11 literals | PIN | base |
| P14 | leaf import shape | auth_routes imports exactly `DEVICE_FINGERPRINT_RE as _DEVICE_FINGERPRINT_RE` from the leaf (mirror of r08, so a GREEN mutant that imports `parse_device_fingerprint` reddens this file too) | PIN | base |

Counts: RED 11, PIN 14 (parametrized nodes multiply them; the RED report states node counts). A tester
scenario from `eval_regression.json` does not apply (it records compare quality; 0 hits for register /
social / fingerprint, measured).

-----------------------------------------------------------------------------------------------------

## 6. Mutation table (each on a byte copy of auth_routes.py; restored from the copy, sha256 compared)

| # | mutant (exact-string edit) | killed by |
|---|---|---|
| M1 | flag reader returns True | P1 |
| M2 | flag reader without `.strip().lower()` | R1 (" true ", "TRUE") |
| M3 | `.fullmatch(` -> `.match(` in the legacy helper | R2 (LEG + "\n") |
| M4 | the `raw == fp` dedupe removed | P3 (legacy == NEW must give REG_BASE, not in_ [NEW, NEW]) |
| M5 | the update stores `legacy` instead of `fp` | R3, R4 |
| M6 | `in_` list `[legacy]` only | R4 (NEW max 5) |
| M7 | `desc=True` -> `desc=False` in the dual read | R3 (call literal; FakeUsers returns min) |
| M8 | the header read before the flag read | R2 (OFF recorder 0 reads) |
| M9 | the INFO line formats the legacy value | R6 (sentinel) |
| M10 | the dual function's except arm removed (exception propagates to the register arm) | R9 |
| M11 | social upgrade-on-match (own == legacy -> dual write) | P5 (SOCIAL_BASE_OWNED under ON) |
| M12 | register consults legacy when NEW is absent | P4 |
| M13 | register always uses the dual function (legacy None -> in_ [fp, None]) | P2 |
| M14 | top computed from the NEW comparison only (legacy reads as new) | R6 / R8 |
| M15 | dual function skips the update when no rows | R8 (top=none still writes) |
| M16 | social call passes `floor=0` instead of the own counter | R5 (the own-6 parameter: 4 written instead of 6) |

Each mutant: byte copy, one exact-string edit matching once, the killing rows via pyt.py -k (bound 600),
restore, sha256 compare; MUTATION LOCK `<worktree>/.qa-mutation.lock` for the duration. Equivalent
survivors are reported for a ruling.

-----------------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first)

### 7.1 Comm set (222 files, `<scratchpad>/s81-08b/comm_files.txt`, nine chunks `comm_chunk_00..08`)

Union, measured at base: (a) module-reference grep for the edited module `auth_routes` (68 files)
UNION its importer `app.main` / `app/main.py` (105) UNION `referral_routes` (10, the share PIN);
(b) the source-scanning pins test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py,
test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py,
test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py (8), every test walking app/ by
path or module (`rglob(`, `os.walk(`, `glob("app`, `iterdir(`, `os.listdir(`, `scandir(`,
`inspect.getsource`, `__file__).read_text`, `"app" /` joins, `.github` readers: 94) and every test that
names an `app/api/`, `app/services/`, `app/utils/` or `app/middleware/` path or `auth_routes.py` (78);
(c) the CLAUDE.md readers test_ci_gates.py, test_behavior_dimension_translation.py,
test_s81_s04_spend_breaker.py (measured: the only three that read the file) + T23
test_s71_u13_compare_auth_required.py + FY25 test_s75_fanout_identity.py + test_w4_13_flag_off_ledger.py;
(d) the SmartCompareApp-scanning backend tests (25; the client sends the header); (e) every test
mentioning a fingerprint (31). MINUS the four test_precommit_hook*.py. No edited test-support module.
At rebase onto 86d5a24d+ add tests/test_s81_kb_schema.py and re-derive the union at head (the new
unit file joins). Base and head, chunks of <= 25, bound 1200 each, `comm -13` of the sorted FAILED
node-id sets EMPTY. Base NOT MEASURED by this spec (GREEN records it in a detached scratch worktree at
the base).

### 7.2 Gates, in order

| # | gate | rule |
|---|---|---|
| G1 | bytes | added lines pure ASCII (count bytes > 127 in the diff hunks only: auth_routes carries 61 pre-existing non-ASCII chars); CRLF kept; `git diff --stat` content lines only |
| G2 | syntax / lint | `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on app/api/auth_routes.py and the unit file |
| G3 | unit file | `pyt.py --bound 600 --tag s08b-head-unit -- tests/test_s81_s08b_legacy_fingerprint.py`: all green |
| G4 | pins | the 1.10 sets A and B at head: green, counts equal to base (599 / 661+1 skipped) |
| G5 | flag ON sweep | ONE runner call with `ENABLE_LEGACY_FINGERPRINT_READER=true` exported for that call only over set A + set B: green (no existing test sends the legacy header, so ON == OFF for them) |
| G6 | mutation | section 6, each KILLED by its row |
| G7 | comm | 7.1 base vs head, `comm -13` empty |
| G8 | hook | the commit through `.githooks/pre-commit`, never `--no-verify` |

-----------------------------------------------------------------------------------------------------

## 8. CLAUDE.md row and owner steps (names only)

Row text (one paragraph heading + one bullet, after the newest SESSION 81 row):

**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, 2026-10-24; default OFF, read PER CALL; a new
name, so unset in production by construction (Railway not read); the backend half of S81-08
CLIENT-FIRST-OTA (RULINGS_S81_08 R-S08-4 / R-S08-7); spec `.qa-s80/S81-08b_UNIT_SPEC.md` of the unit
worktree with its review and rulings in `docs/investigations/2026-10-22-session-81-state/specs/`):**
- `ENABLE_LEGACY_FINGERPRINT_READER` (S81-08b, `app/api/auth_routes.py::legacy_fingerprint_reader_enabled`,
  read per call as the first statement of `_read_valid_legacy_fingerprint`). **Effect ON:** at POST
  `/api/v1/auth/register` and in the W3-3 social apply (`_apply_social_device_fingerprint`, reachable only
  with `ENABLE_SOCIAL_DEVICE_FINGERPRINT` ON) a request that carries a valid `X-Device-Fingerprint` AND an
  `X-Device-Fingerprint-Legacy` header (64 lower-case hex, full match; invalid, empty or equal to the
  primary value -> silently ignored, never a 400) inherits the device counter from
  `users.device_fingerprint_hash IN (primary, legacy)` (one indexed read on
  `idx_users_device_fingerprint_active`) instead of `= primary`; the row written still stores the
  PRIMARY value; one INFO `[LEGACY-FP] site=register|social top=legacy|new|none` per such request, a
  failure one WARNING `[LEGACY-FP] site=... inherit failed: <Type>`; no value is ever logged; no
  response, status or OpenAPI change. **Why:** after the S81-08 OTA the client's primary header carries
  the NEW SecureStore-id hash while every stored row holds the build-3 composition, which the client
  sends as the legacy header at register, both social sign-ins and the share call until
  2027-03-31T21:00Z (client runtime cutoff; no backend date logic: after it the match degrades to
  primary-only by header absence; S81-08c removes this reader). **Flag OFF, or ON without the legacy
  header (build 3):** byte-identical (literal call-list pins). **Not covered (measured):** the share path
  stores the body value and matches nothing (the legacy header there has no consumer); the invite and
  quiz routes read no fingerprint; SAME_DEVICE (`abuse_detection_service.evaluate_invite`) and the
  referral device lifetime cap compare STORED values on the invitee's first compare (a request with no
  legacy header), so a pre-OTA account (legacy hash) and a post-OTA account (new hash) on one device are
  two buckets for the cap (at most one extra cap of 3 lifetime invites per device across the
  transition); SAME_DEVICE is unreachable in production at base (`_load_invitee` selects no device
  hash); no upgrade-on-match (no stored row is rewritten). **Activation order:** after S81-08 merges and
  BEFORE the first post-approval OTA (the DEFECT_LEDGER precondition), in the same window as
  `ENABLE_REQUEST_CONTEXT_HEADERS` (independent: the read is route-level); canary: after the OTA, a
  re-signup on a pre-OTA test device logs `[LEGACY-FP] site=register top=legacy` and inherits the old
  counter. **Rollback:** unset the variable (per call, immediate).

Owner steps (names only): set `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` before the first
post-approval OTA; nothing else (no migration, no credential, no pepper).

-----------------------------------------------------------------------------------------------------

## 9. Stated limits

1. Two request-time matches only (register, W3-3 social). With W3-3 OFF in production the social half is
   inert; social users stay unbound as today.
2. SAME_DEVICE is dead at base and stays dead; even revived, it is stored-vs-stored, out of reach of a
   header (Q1, Q2).
3. The referral device lifetime cap splits across the transition (legacy-hash accounts vs new-hash
   accounts on one device): bounded to one extra cap (3 lifetime invites) per device; needs
   `ENABLE_REFERRAL_SYSTEM` ON.
4. After the cutoff a device with NO registration inside the window loses its link to legacy-hash rows
   (the carried-forward counter exists only for devices that re-registered once inside the window).
5. The legacy header is a client claim; the reader is monotone (it can only raise the inherited counter
   and always stores the primary value), so a forged header buys nothing; a client can still escape
   inheritance by sending a random primary value, exactly as today.
6. The register except arm keeps logging `str(exc)` (pre-existing, flag-independent); the dual path never
   reaches it.
7. The anon usage gate (`anon:{fp}` Redis keys, `ENABLE_ANON_USAGE_GATE`) starts fresh counters for the
   new value after the OTA; compares carry no legacy header (R-S08-5) and anonymous compares are 401
   under `ENABLE_COMPARE_AUTH_REQUIRED` (ON since 2026-10-03).
8. The partial-index claim (1.6) is reasoned, not measured on a database.
9. The comm set base run is not measured here.

## 10. Out of scope

Any client change (S81-08); a migration or a dual-stored column; reviving SAME_DEVICE (`_load_invitee`
select); rewriting stored rows (upgrade-on-match); the anon gate keys; S81-05's middleware or leaf;
Sentry code; S81-08c (removal after the cutoff); S81-09's device keys.

## 11. Open questions for the orchestrator

- Q1 (MAJOR, new defect row): SAME_DEVICE is unreachable in production at base (`_load_invitee`
  selects no `device_fingerprint_hash`, referral_service.py:762; probe: 0 referrer-hash reads). Reviving
  it (one select column) changes production behaviour, so it needs its own flagged unit; this spec
  leaves it untouched and pins that (P11).
- Q2: the device lifetime cap and a revived SAME_DEVICE can survive the transition only with a
  dual-stored value or a rewrite of stored rows (both excluded here). Rule: accept limit 3, or open a
  follow-up (a migration adding a legacy column written at register under this flag; a one-off
  backfill is impossible: the server never saw the new value for the old rows).
- Q3: the legacy header at the share path has no backend consumer (1.4). S81-08 may drop it there
  (one fewer osBuildId read) or keep it; this unit is indifferent (P8).
- Q4: FLAGGED kept (2.9). Confirm, or rule unflagged with R-A1 reasoning.
- Q5: no INFO line for an invalid legacy header (silent, like "dropped"); the primary header logs its
  length at INFO. Confirm silence (fewer log lines) over a count line.

## Not done in this spec

The comm-set base run; the RED file; any edit in the worktree other than this spec.
