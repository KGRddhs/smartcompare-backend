# SESSION 65 — next-unit specs and standing gate artifacts (2026-09-08)

**Why this file exists.** Every unit spec, gate recipe and review checklist this
session produced lived in `.qa-*/` scratch directories, which `.gitignore:72`
excludes — inside worktrees that the context files themselves describe as
removable. The completed units are safe (their reasoning is in the merged PR
bodies, permanently on GitHub), but the NEXT unit's spec and the reusable process
artifacts would have been lost with the first `git worktree remove`. They are
preserved here.

**Everything below was re-verified against `main` at `38ea28a9` before this file
was committed** — not carried forward on trust. Where a claim moved, it is
corrected in place and the correction is marked.

---

## Where the completed units' reasoning lives

Do not re-derive these. Each merged PR body carries the measurements, the
mutation results and the stated limits:

| unit | PR | what it established |
|---|---|---|
| W0 load foundations | #135 | off-loop DNS, shared Supabase transport, bounded Upstash, parse-once |
| W2-1 metering | #137 | paid-door metering; `/url/compare` had never worked (tuple-unpack 500) |
| W1-4 auth | #139 | 503-vs-401; `str(UserDoesntExist(access_token))` IS the bearer |
| W3-11a Arabic revert | #141 | RN mirrors physical `textAlign` on all four paths; a sixth, LIVE site |
| W1-1 admin key + Sentry | #142 | three doors not one; trace-id destruction caught in review |
| W1-8 adapter visibility | #143 | `asyncio.TimeoutError IS TimeoutError` since 3.11 |
| W1-7 + W1-10 | #144 | uvicorn gates on CONNECTIONS not requests; loop-lag heartbeat |
| W3-12 Sentry boot order | #145 | jest is ts-jest and does not hoist; the two-stage Metro pipeline |
| W1-3 OpenAI breaker | #147 | the permanent-lockout pair; `is_circuit_closed` is not read-only |

---

## THE NEXT UNIT — W1-2

Re-verified at `38ea28a9`: `cleanup_expired_ratings` still returns **0 files**
across `migrations/` and `app/`; the five `SECURITY DEFINER` definitions and the
single `REVOKE` are exactly as described; `resolve_referral_code` is still
granted `TO anon, authenticated` at `014:102`; the highest migration is still
`036`, so `037` remains the right number.

**One check to run precisely, because a loose grep will scare you:** the claim is
that the mobile client ships no Supabase *credential*. A grep for the word
"supabase" in `SmartCompareApp/src` returns ~20 hits — all of them PROSE IN
COMMENTS. The claim to verify is
`grep -rniE "SUPABASE_ANON|SUPABASE_KEY|SUPABASE_URL|createClient" SmartCompareApp/src SmartCompareApp/app.json SmartCompareApp/eas.json`,
which returns **nothing**, and `supabase` does not appear in `package.json`. That
is what makes this P1 and not P0: the anon key is server-side only.


# W1-2 — migration 037: make the grants and RLS match what the migrations claim

Findings `CR-SECURITY-01` (SECURITY DEFINER functions executable by PUBLIC) and
`CR-SECURITY-02` (`user_events` readable by the anon role). New file
`migrations/037_security_definer_grants_and_rls.sql` (+ rollback) and tests.
**Applying it is an Ahmed/ops step** — 033-036 are also unapplied — so this unit
delivers the migration, the source-level guard that stops the next one repeating
the mistake, and the live pins that prove whether it worked.

## Corrections to the consolidated report — verified, do not carry the old text

**`cleanup_expired_ratings` DOES NOT EXIST.** The report names it as one of the
three offenders; `grep -rn cleanup_expired_ratings migrations/ app/` returns
nothing. The actual census of `SECURITY DEFINER` in `migrations/`:

| function | defined in | `REVOKE … FROM PUBLIC`? | explicit GRANT? |
|---|---|---|---|
| `delete_user_cascade(uuid)` | `010:70`, redefined `025:28` | **no** | none |
| `increment_lifetime_comparisons(uuid)` | `011:55` | **no** | none |
| `resolve_referral_code(text)` | `014:97` | **no** | `TO anon, authenticated` (`014:102`) |
| `home_savings_aggregate(uuid)` | `036:47` | **yes** (`036:94`) | `036:95` |

So three lack the REVOKE, and `036` is the correct template already in the repo —
copy its shape rather than inventing one.

