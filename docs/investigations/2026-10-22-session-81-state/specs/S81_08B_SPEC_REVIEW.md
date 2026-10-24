# S81-08b LEGACY-FINGERPRINT-READER: adversarial spec review

- Unit: S81-08b LEGACY-FINGERPRINT-READER (lane B backend; flag ENABLE_LEGACY_FINGERPRINT_READER).
- Spec under review: `.qa-s80/S81-08b_UNIT_SPEC.md` of worktree sc-s81-s08b, sha256
  920fb599f82d61b455ddc20e6d692da3d7c6d962c0ce7d2ff120952f8bc5da14 (re-hashed first: match), 52,933 B.
- Base for every measurement: ea3aef15bb234bc7fe3776858556f4782ac40e49 (worktree HEAD verified;
  `git status --short` empty before and after; no file in the worktree edited except this review).
- Reviewer: adversarial spec reviewer (Opus 5.5), 2026-10-24 18:52-20:05 AST. Box under load (a plain
  `ls` 10.6 s, `node -e 0` 2.5 s, several greps over the docs checkout > 120 s): one bounded pytest run only.
- Notes and probes: `<scratchpad>/s81-08b-review/` (notes.md, probe_claude_md.py/.out,
  probe_fn_sha.py/.out, adv_pins.log). Probes are read-only (no scratch worktree was needed: every
  probe reads files or runs existing tests).
- Personal-data rule respected: no fingerprint, id or e-mail value appears in this review.

## Verdict: APPROVE_WITH_CHANGES

The measured core of the spec holds. I re-derived every load-bearing claim at the base and could not
refute the design: exactly two request-time stored-row matches exist (register and the W3-3 social
apply, both through `_inherit_device_counter`); SAME_DEVICE is unreachable in production; the share path
stores the body value and matches nothing; the base function shas, the call lists, the Sentry
allowlist behaviour and the comm-set membership all reproduce. The route-level read (open question a),
no upgrade-on-match (b), body-stored / header-ignored at share (c) and FLAGGED (d) are each supported by
measurement.

Two items must be settled before RED (BL1, BL2), one guard pin is missing (C1), one RED row is partly
vacuous (C2), and the activation text contradicts the binding plan (BL1). None changes the code design.

## Gate evidence (this review)

`[pyt] tag=s08b-adv-pins start=2026-10-24 19:39:55 end=2026-10-24 19:40:42 elapsed=48s bound=600s status=OK rc=0`
over tests/test_s81_s05_request_context.py + tests/test_social_login_device_fingerprint.py +
tests/test_auth_routes_invite_fingerprint.py with `-k "p01 or p06 or p07 or p08 or r08 or b1 or b3 or b5
or b9 or fingerprint"`: `48 passed, 169 deselected, 13 warnings in 35.36s`;
`[hermeticity] sentinel checked 48 test(s)`; `[netguard] blocked 2 attempt(s) from 2 node(s)` (both
`neutralized.supabase.invalid:443` sentinel attempts in test_auth_routes_invite_fingerprint.py, the
pre-existing sentinel class).

## Re-measured and CONFIRMED (file:line at ea3aef15)

