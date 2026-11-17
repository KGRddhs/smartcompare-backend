# INC-SEC-1 ADVERSARY A2 (code paths and order), 2026-11-17 12:40 AST: SOUND (3 MINOR, stated limits / wording)

Head e4cfe89e9601857161a7f7fdb91f4e49a4e3aeb8 (parents 89d94d25 + origin/main 7f672cfe). Read only toward W; one detached scratch worktree under this folder (removed at the end); no live database, no Railway, no ENABLE_* in any shell; no cluster needed for this lens (ADV-1 owns the SQL).

## Verified, not trusted
- git log -6 matches the report. The merge changes no unit byte: every path of afde168f..89d94d25 has the same blob at e4cfe89e except CLAUDE.md; e4cfe89e:CLAUDE.md sha256 = green/CLAUDE.md.union (bc63e374...). diff 7f672cfe..e4cfe89e = 17 files, +2502/-62, the same stat as afde168f..89d94d25.
- Main since base (afde168f..7f672cfe) adds no user-scoped client use (counts: 20 at afde168f, 20 at 7f672cfe, 18 at e4cfe89e).

## C1 (create_share_token): OK
database_service.py:596 drops access_token; :614 always the admin client; :620 get_comparison_by_id with no token (admin read). The only caller, share_routes.py:29, passes no token (also at base), so the user branch was dead and production behaviour is byte-identical. The ownership check (:627-628) stays. The share page reads with the admin client (get_shared_comparison :687). 055 removes the app-role UPDATE on comparisons; no server path depends on it.

## C2 / C2b: OK (one wording gap, M-1)
- feedback_service.py:213 admin client for every caller; :215 C2b only when comparison_id is set; the single except handler :250-257 logs only `[FEEDBACK] save failed type=%s code=%s` (no id, no text).
- Probe at e4cfe89e (fake client, synthetic ids, adv_a2/probe/probe_c2c3.py):
  - own row: kept;
  - other user's row: dropped, NOT_OWNED;
  - missing row: dropped, NOT_OWNED;
  - ownerless row (signed-in): dropped;
  - read failure: dropped, UNREAD;
  - anonymous + owned row: dropped, NOT_OWNED;
  - anonymous + no row, and anonymous + ownerless row: kept;
  - anonymous + read failure: dropped, UNREAD.

  The feedback row is written in every case, and the id never appears in a log line. An insert failure returns success False with the one constant line. With no comparison_id there is no read.

## C3: OK
- referral_service.py:64-72 uses the house idiom (`os.getenv(..., "false").strip().lower() in (true, 1, yes, on)`), read per call at :804.
- Probe:
  - unset, "", false, 0, no, off, tru and enabled give `id, email, subscription_tier, display_name`, the base string;
  - true, " TRUE ", On, 1, yes and "\tyes\n" add `device_fingerprint_hash`.
- ON: abuse_detection_service.py:248-252 compares that hash with the referrer hash (read by the admin client), so SAME_DEVICE fires.
- OFF: the invitee dict and the evaluate_invite input are byte-identical.

## Writer walk at the head (independent; R-12: clients passed to helpers included)
There are 18 user-scoped references. Each is a read or a write that 055 keeps:
- auth_routes.py:1462/1529/1608: users UPDATE of expo_push_token or preferences. users_update is kept, and none of the six guarded columns is touched.
- home_routes.py:254 -> _fetch_savings_aggregate (:95-101): the rpc home_savings_aggregate (036, SECURITY DEFINER; 055 leaves its EXECUTE alone) or a comparisons SELECT of own rows. :770 and :998 are users SELECTs.
- profile_routes.py:197/318: comparisons SELECT of own rows. :487: users SELECT.
- database_service.py:515/548/719: comparisons SELECT. :568: comparisons DELETE of an own row (kept).
- referral_service.py:239: self.user_client is built and never used.

Every write to comparison_feedback, search_logs, user_events, admin_audit_log, referral_invites, user_usage, and every comparisons insert, uses the admin client. Sites: feedback_service.py:213/273/309; database_service.py:473/806; audit_service.py:30; referral_service self.client; usage_service.py:876.

resolve_referral_code has no caller in app/, and the app (SmartCompareApp/src) has no database client. No server path is broken by 055.

