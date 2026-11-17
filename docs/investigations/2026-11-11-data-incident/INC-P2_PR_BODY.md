# fix(price): INC-P2 price-not-lost - each side priced at its own bottle size, dark behind ENABLE_PRICE_NOT_LOST

Status: merged, NOT yet proven. Nothing on any phone changes until the relay flips `ENABLE_PRICE_NOT_LOST` on web in its own window; the proof is the owner's phone (section PROOF ON THE PHONE), never the suites below.

Branch `fix/inc-p2-price-not-lost`, rebased onto origin/main bd0500a3 (#414 / #415 INC-T1 / T1b, #416 INC-I2b; #413 and #412 below). Three commits: GREEN (bfb24a4b), fix round 1 (0380e3ca; FIX1_RULINGS_INC_P2 F1-F7, D1-D7) and the re-verifier's docs fix (8bb97fe0). Absorbs INC-P1 and INC-X1. Class FOCUS (two adversaries, then a correctness re-verifier). Spec `.qa-s80/INC-P2_UNIT_SPEC.md` + review `.qa-s80/INC-P2_SPEC_REVIEW.md`; rulings RULINGS_INC_P2 P2R-1..P2R-37 (the relay's ORCH-P2-A / B / C); RED gate GATE_INC_P2; fix rulings FIX1_RULINGS_INC_P2.

## What the flag does

`ENABLE_PRICE_NOT_LOST` (default OFF, the house idiom, read per call as the first statement of every gated predicate; `app/services/price_service.py::price_not_lost_enabled`). ON:

- Fragrance pairs go through `reconcile_pair_sizes_v2`. Each side keeps the size typed for THAT side (read from its own name, the same with the resolver ON and OFF). A side at its OWN typed size is no longer pended because the other side typed another size (T3-01). With no typed size the shipped common-size re-selection runs (100 ml preferred, else the largest common size); with none common, neither side changes. A side IS still pended for size in two cases: a typed side whose listing is at ANOTHER strict size (P2R-3 / P2R-34), and an untyped side at a size other than the other side's on a request without the `price_size` token (rule 2).
- The floor (P2R-12): a listing under 30 ml, or titled travel / mini / miniature / atomiser / atomizer, is never a side's price unless that size was typed; such a side is re-selected from passing candidates, else pended (pending_genuine).
- The projection (P2-4): when the final sizes differ, the price-comparing consumers (scoring, the factual verdict, the verdict prompt, confidence) receive pending inputs, so no cheaper claim is made across sizes. For the side flag OFF pends, that is flag OFF's own pending dict; when flag OFF pends neither side (the rule-4 projections, A19 / A30) BOTH sides are projected, so a pair flag OFF compares is not compared. The saved-history savings readers skip such a row (F4). The found price rides a private product key that only the wire copies restore (overview, the legacy alias as copies, the SSE `prices` event), after the chokepoint's own checks (region currency, `is_price_showable`, the floor).
- The display rules (ORCH-P2-B): rule 1 a TYPED side whose listing is at its typed size (or has no ml size, P2R-29) is shown on every app; a typed side's listing at ANOTHER size is never shown and never held. Rule 2 an UNTYPED side at a size other than the other side's is shown only when the request's `X-Client-Capabilities` lists `price_size`; without it the side stays exactly as flag OFF ships it (pending, `size_mismatch`) plus the additive `price.offsize_listing`. Rule 3 a mixed pair applies rule 1 to the typed side and rule 2 to the untyped side. Rule 4 a side flag OFF shows never loses its price (P2R-31 for the A30 case).
- Additive wire keys, stable names (P2R-22): `price.size_ml`, `price.per_ml` (4 places, currency per ml), `price.offsize_listing` {amount, currency, size_ml, per_ml, retailer, url, title cut to 120, source_method} (only on a side held without the token), `metadata.pair_price_sizes` {mode same_size | different_sizes | unknown, sizes_ml}. `different_sizes` is also stamped when one side's size is unknown and the other's is known and not 100; 2e7a1229 then draws its different-sizes note when both prices are shown (eng m8). No `_p2*` key reaches a body, SSE event or History row on any path, a wire fault or a mid-request flip included: F1, rows F1a (overview + alias, cap0 / cap1), F1b (flag flip between the reconcile and the build), F1c (every stream event), F1d (the GET route response and the body handed to the History persist), F1e (the 44-fixture walk), F1f (flag OFF the alias is product_data itself).
- P2-7 as narrowed by F3: a re-selected shown price is written under the key the next identical request reads ONLY (a) at the side's own typed size when the key text (brand + name + variant) carries that size, or (b) for an untyped side at exactly 100 ml, the basis a bare-name key already means with the flag OFF. A size the partner side dictated is never written under a key that does not carry it (F3a; F3b and the F3c walk read the cache back flag OFF and ON). (a) is reachable with `ENABLE_PRODUCT_RESOLVER` off (the typed size stays in `name`) and on (`variant` = "EDP 100ml"); F3d pins both. The write goes through `should_cache_price` and the existing TTLs, a converted re-selection never overwrites a genuine entry. P2R-6: every L1 price write keeps `_seen_at` (ISO-8601 UTC).
- P2-8 `numbers_match` ignores ml / oz / fl oz size numbers on the product side; P2-9 a genuine Shopify reseller hit is parked ahead of a converted / estimate / listing-url park and seeded; P2-10 auction / peer marketplace sellers (`_P2_MARKETPLACE_SELLERS`: Whatnot, eBay, AliExpress, Temu, Back Market, The RealReal, ...) never become the Tier-1 Shopping pick, an adapter converted park or a V2 re-selection; P2R-13 a Rasasi Hawas row joins `_GENDER_FLIP_LINES` under the flag (a DATA row the owner may veto; inert unless `ENABLE_LISTING_MATCH_GUARD` is on).
- `app/api/text_routes.py` passes `price_size_cap=True` at the GET, POST and stream compare calls when the flag is ON and the header carries the token.

OFF: every response body (sync GET / POST, every SSE event, every partial), status, cache write, DB row and prompt byte is identical to base (A34 12 cells, B17 24 cells, B07, B22[None], H4, R03, S03, F1f, F2). UNFLAGGED by ruling, each built with every argument inside its own guard, names and numbers only:
1. `PRICE_OUTCOME` (response_builder): one INFO line per product per build: slot, product, shown, amount, currency, size_ml, method, retailer, marketplace=0|1, origin, race, reconcile (`floor` for a floor pend, F7b), pend_reason, display_rule, miss / miss_host / miss_status / miss_rule (read under every key the notes are written under, F7a), fam, rejected, examples, cache_write, cap, host.
2. `PRICE_CACHE_HIT layer=l1|l2 age_s=<n>|unknown` on every price L1 / L2 hit; 3. `PRICE_CACHE_SKIP reason=<check> site=persist|direct_hit|reselect`; 4. the in-memory request trace + miss ledger those lines read.
5. F1: the legacy alias without the private keys when the wire copies were not built (keyed on the keys; a flag-OFF body never carries one, so the alias stays product_data itself).
6. F4: `home_routes._extract_winner_loser_prices` (/home/savings) and `profile_routes._extract_winner_loser_prices` (/profile/monthly-stats) return (None, None), so the row is skipped, when the stored `metadata.pair_price_sizes.mode` is present and not `same_size` (`home_routes._pair_price_sizes_differ`). Not flag-gated on purpose: a row stored in a flag window stays skipped after a rollback; a row without the stamp is read exactly as today (F4d walks 44 flag-OFF bodies).

## Fix round 1 (FIX1_RULINGS_INC_P2)

| fix | finding | change | rows (tests/test_inc_p2_fix1.py) |
|---|---|---|---|
| F1 | corr MAJOR-1 = eng MAJ-2 | RB `_p2_strip_private` in the fallback branch | f1a-f1f |
| F2 | corr MAJOR-2 | SCS: the trace key and the L2 age read inside their guards; PS: the trace `before` list inside its guard | f2 (off / on; green at 5cd93c6a, measured in a scratch worktree), f2b |
| F3 | corr MAJOR-3 | SCS `_p2_cache_reselected`: the (a) / (b) basis check, `PRICE_CACHE_SKIP reason=size_basis site=reselect` | f3a-f3e |
| F4 | eng MAJ-1 | home_routes / profile_routes extractors skip a cross-size stored row | f4a-f4g |
| F5 | eng MAJ-3 | the comm set re-derived from the import graph (section Gates) | - |
| F6 | X01, X04 = E09, X05, E06, E12 survivors | killing rows; each re-applied as a mutant | f6_* |
| F7 | corr m4 / m5 | PS `p2_ledger_names` + `price_miss_summary(list)`; `_p2_trace_reconcile` floor | f7a, f7b |

## Gates (every run through gate.py, the pinned venv, one pytest at a time; full [pyt] lines in the fix report INC-P2_FIX1_REPORT.md)

- Rebase 2 onto bd0500a3 (orchestrator): CLAUDE.md only (flag line: #416's insert, then ours; blocks: I2b, blank, P2), once per commit; SCS and woocommerce_service.py auto-merged; the six app files' +/- lines byte-equal before and after; test sha256s unchanged. At 8bb97fe0: unit ON / OFF 721 passed; CI set + I2b files 2620 passed; comm set (766 files, 31,192 nodes) 29 failed = the 28 base ids + a test_retro_w0_4 loop-gap timing row (158 vs 150 ms), green 2/2 alone; fences 246 passed / 4 w37 drift.
- Rebase 1 onto 5cd93c6a: CLAUDE.md 2 hand-joined conflicts (both sides kept), SCS auto-merged (our +/- lines byte-equal before and after). At the rebased head: the frozen pair ON 495 / OFF 495 passed; tests/test_inc_i2a_picture_not_cut.py + tests/test_s81_12_legal_v3.py 105 passed on a re-run (the first run failed E27 only, see below).
- RED step: tests/test_inc_p2_fix1.py (sha256 b148541e...664e) at the rebased GREEN head 0c66ca4e (scratch worktree): 63 failed, every one an AssertionError; 163 of its 226 nodes green there (PIN); the frozen pair 495 passed (unchanged, sha256 43d309db... / 07d72b74...).
    [pyt] tag=inc-p2-fix1-redfinal2 start=2026-11-17 05:43:51 end=2026-11-17 05:44:07 elapsed=16s bound=600s status=FAIL rc=1
- F2 PIN measured at main 5cd93c6a (scratch worktree): f2[off], f2[on], f2b green there.
    [pyt] tag=inc-p2-fix1-base-f2 start=2026-11-17 02:06:50 end=2026-11-17 02:06:55 elapsed=5s bound=600s status=FAIL rc=1  (the 2 failures are f4c, which needs the marker that only exists on the branch)
- Unit files (the three) at the final tree: flag ON 721 passed, flag OFF 721 passed.
    [pyt] tag=inc-p2-fix1-final-on start=2026-11-17 05:54:54 end=2026-11-17 05:55:07 elapsed=14s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-fix1-final-off start=2026-11-17 05:55:14 end=2026-11-17 05:55:28 elapsed=13s bound=600s status=OK rc=0
- Mutants (byte copy in a scratch worktree, one exact edit, restore + sha256 compare; 16 mutants, 18 applications): F1, F2, F2b, F3u, F3t, F3x, F4h, F4p, F4m, F7a, F7b, X01, X04, X05, E06, E12 all KILLED on an AssertionError (F3t and F4m after the rows f3f / f4h were added).
- CI-order set, ONE alphabetical process, 36 files (test_429_contract first; the source pins, the CLAUDE.md and black-clean readers, the savings readers, the frozen pair, the fix-round file, tests/test_inc_i2a_picture_not_cut.py, tests/test_s81_12_legal_v3.py): 2567 passed, 1 failed = test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait.
    [pyt] tag=inc-p2-fix1-ci start=2026-11-17 05:44:56 end=2026-11-17 05:46:54 elapsed=118s bound=1200s status=FAIL rc=1
  E27 is a timing flake of #413's own row (`round(elapsed, 2)` 0.42 against a 0.421 s bind wait): it fails the same way at main 5cd93c6a (scratch worktree, the whole file) and passes alone twice at main and twice on the branch.
    [pyt] tag=inc-p2-fix1-base-i2a start=2026-11-17 05:55:34 end=2026-11-17 05:56:10 elapsed=36s bound=600s status=FAIL rc=1  (AssertionError: (0.42, 0.421))
- Comm set by the union rule at the final tree (F5: re-derived from the import graph, every import statement incl. function-level, plus the text references, the named pins and the ruling's members; GREEN's 741 + 20 = 761 files, the four hook files excluded), 31 chunks of <= 25 files, flag unset: 31,071 nodes, 26 failed + 2 errors = 28 ids = exactly the base record's 28 (b0ad2603). branch-only-NEW: EMPTY. tests/test_s80_b1.py p8 (GREEN Q2) passed. 0 TIMEOUT, 0 BUSY. The 20 new members: test_be_harness, test_cron_eval_nightly, test_cron_expire_bonuses, test_cron_reengagement, test_eval_gate, test_eval_grading, test_eval_kpi_gate_verdict, test_eval_persistence, test_eval_runner, test_inc_i2a_picture_not_cut, test_inc_p2_fix1, test_kpi_metric, test_migration_044_apple_siwa_tokens, test_migration_index_predicate_immutability, test_registry_liveness_gate, test_s71_u13_harness_auth, test_s81_d22d_learning_hardening, test_s81_g5_gate_rows, test_s81_s09_gate_rows, test_seed_zyte_guard.
    [pyt] tag=inc-p2-fix1-c01 start=2026-11-17 04:26:11 end=2026-11-17 04:26:45 elapsed=34s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c02 start=2026-11-17 04:26:52 end=2026-11-17 04:27:20 elapsed=28s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c03 start=2026-11-17 04:27:27 end=2026-11-17 04:27:53 elapsed=26s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c04 start=2026-11-17 04:27:59 end=2026-11-17 04:28:55 elapsed=55s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c05 start=2026-11-17 04:29:02 end=2026-11-17 04:29:31 elapsed=29s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c06 start=2026-11-17 04:29:38 end=2026-11-17 04:29:52 elapsed=14s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c07 start=2026-11-17 04:29:59 end=2026-11-17 04:30:19 elapsed=20s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c08 start=2026-11-17 04:30:26 end=2026-11-17 04:30:57 elapsed=32s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c09 start=2026-11-17 04:31:46 end=2026-11-17 04:32:55 elapsed=70s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c10 start=2026-11-17 04:47:12 end=2026-11-17 04:48:22 elapsed=71s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c11 start=2026-11-17 04:48:40 end=2026-11-17 04:49:08 elapsed=29s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c12 start=2026-11-17 04:49:36 end=2026-11-17 04:50:18 elapsed=42s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c13 start=2026-11-17 04:51:06 end=2026-11-17 04:51:18 elapsed=12s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c14 start=2026-11-17 04:51:25 end=2026-11-17 04:51:44 elapsed=19s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c15 start=2026-11-17 04:51:50 end=2026-11-17 04:52:20 elapsed=29s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c16 start=2026-11-17 04:52:27 end=2026-11-17 04:53:09 elapsed=42s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c17 start=2026-11-17 05:00:21 end=2026-11-17 05:00:45 elapsed=24s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c18 start=2026-11-17 05:00:52 end=2026-11-17 05:01:12 elapsed=20s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c19 start=2026-11-17 05:01:19 end=2026-11-17 05:03:19 elapsed=120s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c20 start=2026-11-17 05:03:26 end=2026-11-17 05:04:55 elapsed=89s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c21 start=2026-11-17 05:06:04 end=2026-11-17 05:07:49 elapsed=105s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c22 start=2026-11-17 05:09:29 end=2026-11-17 05:11:13 elapsed=104s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c23 start=2026-11-17 05:23:22 end=2026-11-17 05:24:30 elapsed=68s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c24 start=2026-11-17 05:25:09 end=2026-11-17 05:25:49 elapsed=40s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-fix1-c25 start=2026-11-17 05:35:52 end=2026-11-17 05:37:04 elapsed=72s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c26 start=2026-11-17 05:37:11 end=2026-11-17 05:37:31 elapsed=20s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c27 start=2026-11-17 05:37:38 end=2026-11-17 05:38:20 elapsed=42s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c28 start=2026-11-17 05:38:26 end=2026-11-17 05:39:02 elapsed=35s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c29 start=2026-11-17 05:39:09 end=2026-11-17 05:39:36 elapsed=27s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c30 start=2026-11-17 05:39:43 end=2026-11-17 05:40:18 elapsed=36s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-fix1-c31 start=2026-11-17 05:40:25 end=2026-11-17 05:40:32 elapsed=7s bound=1200s status=OK rc=0
- The four pre-commit hook files ALONE: -k "not dash" 167 passed / 160 deselected; -k dash 157 passed, 3 skipped / 167 deselected.
    [pyt] tag=inc-p2-fix1-hook1 start=2026-11-17 05:47:11 end=2026-11-17 05:50:30 elapsed=200s bound=1800s status=OK rc=0
    [pyt] tag=inc-p2-fix1-hook2 start=2026-11-17 05:51:51 end=2026-11-17 05:54:27 elapsed=157s bound=1800s status=OK rc=0
- The fourteen backend-scanning client fences (15 suites by path, jest 29.7.0): 246 passed, 4 failed = the four accepted config/nativeBundle.w37 drift nodes.
    [jest] tag=inc-p2-fix1-fences start=2026-11-17 05:54:59 end=2026-11-17 05:55:05 rc=1
- Lint: ruff 0.16.5 `--select E9,F63,F7,F82` clean on the five app files and the new test file; full ruff head = base per app file; py_compile OK; no edited file is in .github/black-clean-paths.txt (no black --check owed); 0 added bytes > 127; CRLF kept.

## Stated limits

- D1: only the three phone compare calls (GET, POST, stream) pass the token; the legacy product1 / product2 POST and the image / URL routes do not (an untyped off-size side there is always held).
- D3 / P2R-6: `_seen_at` is an underscore key; `public_price_view` strips it only with `ENABLE_EXACT_PRICE_GATE` ON (production), so with that gate false a cached `_seen_at` reaches the wire. An L2 promotion carries `_seen_at` only when the row's age is known; L2 has no seen-at column.
- D4: no fragrance line or lexicon entry carries the word Mini; the floor words match whole words only (F05).
- D5: the Hawas row ships under the flag and acts only with `ENABLE_LISTING_MATCH_GUARD` on.
- D6 / P2R-11 / eng m4: the ledger records timed_out (race miss), the Shopping filters numbers_match, variant, identity and marketplace, and the floor. NOT noted: select_best, showable, implausible_low, concentration and out_of_stock rejections (miss stays not_found / none for them); `refused` and `no_price_parsed` are deferred to INC-P3 SHOP-POLITE.
- D7 / D8 (narrowed): the resolver cell of the seam rows uses the apply_resolution Step-1 shape; the moderation-window stream partial is not driven (the gather-stage tail partial is, B03s).
- D9 / F7: the miss ledger is read under the product's full_name and the price task's key built from its Step-1 brand / name / variant; a camera (vision) product whose name repeats its brand can still read miss=none.
- P2R-31: when flag OFF pends nothing but the flag keeps a side at a different size (a refused marketplace re-selection, A30), a phone without the app update sees two amounts at different sizes with no size drawn; the price and value bars stay limited_data.
- P2R-36 (ORCH-P2-C, count first): a marketplace price that reaches the wire by a path P2-10 does not cover stays shown with the flag ON and is logged `marketplace=1`; the relay counts those lines before any hide unit (INC-P2m).
- corr m2: the 1.0 s `asyncio.wait_for` bounds the P2-7 write only with `ENABLE_ASYNC_REDIS_OFFLOAD` on (absent in production); there the synchronous Upstash call is bounded by its own client timeout.
- eng m6: the P2-7 write is awaited inline: worst case about 4 s per compare under the flag (2 sides x a 1.0 s key read for a converted price + a 1.0 s persist), shown as `INC-P2 cache write failed` WARNINGs.
- eng m5: the parked / recovered trace sets hold `id()` values; a reused id can in rare cases mislabel a later dict's `origin` (log only).
- GREEN Q3: the W4-7 listing-count replay adds duplicate Shopping rejection notes (counts only). GREEN Q4 / SL8: a body built outside the request (share / history rebuilds) logs `reconcile=unknown`.
- SL2 / C-9: `scoring_v2.winner_evidence` (saved row only) may keep today's price-provenance sentence; the Claude verdict is written from the projected inputs, so it may say a side has no confirmed price while the phone shows its amount.
- SL3: a typed "50 ML" no longer rejects a "100 ml" title at numbers_match (any category); the size axis of the later gates and the reconcile decides. SL4: an oz-only or two-size title gives no `size_ml`.
- SL5 (F3): entries written under the flag live up to their TTL (7 days genuine, 24 h converted) after a rollback; they are only own-typed-size or 100 ml entries, which the flag-OFF path reads like any entry of that key (F3c measures one flag-OFF gain: a pair flag OFF pended both sides of is shown at 100 ml from such an entry). Old bare-name entries are not purged.
- C-8 / SL10: under the flag the W4-7 replay and `rating_service`'s Shopping pick follow the marketplace skip and the numbers_match strip; refurb sellers (Back Market, Swappa, Gazelle) also drop from every category's Tier-1 pick.

## PROOF ON THE PHONE (RULINGS section E as amended by G, H and J; GATE sections 6-8)

Precondition: merged; the relay flips `ENABLE_PRICE_NOT_LOST` on web in its own window (no other flip in it). Two phone cells: **cap1** = a phone on the fourth app update (group c5a02157, built from 2e7a1229, live since 2026-11-16 23:46 AST) cold-started twice after that time: it SENDS `X-Client-Capabilities: price_size` and draws `size_ml`, `per_ml` and the different-sizes note. **cap0** = any other phone (store 683f56c0, OTA 82172383): no token, no size drawn. Every screenshot names its cell.

| pair (typed exactly) | cap1 (fourth update) | cap0 (older app) | backing (Railway log, plain words) |
|---|---|---|---|
| "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp" (T3-01) | both amounts, each with its size (30 ml, 100 ml), the different-sizes note, no cheaper line | both amounts, no size, no cheaper line | Dior `reconcile=both_shown shown=yes size_ml=100`, Ted `size_ml=30`, `marketplace=0` on both, `cap=price_size` / `cap=none` |
| "YSL Libre EDP" vs "Lancome La Vie Est Belle EDP" (R01, untyped, 90 ml vs 100 ml) | both amounts with sizes and the note | today's screen: YSL "No confirmed price yet", Lancome's amount | YSL `reconcile=both_shown cap=price_size` / `reconcile=offsize_held cap=none` |
| a mixed pair: "Ted Baker M 30ml" vs "Dior Sauvage EDP" | both amounts with sizes and the note | Ted's amount; Dior "No confirmed price yet" | Dior `both_shown` / `offsize_held` (if Dior has a 30 ml listing it is re-selected: both shown on every app, same size, no note, `reconcile=reselect`, `PRICE_CACHE_SKIP reason=size_basis site=reselect`) |
| "Sauvage EDP" vs "Bleu de Chanel EDP", twice a few minutes apart | the same two amounts on both runs (both 100 ml) | the same | run 1 Bleu `origin=live reconcile=reselect` (a cache origin means the check was NOT exercised: say so); run 2 `PRICE_CACHE_HIT` for Bleu |
| Baccarat Rouge 540 (70 ml) vs a 100 ml perfume (the BR540 row) | both amounts with sizes and the note | BR540 "No confirmed price yet" (rule 2) | BR540 `size_ml=70`, `offsize_held` in cap0 |

Every row: no `pend_reason=size_mismatch` on a side shown in cap1, and the result is NOT counted in the Home / Profile savings (F4). Not provable in production: what a race miss shows when a genuine reseller hit exists (rare; B09 only), the stated limits above.

## FLIP NOTE

- Flag: `ENABLE_PRICE_NOT_LOST` on web (true).
- Canary filters (plain words, never brackets): `PRICE_OUTCOME`, then `cap=none` (a phone without the update; `cap=price_size` with it), `reconcile=offsize_held`, `marketplace=1` (the ORCH-P2-C count), `miss=timed_out`; also `PRICE_CACHE_HIT`, `PRICE_CACHE_SKIP`, and the WARNINGs `INC-P2 p2 wire skipped`, `INC-P2 cache write failed`.
- A phone without the app update can show two prices for different bottle sizes with no size drawn, and no price comparison is made.
- Rollback: set the flag false (read per call, immediate for new responses). The price entries written under the flag stay up to their TTL (7 days genuine, 24 h converted); they are only own-typed-size or 100 ml entries, which the flag-OFF path reads like any entry of that key (genuine, or converted for 24 h); so after a rollback a pair flag OFF used to pend can show both sides at 100 ml (a gain, measured in F3c; ruling P2R-38). Purge option (owner): delete the `price:` L1 keys (Upstash) and the L2 price rows saved in the window. Rows saved in the window stay out of the savings figures.
- FLIP PRECONDITION (F4): `ENABLE_HOME_SAVINGS_AGGREGATE` stays OFF while `ENABLE_PRICE_NOT_LOST` is on, until a later migration adds the same `pair_price_sizes` filter to `home_savings_aggregate` (migration 036). No migration in this unit.

| behaviour | the switch state it needs | production today (names only, the relay's read) |
|---|---|---|
| the Hawas gender row | `ENABLE_LISTING_MATCH_GUARD` on | not set on web (default off): INERT today |
| `_seen_at` on the wire | `ENABLE_EXACT_PRICE_GATE` false | not set on web (default ON): `_seen_at` does NOT reach the wire today |
| the 1.0 s bound on the cache write | `ENABLE_ASYNC_REDIS_OFFLOAD` on | not set on web (default off) |
| the KB-served cell | `ENABLE_KB_FIRST_SERVE` on | not set on web |
| the resolver interplay | `ENABLE_PRODUCT_RESOLVER` on | not set on web |
| the F4 hard rule | `ENABLE_HOME_SAVINGS_AGGREGATE` off | not set on web; it must never open while `ENABLE_PRICE_NOT_LOST` is on until a migration adds the same filter |

## Owner steps (names only)

None to merge beyond the relay's window. The relay flips `ENABLE_PRICE_NOT_LOST` on web in its own window and runs the proof above; the Rasasi Hawas row is the owner's to veto.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