**The three are not equivalent, and the fix differs.**
* `delete_user_cascade` and `increment_lifetime_comparisons` have **no explicit
  grant at all**, so EXECUTE falls to PUBLIC by PostgreSQL default and PostgREST
  exposes them as RPC. That is the real hole: a one-call account-destruction
  primitive for any UUID, and a freemium-counter primitive.
* `resolve_referral_code` is **deliberately** granted to `anon` — an anonymous
  user has to resolve a referral code before signing up. Do NOT revoke that
  grant; it is a product requirement. It still wants `REVOKE ALL … FROM PUBLIC`
  first so the exposure is the explicit grant rather than the default, which is
  what makes it reviewable and what stops a future role inheriting it.

**Severity is P1, not P0, and here is the reason — confirmed, not assumed.**
The mobile client ships **no Supabase key**: `grep -rniE "supabase|createClient"
SmartCompareApp/src` returns nothing, `@supabase/supabase-js` is not in
`package.json`, and the client's only base URL is the FastAPI backend. All
Supabase access is server-side, so the anon key is not distributed and the
functions are not reachable from a user's device. What stands between the
internet and `delete_user_cascade` is therefore the secrecy of one server-side
key — defense in depth is missing, but the door is not open.

**The `user_events` half is a MIGRATIONS-VS-LIVE claim, not a source claim.**
`010:57-59` already defines `events_insert` and `events_select` with
`USING (auth.uid() = user_id)`. So the source says the right thing and the
finding is that the LIVE database does not match it — RLS not enabled on the
table, or the migration never applied. A source test cannot detect that. Only a
`live_db` pin can, which is why this unit has two halves with different lifetimes.

## The unit

**1. `migrations/037_security_definer_grants_and_rls.sql`**, following 036's shape:
`REVOKE ALL ON FUNCTION … FROM PUBLIC` for all four functions (037 included, so
the set is closed), then re-`GRANT EXECUTE` only where a role genuinely needs it —
`resolve_referral_code` TO `anon, authenticated`, and nothing else unless a
reader is demonstrated. `ALTER TABLE user_events ENABLE ROW LEVEL SECURITY` (and
`FORCE` if the table owner is the service role) so the existing policies are
actually in effect. Ship the rollback alongside.

**Do not guess which roles need EXECUTE.** For each function, find its callers
(`grep -rn "<fn name>" app/`) and grant to the role that client authenticates as.
`delete_user_cascade` and `increment_lifetime_comparisons` are called through the
service-role client, which bypasses grants — so the correct grant for them is
NONE, and the test should assert that.

**2. Source test — the durable half.** Every `SECURITY DEFINER` in `migrations/`
has a matching `REVOKE ALL … FROM PUBLIC` somewhere in `migrations/`. RED today:
three lack it. This is what stops migration 038 repeating it, and it is the half
that keeps working whether or not anyone applies 037.

**3. `live_db` pins — the half that can actually see the finding.** Marked
`live_db` so CI skips them. With the ANON key: `count=exact` on `user_events`
must be 0 (RED today: 146 rows, 7 real user UUIDs), and an RPC call to each
revoked function must be rejected. **Do NOT write a live test that calls
`delete_user_cascade` with a real user id.** Use a UUID that cannot exist, and
assert on the permission error rather than on any effect.

## Gates
1. TDD red-first: the source test must fail with three named functions before the
   migration is written.
2. Byte-identity N/A (no price-path module); full CI-equivalent suite before push.
3. Ruff + `py_compile` on any changed Python; the SQL is reviewed by reading.
4. Fable review before commit. Agents never commit.

## What this unit CANNOT do, and must say so in the PR
It cannot prove production is fixed, because applying migrations is Ahmed's step
and 033-036 are also unapplied. The PR must state plainly: **merging this changes
nothing in production.** The migration has to be applied after 033-036, in order,
and the `live_db` pins re-run against the real database afterwards — that run, not
this merge, is the evidence. Anything less and this becomes a security fix that
everyone believes shipped and nobody applied.

---

## Standing artifact — findings that were REFUTED by measurement

# W1 finding corrections — measured, not read (Fable, 2026-09-08)

Two findings I recorded during W0-1 review were carried forward into the W1 queue.
Both were re-tested against the pinned interpreter before any unit was written.
One is REFUTED outright; one is DOWNGRADED from "fail-open vulnerability" to
"defensive hardening".