| Claim | Measured |
|---|---|
| auth_routes reader / inherit / social apply / register / social route spans | `_read_valid_device_fingerprint` 478-496, `_inherit_device_counter` 499-537, `_apply_social_device_fingerprint` 540-579, `register` def 584-683 (decorators 582-583), `social_login` 1160-1184, W3-3 call 1171-1172, own-hash early return 566, fp read 624, inherit call 627, `str(exc)` WARNING 629 |
| P13 / 1.11 base shas (LF, ast.get_source_segment) | 06a65002...9bec, 11c4de26...2da04, 22e65151...2893: all three equal the spec; file LF sha 5add302d...0d98be2, 1,650 CRLF, 67,765 B |
| auth_service has no fingerprint reference | Grep -i fingerprint app/services/auth_service.py: 0 |
| app/ fingerprint census (1.1) | 11 files, 100 occurrences; counts per file equal the table |
| no other stored-row match | `device_fingerprint_hash` outside auth_routes / referral_service / abuse_detection_service: only referral_routes.py:117, :209; scripts/: 0; migrations: only 014, 021, 023, 025, 032, 043 (column, indexes, cascade NULLs) |
| SAME_DEVICE unreachable | referral_service.py:762 selects `id, email, subscription_tier, display_name`; the fallback dict (:655-658) has no hash either; abuse_detection_service.py:249 reads the absent key, :124-125 returns False first; `evaluate_invite` has exactly one caller (referral_service.py:664) |
| device lifetime cap stored-vs-stored | referral_service.py:772-812 (`.eq("id")` then `.eq("device_fingerprint_hash", fp)` of the STORED value) |
| share stores the body, matches nothing | referral_routes.py:117-119 pattern, :205-213 call; referral_service.py:318-325 payload; ShareRequest `extra: ignore` (:108) |
| invite / quiz read no fingerprint | referral_routes.py has 3 fingerprint references (:115 comment, :117, :209) |
| index facts | 021 partial index; 023 `idx_users_device_fingerprint_active`; 032:38-43 drops the 021 duplicate |
| Sentry | sentry_service.py:183-186 allowlist, :463-466 deny/[Filtered]; probe_out.json sentry block: all six `[Filtered]` |
| S81-05 guards | test_s81_s05_request_context.py r08 :527-553, p01 :1325-1369, p02 :1382-1392, p06 :1540-1555, p07 :1558-1564 |
| comm set covers the reference greps | every tests/*.py naming `auth_routes`, `fingerprint`, `request_context` or `referral_routes` is in comm_files.txt (loop over the four greps: 0 missing) |
| FY25 identity sha pinned by S81-14 | `git show 86d5a24d:tests/test_s81_kb_schema.py` :412-428 IDENTITY_NODES (FY25 file, FY25 fixture, W4-13 ledger + fixture) |
| no in-flight S81 branch edits auth_routes.py | `git diff --name-only ea3aef15...<branch> -- app/api/auth_routes.py` over every S81 ref: none |

## Refuted claims (each with the measured truth)

RF1 (MAJOR; spec section 8 row "Activation order", owner steps; also the brief item 7 and the
session-81 ledger :82). Claim: S81-08b flips "after S81-08 merges and BEFORE the first post-approval OTA
..., in the same window as `ENABLE_REQUEST_CONTEXT_HEADERS`". Measured: PLAN_S81.md:185 (binding flip
order) is "LEGAL-V3 merged + backend + landing deployed -> the first OTA (S81-08 + S81-11 + consent v3
copy) -> ledger, breaker, request context ON -> ...", and the merged S81-05 row in CLAUDE.md says
`ENABLE_REQUEST_CONTEXT_HEADERS` flips "after the S81-08 OTA has propagated, in its own canary window".
Request context therefore flips AFTER the OTA and S81-08b must be ON BEFORE it: they cannot share a
window. Followed literally, the row would put the reader ON after the OTA and miss the DEFECT_LEDGER
precondition. "After S81-08 merges" is also unnecessary: the reader is client-independent and inert for
build 3 (P2 / P7), so it can be ON from its own deploy. See BL1.

RF2 (MINOR; header "Contracts consumed"). Claim: "R-S08-5 (no legacy header on compares / usage /
camera / SSE)". Measured: RULINGS_S81_08.md:12 (R-S08-5) is the ALLOWLIST of metered requests that carry
the device and consent headers; the rule that the legacy header rides "never on compares, usage status
or any other request" is R-S08-4 (:9). The fact is right; the citation is wrong (it matters because the
S81-08 spec's pre-ruling row B1, S81_08_UNIT_SPEC.md:529, still expects the legacy header on
`/usage/status`; R-S08-4 and that review's C8 override it, and a RED written from the wrong ruling id
would cite the wrong authority).

RF3 (MINOR; section 0 "Every users.device_fingerprint_hash row written before the OTA holds the LEGACY
composition" and 2.4 "carried forward"). Measured: the legacy value is recomputed by the client with the
CURRENT osBuildId (migration 021 COMMENT names bundle id + osBuildId + nonce; the S81-08 spec row A4
pins the digest input `app.qaren.test|<osBuildId>|<nonce>`). A row written under an earlier OS build
does not equal today's legacy header, exactly as it does not equal today's primary header at base. The
reader recovers only rows written under the device's current OS build (and app id and nonce). Not a
design defect; a missing stated limit (C3).

RF4 (MINOR; stated limit 7 "The anon usage gate ... starts fresh counters for the new value after the
OTA"). Measured: build 3 never sends `X-Device-Fingerprint` on `/text/quick` or `/image/identify`
(S81-05 stated limit 1; image_routes.py:227 and text_routes.py:1405 read it, but no build-3 call site
sets it); R-S08-5 adds it with the OTA. No `anon:<legacy>` counter can exist, so nothing is lost; the
limit as written describes a loss that cannot happen (C4).

RF5 (TRIVIAL; citations). `create_invite` is referral_service.py:242-362 (the return after
`_lifetime_invites_used` :353-362), not :242-340; payload :318-325. test_s05_p01 is :1325-1369
(:1372-1379 is `_CTX_HEADER_NAMES`, p02's set). `social_device_fingerprint_enabled` is :395-417.
`register` def is :584 (decorators :582-583).

RF6 (MINOR; spec header "Known rebase items ... No other S81-14 file is touched" names only S81-14).
Measured: `feature/s81-s06-anthropic-router` (in flight, fix round 1) edits CLAUDE.md:341 (the Feature
Flags paragraph, ONE physical line, the same line change 2(b) edits) and inserts its row at :497 (the
same anchor as S81-14 and this unit). Change 2(b) is a whole-line textual conflict with S81-06 at
rebase; the row insertion is an anchor union. Neither touches auth_routes.py (C13).

Confirmed upstream refutation (recorded for the orchestrator, NOT a spec defect): R-S08-4 ("a stored-row
match at register, social sign-in and the SAME_DEVICE checks accepts the new value OR the legacy
value"), PLAN_S81.md:103 ("so ... the referral SAME_DEVICE check keep working"), the S81-08 review RF11
(S81_08_SPEC_REVIEW.md:98-103, "fed by the share body") and the DEFECT_LEDGER S81-08b row all assume a
live SAME_DEVICE match a header can feed. The spec is right: it is dead at base (confirmed table above)
and stored-vs-stored even if revived. See BL2.

## Blocking issues (settle before RED)

BL1 (activation order; RF1). Replace the row's activation sentence and the owner step with: "flip ON on
`web` after this unit is deployed and BEFORE the first post-approval OTA (the DEFECT_LEDGER
precondition), as its own step ahead of 'the first OTA' in the PLAN_S81 flip order; independent of
`ENABLE_REQUEST_CONTEXT_HEADERS`, which flips after the OTA; ON with no legacy header is byte-identical
(build 3), so flipping it before approval is inert for the reviewer (the owner's call)". The OTA
precondition must be stated as a dated ledger line naming `ENABLE_LEGACY_FINGERPRINT_READER=true` on
`web`, never "merged". PLAN_S81:185 needs the new step (orchestrator; Q2).

BL2 (scope vs binding text). R-S08-4 and the DEFECT_LEDGER row require the SAME_DEVICE checks to accept
either value; the spec (correctly, by measurement) changes neither SAME_DEVICE nor the device lifetime
cap. A spec cannot silently narrow a binding ruling: the orchestrator rules the narrowed scope (two
request-time sites only; SAME_DEVICE a separate flagged defect row; the cap split accepted as limit 3)
and amends R-S08-4, PLAN_S81:103 and the DEFECT_LEDGER row before RED (Q3, Q5).

## Corrections

C1 (MAJOR; missing guard pin). Sections 1.11 and 4.2 list test_s81_s05 r08 / p01 / p02 / p05 / p06 /
p07 but NOT `test_s05_p08_no_dual_hash_names` (tests/test_s81_s05_request_context.py:1567-1578), which
asserts the substrings `legacy_hash` and `device_lookup_keys` occur in NO `app/**/*.py` or
`scripts/**/*.py` text (code, comments and docstrings alike). `legacy_hash` is the natural local name
for exactly this unit's value. Measured at base: neither substring occurs anywhere in app/ or scripts/
(probe_claude_md.out). Add p08 to 1.11 and 4.2 and state the rule for GREEN: never write the identifier
or the text `legacy_hash` / `device_lookup_keys` in app/ or scripts/; use `legacy` / `legacy_fp`. Also
state the p01 needles GREEN must not write into auth_routes (`header_state`, `device_key_pepper`,
`x-ai-consent-version`, `x-compare-request-id`: :1334-1344) and that the legacy read must keep
`auth.count('request.headers.get("X-Device-Fingerprint")') == 1` (p07 :1564; the
`"X-Device-Fingerprint-Legacy")` spelling does not match that needle, a constant or a second primary
read would).

C2 (MINOR; R11 partly vacuous). R11 slices the row "to the next `\n**SESSION`". This row is the LAST
`**SESSION` paragraph of the flags section at the base and at 86d5a24d; the next `\n**SESSION` after it
is the `**SESSION 65e CLOSE` paragraph about 134 KB (ea3aef15) / 134 KB (86d5a24d) later
(probe_claude_md.out: tests_idx 304804 / 318992, next heading 438566 / 452754). In that tail the R11
tokens `register`, `social` and `rollback` already occur, so a row that omits them still passes. Bound
the slice at the FIRST of `\n**SESSION` and `\n## ` (the `## Tests` heading), and assert the row is
shorter than a sane maximum (for example 8,000 characters). The unique tokens (the flag name, the header
name, `SAME_DEVICE`, `2027-03-31`, `S81-08`, `S81-08c`) are not present in the tail and stay sound.

