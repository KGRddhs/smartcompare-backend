# RULINGS INC-SEC-1 (S96 orchestrator, 2026-11-17 about 07:20 AST), binding on the AMEND + RED round

- Draft: wf_7384f7ef-ff3 (two Opus 5.5 agents), at sec1/INC_SEC1_UNIT_SPEC_DRAFT.md, with the walk in sec1/INC_SEC1_WALK.md.
- Review: sec1/INC_SEC1_SPEC_REVIEW.md, verdict AMEND (6 MAJOR, 7 MINOR). It found NO blocking walk gap: an independent AST scan of 209 calls found the same 18 user-scoped references.

## The base moved
- origin/main is now **afde168f21703baba4bc4857eedf1042e5432196**: #415 (054) and #416 (I2b) are merged.
- The worktree is `C:/Users/SynAckITPC/Documents/AI/sc-s96-sec1`, branch fix/inc-sec1-app-user-access at afde168f.
  - It has a node_modules JUNCTION. Unlink it with `cmd /c rmdir` before any removal.
- 054 is now in main, so:
  - The merged 054 blobs are the pin source for X01. Re-read them at afde168f.
  - **This unit amends** 054's test row test_m02_next_free_number, which asserts 54 is the highest. Only the test changes; 054's SQL stays byte-equal.
  - It also re-pins the migration-listing digests in tests/test_s81_s22b_self_critique_retire.py.

## Rulings on the review
- **R-1 (F-01):** X01 pins the 054 files at afde168f.
- **R-2 (F-02):** section 10 names these moved pins:
  - re-pin the two listing digests;
  - test_feedback.py: configure the comparisons read as owned in its fixture;
  - test_migration_037_security_definer_grants.py: invert the live_db pin to expect 42501 (F8 is IN, R-14), and re-word its docstring and comments (:353-357, :570-579, :883-895).

  All of these files join the comm set.
- **R-3 (F-03):** name the ten tables. Apply the bare-true / IS NULL / share_token assertions only to policies whose roles include public, anon or authenticated. products_service_role_all is kept, and appears in K1 AFTER and in the cluster setup.
- **R-4 (F-04):** the apply note's Railway search adds these plain words, and expects 0 hits:
  - save failed
  - push token update failed
  - reengagement-subs update failed
  - preference-toggles update failed
  - Error deleting comparison
  - Share-token write failed

  In the Postgres log, an authenticated permission-denied on comparison_feedback, comparisons (delete) or users means STOP and roll back 055. The real-path proof: no `save failed` line within a minute of the owner's own feedback.
- **R-5 (F-05):** add the FORBIDDEN state: 055 applied while the server runs a deploy before C2. The apply note and the owner summary must both say: never roll the server back past the C2 commit while 055 is applied; roll 055 back first.
- **R-6 (F-06):** C2b runs for anonymous callers too. An anonymous caller owns no comparison, so a comparison_id is dropped whenever the row exists and is owned by anyone, or the read fails. Each drop logs a fixed word (FEEDBACK_COMPARISON_NOT_OWNED or FEEDBACK_OWNERSHIP_UNREAD). Keep the row and drop the id: no feedback is lost (Q2). Cases go into C03.
- **R-7 (F-07):** C04 uses a fake client that returns only the selected columns, or asserts the select string.
- **R-8 (F-08):** in the rollback, put DROP POLICY IF EXISTS before every CREATE POLICY, and state AS PERMISSIVE. The rollback is idempotent. K1 prints name, permissive, cmd, roles, USING and WITH CHECK.
- **R-9 (F-09):**
  - K2 enumerates every public relation where anon or authenticated holds any privilege, with its owner, and STOPs when that set is not the measured 21.
  - K2 and K8 print PUBLIC's ACL entries, and STOP if PUBLIC holds anything 055 revokes.
- **R-10 (F-10):** P4 and P8 add three proofs: an authenticated UPDATE of its own comparison, the invitee read of referral_invites, and a user_usage UPDATE.
- **R-11 (F-11):** fold (a)-(g) into their rows:
  - (a) `-- noqa: RF05` on every quoted policy name;
  - (b) M05 strips comments before it tests for SECURITY DEFINER;
  - (c) P10 gets a positive control and a detector mutant;
  - (d) L4 names notifications_enabled;
  - (e) the C2 docstring says "after 055";
  - (f) a K3 row checks service_role rolbypassrls;
  - (g) a server_version_num row: 140000 or more, or STOP.
- **R-12 (F-12):** a stated limit: the AST writer walk sees a user client only when it is built in the same function.
- **R-13 (F-13, Q3):** C3 makes the same-device referral control fire, which changes rewards, and that is the owner's call. So C3 ships DARK:
  - a new switch, ENABLE_REFERRAL_SAME_DEVICE_CHECK, default OFF, read per call in the house idiom;
  - with it OFF, the invitee select and the abuse result are byte-identical to today;
  - with it ON, device_fingerprint_hash is selected and the same-device check fires.

  The owner summary states the choice in plain words. The email half of R1-05 is closed by the 055 trigger, which is not behind a switch.
- **R-14 (Q1):** F8 is IN. The walk proves the server is the only caller. It overturns 037's deliberate anon grant, and the 037 pins move under R-2.
- **R-15 (Q4):** the WHOLE demographics_profile column is guarded. The walk shows no user-scoped writer of it; the server writes it with its own key.
- **R-16 (Q5):** K3 checks that service_role holds SELECT on the three cohort views, and STOPs if not.
- **R-17:** Q6 (revoke everything from anon on user tables), F9's default privileges and R1-08's column grant are FOLLOW-ups.
- **R-18:** the order. The window applies 054 first, then 055, and only after the deploy carrying C1 / C2 / C2b is live. C3 is dark, so its flip is separate.
- **R-19:** the cluster. The throwaway PostgreSQL 18.1 at C:/Program Files/PostgreSQL/18 (already installed; install nothing), initdb into the scratchpad, loopback, trust, stopped afterwards. Run on:
  - base + 054;
  - base + 054 + 055, with proofs P0-P8;
  - each rollback: the grid must be byte-equal to before;
  - a re-run of 055 (idempotent);
  - 055 without 054.

  Stated limit: production is PG 15. Every statement must exist in 15, and the version row (R-11 g) guards it.