## REFUTED — "`::ffff:127.0.0.1` is not caught by `is_loopback`"

FALSE on this codebase. Python's `ipaddress` delegates the classification
properties of an IPv4-mapped IPv6 address to the mapped IPv4 address. Measured
on the pinned interpreter (`runtime.txt` = `python-3.12.9`, CI `python-version: '3.12'`):

    ::ffff:127.0.0.1        is_loopback True   is_private True    -> BLOCKED
    ::ffff:169.254.169.254  is_link_local True is_private True    -> BLOCKED
    ::ffff:10.0.0.1         is_private True                       -> BLOCKED
    ::ffff:192.168.1.1      is_private True                       -> BLOCKED
    0.0.0.0                 is_private True                       -> BLOCKED
    ::                      is_private True    is_reserved True   -> BLOCKED
    ::ffff:8.8.8.8          all False                             -> ALLOWED (correct)

`_addr_infos_allowed` already blocks every mapped form of the private ranges.
No unit needed. Not a version risk either: the runtime is PINNED to the same
3.12 line that CI runs, so there is no interpreter on which this codebase
behaves differently.

## DOWNGRADED — "empty `addr_infos` returns True (fail-OPEN)"

The code half is real: `_addr_infos_allowed` iterates and returns True after the
loop, so an empty list yields ALLOWED. But the antecedent is not reachable
through the production call path. Measured: `socket.getaddrinfo` RAISES
`gaierror` on an unresolvable host (errno 11001 on this platform) rather than
returning `[]`, and returns 2 entries for a resolvable one. An empty return is
undocumented and not produced by the platform resolver, and both validators call
`getaddrinfo` directly, so nothing interposes a different implementation in prod.

Verdict: defense-in-depth, LOW. An empty result means "no address was confirmed
public", which should fail CLOSED to keep the guard's invariant true by
construction rather than by the resolver's good behaviour. Fold the three-line
change plus its test into a later `url_validator` unit; it does not earn a unit,
a flag, or a PR of its own.

## The rule this pair is evidence for

Both were recorded from reading, and reading is where they went wrong: one
assumed a library does less than it does, the other assumed a syscall does more.
A finding about library or syscall BEHAVIOUR is not established until it has been
run on the pinned version. The same rule already caught the `sign_out(scope=...)`
TypeError and the `UserDoesntExist(access_token)` leak in W1-4 — in both of those
directions, reading the docs would have given the wrong answer.

---

## Standing artifact — the per-unit review checklist

Generalised from this session's batch. The unit-specific sections are kept as worked examples of the shape.

# Fable review checklist — batch wf_f6168360-bf7 (4 units)

Per unit, BEFORE committing anything. Agents never commit; I do.

## Every unit
- [ ] Read the actual `git diff` + `git status`, not the agent's description of it.
- [ ] Scope: only what the spec asked. Anything extra comes out or gets justified.
- [ ] Every behavioural claim in `measurements_run` — re-derive at least the load-bearing ones myself. The agents were told to measure; verify they did.
- [ ] Each key test FAILS with the fix reverted. Check the ones the adversary did not.
- [ ] Ruff `E9,F63,F7,F82` + `py_compile` (backend) / `npx --no-install tsc --noEmit` + eslint (client).
- [ ] Module-reference comm gate at base AND head, with the unit's OWN new test file in the set.
- [ ] Full CI-equivalent suite locally before pushing.
- [ ] PR body states what was NOT verified and why.

## W1-1 (sc-w1-sec) — security
- [ ] `verify_admin_key` is still CONSTANT-TIME after the bytes conversion. No `==`, no length short-circuit.
- [ ] A correct key still authenticates. An unset `ADMIN_API_KEY` is still a hard 403, never a skeleton key.
- [ ] `_before_send`'s 503-drop branch still works — the new walk must not flatten or reorder `contexts`.
- [ ] Regions are SCRUBBED, not blanked. A triageable event must survive.
- [ ] The scrub test fails with the scrub removed. The agent was told to verify this; confirm it.
- [ ] **SENTRY IS LIVE IN PROD** (`SENTRY_DSN` set on both services; "Sentry initialized successfully" in the deploy log). This leak channel is armed, not theoretical.
- [ ] PR body carries the Ahmed action: rotate `ADMIN_API_KEY` WHEN THIS DEPLOYS, not before.