C3 (stated limit; RF3). Add: "the legacy header carries today's composition with the CURRENT osBuildId;
a stored row written under an earlier OS build (or another app id or nonce) matches neither header, as
at base; the reader restores today's match rate, not more."

C4 (stated limit 7; RF4). Rewrite: "the anon gate keys (`anon:<fp>`) are untouched; build 3 never sends
the device header on the anonymous routes, so no legacy-keyed anon counter exists to carry; with
`ENABLE_COMPARE_AUTH_REQUIRED` ON (since 2026-10-03) anonymous compares are 401 anyway."

C5 (citations; RF2, RF5). Fix the R-S08-5 -> R-S08-4 attribution and the spans named in RF5.

C6 (mutation table: PIN rows without a named mutant). P6, P8, P11 and P12 kill nothing in section 6.
Each is a no-call or scope PIN whose deciding condition sits outside the unit (W3-3 OFF; the share route
reads no header; untouched referral code), so as written they cannot be shown non-vacuous. Add, each on
a byte copy, killing row in brackets: M17 `social_login` calls `_apply_social_device_fingerprint` when
the legacy flag is ON whatever W3-3 says [P6]; M18 `share_comparison` forwards
`request.headers.get("X-Device-Fingerprint-Legacy")` as `device_fingerprint_hash` when the body omits it
[P8]; M19 `_load_invitee` selects `device_fingerprint_hash` [P11]; M20 `_referrer_device_lifetime_count`
uses `.in_` over a two-value list [P12]. M17 and M18 edit auth_routes / referral_routes copies; M19 and
M20 edit referral_service copies (a byte copy of referral_service.py joins step 0 for the mutation run
only). Or declare P11 / P12 scope pins with no mutant and say so (Q6).