## Deploy / apply mix (production: 054 applied, 055 not)
| state | feedback | share | verdict |
|---|---|---|---|
| D0 (deploy before C2) + no 055 (today) | user client for signed-in (afde168f feedback_service.py:182-186) | admin | OK |
| D1 (C1/C2/C2b) + no 055 | admin + C2b | admin | OK (C2b drops listed above) |
| D1 + 055 (target, R-18) | admin | admin | OK |
| D0 + 055 (055 first, or the server rolled back or redeployed to a commit without C2) | 42501 at the insert; the route still says received; only `save failed` logs | admin | FORBIDDEN |
| D1 + 055 rolled back | admin | admin | OK (the gaps reopen) |
| C3 OFF, any state | - | - | byte-identical |
| C3 ON, any state | - | - | SAME_DEVICE fires (the owner's flip) |

The notes name the FORBIDDEN state plainly: the apply note (sections 1 and 10), the owner summary ("The order, and the one thing never to do") and the 055 header. M-2 widens the wording.

## ORCH-SEC1-C: can a legitimate signed-in user lose the comparison link through C2b?
1. **Feedback before the row is persisted: no, KEPT.** The id reaches the client only after the awaited insert: text POST text_routes.py:925-929, text GET :1146-1150, stream :1395-1412, all via _persist_comparison_bounded (:165-200); a timeout echoes null. The image and URL routes echo no id (their persist is fire-and-forget), so their feedback carries none.
2. **Made signed-out, rated after sign-in: nothing to keep.** Signed-out compares persist no row and echo no id, so there is no link. Nothing is dropped.
3. **History item: KEPT.** history_routes.py:147-154 returns only the caller's own row (404 otherwise), and api.ts:525 and ResultsScreen.tsx:458 carry that id. Home smart pick and profile recent decisions also come from the caller's own rows.
4. **Shared comparison opened by another signed-in user: DROPPED, which is right.** The app gives that user no feedback path with the id: the history GET returns 404 for a non-owner, and ReferralLandingScreen renders no feedback card. Only a hand-made request could name it, and C2b drops the link.
5. **Found: an expired or rejected sign-in.** With ENABLE_STRICT_OPTIONAL_AUTH OFF, get_optional_user returns None (auth_routes.py:440-449, :482, :490), so the feedback arrives as anonymous. C2b then drops the link to the sender's OWN comparison (feedback_service.py:169-173). Base kept it.
   - A transient read failure also drops a signed-in user's own link (:174-176).
   - The row is kept in both cases; only the link goes.
   - The drop is defensible, because ownership cannot be proven, but it is a loss for a legitimate user. See M-1.

## Findings
- **M-1 MINOR (wording and a stated limit).**
  - The owner summary says "only a link to someone else's comparison is dropped". Spec Q8 says C2b changes the record only for another user's row.
  - Neither is true. C2b also drops the link for a missing or ownerless row (signed-in), for a failed read, and for an anonymous or expired-sign-in sender naming any owned row, their own included (case 5).
  - Fix: list the drop cases in the owner summary and the PR body, and state case 5 as a limit. It is rare: a token that expires between the compare and the tap, or an auth outage. The FEEDBACK_COMPARISON_NOT_OWNED count measures it.
- **M-2 MINOR (wording).**
  - The FORBIDDEN sentence says "roll the server back past the C2 commit". The same state follows from ANY deploy of a commit without C2, for example a branch cut before the merge or a manual deploy from another checkout.
  - Fix: write "never run a server build without the C2 commit while 055 is applied" in apply note sections 1 and 10 and in the owner summary.
- **M-3 MINOR (accuracy).**
  - The owner summary says the app's public key "ships inside the app". But SmartCompareApp/src at the head has no database client and no reference to that key, and the same summary says the app never talks to the database.
  - Fix: write "the public key (public by design; anyone who obtains it)".

## Public repo and notes
The three notes, the commit messages and the diff contain no e-mail, real id, key, project ref or step-by-step misuse text. The only ids are example.invalid and the synthetic 5a5a5a5a-... values. The notes describe what is permitted and what changes.

## Runs
- [pyt] tag=s96s-adva2-lens start=2026-11-17 12:35:25 end=2026-11-17 12:35:46 elapsed=20s bound=1200s status=OK rc=0.
  - 14 files at W (HEAD e4cfe89e): the RED file, test_feedback, test_feedback_service, test_m13_29, test_s80_b1, test_s81_sf1_surfaces_be, test_share_routes, test_referral_loop2, test_referral_service, test_referral_service_internals, test_abuse_detection, test_referral_e2e, test_referral_lifetime_cap, test_m13_28.
  - Result: 472 passed, 1 skipped; [hermeticity] 472 checked; [netguard] 11 attempts from 5 nodes.
- [pyt] tag=s96s-adva2-netbase start=2026-11-17 12:36:14 end=2026-11-17 12:36:18 elapsed=4s bound=600s status=OK rc=0.
  - The same 5 nodes at base afde168f, in the scratch worktree.
  - Result: the same 11 attempts from the same 5 nodes, so they predate this unit.
- probe_c2c3.py at e4cfe89e (scratch worktree, no network, synthetic ids): results above.
- The scratch worktree is removed (git worktree remove --force, then prune). W is still at HEAD e4cfe89e with a clean status.