## W1-7 + W1-10 (sc-w1-ops)
- [ ] The `${UVICORN_LIMIT_CONCURRENCY:-100}` expansion was PROVEN through `sh -c`, not assumed. If unproven, a literal shipped instead and the PR says so. A literal `${...}` reaching uvicorn is a crash loop.
- [ ] `railway.json` and `Procfile` are byte-identical after the `web: ` prefix.
- [ ] No `--proxy-headers` crept in (it changes the limiter key).
- [ ] `/health` stayed a pure dict read — no await, no I/O. It is Railway's deploy healthcheck.
- [ ] `status` and `message` values are unchanged (an external check may string-match them).
- [ ] Heartbeat task is cancelled on shutdown and `CancelledError` is not swallowed.
- [ ] **MY ADDITION, not in the spec — fold in here:** `app/main.py`'s cold-start comment tells an operator to cron
      `https://smartcompare-backend-production.up.railway.app/health`, which returns Railway's edge 404
      "Application not found". Live host is `https://web-production-58776.up.railway.app` (verified 200; the
      client's `api.ts:19` already uses it). Fix the comment in the same hunk. It is the ONLY operational
      reference to the dead host — every other hit is archival under `docs/`.

## W1-8 (sc-w1-obs) — price path
- [ ] `except Exception` was NOT widened. `CancelledError` is a `BaseException` and must still propagate, or prefetch cancellation breaks.
- [ ] Timeout and error are logged distinguishably. INFO, not WARNING.
- [ ] Healthy path logs NOTHING.
- [ ] `failed_count` is purely additive; no existing caller reads the dict positionally.
- [ ] **Byte-identity gate** over the FROZEN `_proof` corpus. Compare the `results` arrays, not the OVERALL SHA (it hashes the `--flags` list). Verify the corpus manifest first. **`_proof/sweep2.py` must NOT have been run** — check the corpus manifest is unchanged.

## W3-11a (sc-w3-rtl) — client, OTA blocker
- [ ] All five sites restored to the exact `593ec1e` literal: `specsCellValueLeft:'right'`, `specsCellValueRight:'left'`, `legendNameRight:'right'`, `charCount:'right'`, `prioritiesPercent:'right'`.
- [ ] The contract fence is INVERTED and its docstring no longer claims textAlign is physical. The false premise is what produced the wrong fix.
- [ ] `I18nManager` import removed from all four files — it is used for nothing else in any of them. A live import removed is a build break; a dead one is a lint failure.
- [ ] Nothing else from the W3-11 Arabic pack leaked in. This must read as a pure revert.
- [ ] PR body is explicit that on-device Arabic rendering is NOT verified here, and that the revert restores exactly the bytes every shipped build has run.

## Byte-identity gate — the exact command (W1-8; I run this, not the agent)

`_proof/` does NOT exist in `sc-w1-obs` and is not gitignored — it is untracked
local data living only in `sc-w0-load` and the shared clone. So the gate needs an
explicit root. Run from `sc-w1-obs`:

```
python scripts/verify_flag_byte_identity.py \
  --flags ENABLE_OFFLOOP_DNS_RESOLVE,ENABLE_SUPABASE_CLIENT_REUSE,ENABLE_UPSTASH_BOUNDED_TRANSPORT,ENABLE_PRICE_PARSE_OFFLOAD \
  --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof \
  --out .qa-w1b/gate_head_W1-8.json
```

Use EXACTLY that four-flag list — the OVERALL SHA hashes the flag list, so a
different list gives a different SHA over identical results.

- **Expected base:** `OVERALL SHA256 9504e5a94a218969764c8cbfdb43243da7bfcd8e0950bb5fb9148b9a9258ce99`,
  `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=825 calls=1656`.
- **First re-verify the corpus manifest** = `380902fba73c9169ed0becf77a45fe27b50c2caed511a364313f41270b497ba9`
  over `_proof/html` + `_proof/global/html` (593 frozen read-only files). A gate
  number over a moved corpus means nothing.
- If the SHA differs, diff the `results` ARRAYS of the two payloads before calling
  it a regression.
- **Do NOT run `_proof/sweep2.py`.** Record "sweep skipped per GATE_RECIPE ruling
  (live-network, nondeterministic)".

Note W1-8 is UNFLAGGED, so this is not a flag-OFF check in the usual sense. What it
proves is that adding logging and a `failed_count` key changed no extracted price
result anywhere in the 1,656-call corpus.