C7 (RED literals). probe_out.json's call lists came from a recording client that returned a FIXED prior
row regardless of filters (register update lcu 3, social update lcu 4 for any seed). The RED file must
record REG_BASE / SOCIAL_BASE_NULL / SOCIAL_BASE_OWNED at base with its OWN evaluating FakeUsers and its
own seeds (the call shape transfers; the update values do not), and say so in its header.

C8 (P4 coverage). Extend P4 to "NEW invalid (upper-case, 63 chars, empty) + legacy valid": zero FakeUsers
calls and no `get_admin_supabase_client` call in both flag states. Today P4 covers only "legacy only".

C9 (row wording). "one indexed read on `idx_users_device_fingerprint_active`" states a reasoned claim
(limit 8) as fact: write "an `IN` read the 023 partial index can serve (reasoned from the predicate, not
measured on a database)". Drop "after S81-08 merges" (BL1).

C10 (stated limit; CORS). Add: CORS `allow_headers` (main.py, pinned by test_s05_p03 :1395-1411) does not
list `X-Device-Fingerprint-Legacy`; native clients do not preflight, an Expo web build would; unchanged,
like S81-05 limit 5.

C11 (stakes, for Q1 / Q4). Measured: the daily and monthly free counters are keyed per user id
(usage_service.py:153-160) and `consume_comparison_credit` (:332) reserves them per user; the inherited
`lifetime_comparisons_used` only gates the lifetime-free branch (:359-378: allowed regardless of the
caps, a read-then-allow outside the atomic consume, bumping the same per-user counters) and the
`remaining.lifetime_free` figure on `/usage/status` (`_usage_status_body` :801-837). So a re-signup that inherits nothing
gets the same 3/day and 10/month as one that inherits, plus a lifetime-free window that skips the atomic
consume (a parallel burst can pass it) and a fresh "3 free" display. State this in section 0 so the
severity is not read as "free-tier farming reopens": the real device control is the referral cap
(limit 3) and, later, S81-09.

C12 (R6 sentinel). R6 forbids the synthetic UID anywhere in caplog over R3-R9. Measure at RED that no
base log line on the register / social paths carries the user id (none found by reading :582-683 and
:540-579, but app loggers outside the route can); if one does, restrict the sentinel to NEW and LEG.

C13 (known rebases; RF6). Add S81-06 (`feature/s81-s06-anthropic-router`) to the header's known rebase
items: CLAUDE.md:341 (whole-line conflict on the Feature Flags paragraph: re-apply the one pointer
sentence on top of S81-06's line) and the :497 anchor union. Re-derive the comm set at head after each
rebase (S81-06 adds test files that import app.main).

C14 (top label on ties, TRIVIAL). With equal `lifetime_comparisons_used` on a NEW row and a LEGACY row,
`order(desc).limit(1)` returns either, so `top=` is not deterministic; say so in 2.2 (a log label only)
and keep the RED seeds tie-free (they are).

## Contract risks

K1 (the flag is a second gate on the OTA). With FLAGGED (the spec's and the orchestrator's default) the
OTA precondition is "deployed AND `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` by a dated ledger
line". The DEFECT_LEDGER S81-08b row still says "none (additive read of a header no client sends yet)"
in its flag column and "LIVE BEFORE the first post-approval OTA"; R-S08-4 says "unflagged-safe". An OTA
gate that checks "merged" ships the reader dark: every post-OTA re-signup then inherits nothing,
silently (no error, no log line: the base path runs). Fix: update the DEFECT_LEDGER row and the S81-08
OTA checklist to name the ledger line (BL1).

K2 (narrowed scope vs R-S08-4). Delivering the unit as specified leaves the device lifetime cap split
across the transition (limit 3, at most one extra cap of 3 lifetime invites per device; each redemption
grants the referrer 5 or 10 bonus comparisons, referral_service.py:699-700) and leaves SAME_DEVICE dead.
Both are outside a header's reach (stored-vs-stored) and need a ruling (BL2) or a migration follow-up
(spec Q2).

K3 (share legacy header with no consumer). R-S08-4 tells the client to send the near-fingerprint legacy
composition at the share call; measured, nothing reads it (referral_routes.py:176-231). Data
minimization argues for dropping it at share in S81-08 (spec Q3, my Q4). Backend-indifferent (P8).

K4 (rebase). The CLAUDE.md:341 Feature Flags line is edited by S81-04 (merged), S81-06 (in flight) and
this unit: one physical line, three writers; every rebase re-applies the pointer sentence by hand
(C13).

K5 (observability when OFF). With the flag OFF and the OTA live there is no signal at all (no log line,
no metric): the canary must be run deliberately (a re-signup on a pre-OTA test device that has not had
an OS update since its first registration, C3), and only the ON path logs `[LEGACY-FP]`.

## Pin collisions

- tests/test_s81_s05_request_context.py::test_s05_p08_no_dual_hash_names (:1567-1578): text scan of app/
  and scripts/ for `legacy_hash` / `device_lookup_keys`. NOT listed in the spec (C1). Green at base.
- test_s05_p07 (:1558-1564): `auth.count('request.headers.get("X-Device-Fingerprint")') == 1`. Listed;
  safe for the `-Legacy"` spelling, red for a second primary read or a refactor through a constant that
  removes the literal (C1).
- test_s05_p01 (:1325-1369): `request_context` text is allowed in auth_routes
  (allowed set :1317-1322); the four header / pepper needles are forbidden outside the two leaf files;
  auth_routes' leaf import set must stay `{"DEVICE_FINGERPRINT_RE"}`. Listed.
- test_s05_r08 (:527-553): `_DEVICE_FINGERPRINT_RE` must stay the imported leaf object, never assigned.
  Listed (the spec reuses it with `.fullmatch`).
- tests/test_s81_kb_schema.py IDENTITY_NODES (86d5a24d, :412-428): LF sha of
  tests/test_s75_fanout_identity.py, its fixture, tests/test_w4_13_flag_off_ledger.py and its fixture.
  Listed for FY25; the W4-13 ledger pair is pinned the same way (also unedited by this unit).
- tests/test_s81_s04_spend_breaker.py::test_r38_claude_md_row (:1656-1666): the S81-04 row ends at the
  next `\n**SESSION`; the new row must be its own column-0 `**SESSION 81 ...` paragraph. Listed.
- T23 / OpenAPI (test_s71_u13_compare_auth_required.py, tests/fixtures/s71_u13_flag_off_baseline.json,
  test_s05_p02): no Header parameter. Listed; P10 mirrors it.
- Not affected (measured): FY25 digests (flag never read on a compare path), W4-11 prompt digests,
  test_retro_w2_1 URL pins, the W4-13 ledger fixture, copy-policy fences, the camera failure envelope,
  cache keys, the error-handler code mapping (no new code, no raise).

## Questions for the orchestrator

1. Q1 (flag). Rule FLAGGED (spec 2.9; my read agrees: R-A1 admits only proven byte-identity and a forged
   header changes a DB filter) and, if so, allow the owner to flip it right after deploy, before approval,
   since P2 / P7 pin flag ON + no legacy header = build 3 byte for byte? Update the DEFECT_LEDGER flag
   column and the S81-08 OTA precondition to the dated ledger line (K1).
2. Q2 (plan). Insert "S81-08b ON" into PLAN_S81:185 before "the first OTA" (or at its deploy), NOT with
   "ledger, breaker, request context ON" (RF1 / BL1).
3. Q3 (scope). Amend R-S08-4, PLAN_S81:103 and the DEFECT_LEDGER S81-08b row to the measured scope: two
   request-time matches (register, W3-3 social apply); SAME_DEVICE unreachable at base
   (referral_service.py:762, abuse_detection_service.py:249 / :124-125) and opened as its own flagged
   defect row (spec Q1)?
4. Q4 (client). Drop `X-Device-Fingerprint-Legacy` at the share call in S81-08 (no consumer, K3), keeping
   it at register and both social sign-ins only?
5. Q5 (cap split). Accept limit 3 (one extra cap per device across the transition) or open the migration
   follow-up (a legacy column written at register under this flag; spec Q2)?
6. Q6 (P11 / P12). Keep P11 as a scope pin that freezes a known defect (the `_load_invitee` select) and
   P12 (an untouched function), with mutants M19 / M20 (C6), or drop both and rely on the diff gate
   (referral_service.py is not in the change list)?
7. Q7 (spec Q5). Confirm silence for an invalid legacy header (no log line; the reader never 400s). My
   read: confirm; the primary header's `len=%d` INFO line already exists for the operator.

## Not done in this review

No RED or GREEN file, no mutation run (spec section 6 is a GREEN gate), no comm-set run (NOT MEASURED,
as in the spec), no database or production access. The only bounded run is the [pyt] line above.
