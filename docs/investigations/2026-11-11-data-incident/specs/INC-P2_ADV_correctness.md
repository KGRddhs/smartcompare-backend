# INC-P2 PRICE-NOT-LOST - ADVERSARY REPORT, lens CORRECTNESS (Opus 5.5, 2026-11-17)

VERDICT: NOT_READY (0 blocking, 3 major, 8 minor).
Unit INC-P2; worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-p2, branch fix/inc-p2-price-not-lost, HEAD 8abc5115fa3b98dafb9afa0ae7ee506aa33267da (verified at the start and at the end; the worktree was never edited; `git status --short` was empty both times). Every probe and mutant ran in the detached scratch worktree <SP>/INC-P2_adv_correctness at 8abc5115. It was removed with `git worktree remove --force`, and `git worktree list` no longer shows it. The scratch app files were sha-equal to HEAD before the mutants and after the last restore (price_service 449a4b2b..., response_builder b4ce8921..., SCS d53db27c..., text_routes 697d52ac...). The frozen pair was re-hashed at the start and at the end: 43d309db521ca62b7df79450e937a0eb44f54c839e8843a4514960dd0bae0dee and 07d72b74a83b7a8d104354ac92dd6fe60b756cbae80219155bf28654e2b69b86. The committed blobs match too; the scratch checkout was rewritten to the LF blob bytes before any run. Nothing here is phone proof.

## 1. Runs (gate.py, the pinned venv, one pytest at a time)
- RED pair ON (ENABLE_PRICE_NOT_LOST=true in the runner env only): 495 passed.
  [pyt] tag=inc-p2-adv-c-on start=2026-11-17 00:55:18 end=2026-11-17 00:55:30 elapsed=11s bound=600s status=OK rc=0
- RED pair OFF: 495 passed (includes the A34 12-cell and B17 24-cell digest rows, B07, B22[None], H4, R03, S03).
  [pyt] tag=inc-p2-adv-c-off start=2026-11-17 00:55:37 end=2026-11-17 00:55:48 elapsed=12s bound=600s status=OK rc=0
  [netguard] only the sentinel neutralized.supabase.invalid:443 on the six route rows (both runs); [hermeticity] clean.
- Probe file 1 (<SP>/INC-P2_adv/test_zz_p2adv_probe.py, 9 nodes): 9 passed.
  [pyt] tag=inc-p2-adv-c-probe1 start=2026-11-17 00:53:06 end=2026-11-17 00:53:10 elapsed=4s bound=600s status=OK rc=0
- F3 base-equivalence: the one new SCS line was removed on a byte copy, probe p3 was run, and the file was restored and sha-verified.
  [pyt] tag=inc-p2-adv-c-p3base start=2026-11-17 01:10:48 end=2026-11-17 01:10:52 elapsed=3s bound=600s status=OK rc=0
- Wire-state probe (<SP>/INC-P2_adv/test_zz_p2adv_wire.py, 26 nodes): 26 passed.
  [pyt] tag=inc-p2-adv-c-wire start=2026-11-17 01:10:58 end=2026-11-17 01:11:02 elapsed=4s bound=600s status=OK rc=0
- Mutants: 45 single runs, tags inc-p2-adv-c-mut-<id>, from 00:58:22 (m01) to 01:10:28 (x24). Each is FAIL rc=1 (killed) or OK rc=0 (survived); every [pyt] line is in mutants_result.jsonl and the logs are mut_<ID>.log. 0 TIMEOUT, 0 BUSY, no [gate] wait reported.

## 2. Findings

### MAJOR-1: with the flag ON, a wire fault leaks the private `_p2_*` keys to the wire (the legacy `products` alias, then History)
- Code: response_builder.build_comparison_response, `if _p2_wire: result["products"] = _p2_alias_products(...)` / `else: result["products"] = product_data`. When `_p2_wire_prices` returns None (its own except arm, one WARNING), product_data is shipped as it is. It still carries `_p2_shown_price` (the whole stashed price dict: amount, url, title, retailer, source_method) and `_p2_open`. A flag flip between the reconcile read and the response_builder read has the same effect.
- Measured (probe p1; T3-01 pair, flag ON, fix ON, cap1, p2_wire_price raising as B18 does): p2_keys(body) = ['_p2_shown_price', '_p2_open']; body["products"][1]["_p2_shown_price"]["amount"] = 58.11, while overview[1] is pending size_mismatch.
- This contradicts the RB comment ("the build ships the flag-OFF body"), the PR body ("The private `_p2_*` keys never reach the wire") and GATE section 5 ("stripped everywhere"). B18 asserts only the overview (prove-nothing for the alias).
- Fix (small): in the else branch, ship copies without the `_p2*` keys whenever any product carries one. Add an assertion p2_keys(body) == [] in B18.

### MAJOR-2: an unflagged line changes the flag-OFF behaviour (the argument is evaluated outside the guard)
- Code: SCS `_get_price`, before the L1 read: `_ps_mod.price_trace_product(_shopping_cache_key(brand, name, variant))`. price_trace_product guards itself, but `_shopping_cache_key` runs outside it, and it raises AttributeError for a truthy non-str variant (`variant.lower()`). At base this helper first runs at :7324, after the L1 / L2 hit returns. W4-7 treats an int variant as a real malformed-identity class (tests/test_w4_7_factcheck_shopping_key.py::test_c10, ("Apple", "iPhone 15", 256)).
- Measured (probe p3, flag OFF and ON, `_get_price("Dior", "Sauvage", 5, "bahrain", ...)` with an L1 hit): HEAD raises AttributeError("'int' object has no attribute 'lower'"). The same bytes without that one line return the cached 50.000 price (p3base, both flag values). The price task fails, so the product ships pending where base served the cached price.
- This breaks P2-1 / P2-19 (flag OFF byte-identical except the log lines) and P2R-11 (unflagged ledger appends must be pure in-memory appends inside a guard). The PR body's "OFF: every response body ... identical" is false for this input.
- Fix: compute the key inside the guard (for example via `_shopping_cache_key_or`), and add a flag-OFF PIN row for an int-variant L1 hit.

### MAJOR-3: P2-7 caches a partner-dictated size under the shared untyped key. Later pairs, and the flag-OFF code after a rollback, then lose a price that base shows.
- Code: SCS `_p2_cache_reselected` writes every `_p2_reselected` side under that side's own request key. In the typed branch of `reconcile_pair_sizes_v2`, an UNTYPED side is re-selected to the OTHER side's typed size (`target = typed[i] if typed[i] is not None else typed[1 - i]`), so the bare-name key of an untyped product receives a size nobody typed for it. A cache hit returns no candidates, so a later pair cannot re-select away from it.
- Measured (probe p2; "Ted Baker M 30ml" vs "Sauvage EDP", Sauvage live at 100 ml with a 30 ml candidate, fix ON): with the flag ON, the write is `price:75da9259ce6d` = Sauvage 30.000 "Sauvage EDP 30ml", TTL 604800. That key is the one `_get_price` reads for "Sauvage EDP". With the flag OFF nothing is written.
- Measured (probe p2b; the next request "Sauvage EDP" vs "Bleu de Chanel EDP", Bleu 100 ml):

  | cell | clean L1 (Sauvage 100 ml) | polluted L1 (Sauvage 30 ml) |
  |---|---|---|
  | flag OFF (also the state after a rollback) | both shown | Sauvage PENDING size_mismatch |
  | flag ON cap0 | both shown, same_size | Sauvage held + offsize_listing 30 |
  | flag ON cap1 | both shown, same_size | 30 ml vs 100 ml, different_sizes, no comparison |

  The same holds in the no-typed branch for any common size other than 100.
- PR body SL5 / K-2 states that the entry is read by later pairs. It does not say that those pairs then pend or hold a side base shows (the P2R-26 harm carried across requests), nor that the entries outlive the flag. The FLIP NOTE's "Rollback: set it false (read per call, immediate)" and the CLAUDE.md "rollback = unset it" are false for up to 7 days (genuine) or 24 h (converted).
- Ruling needed:
  - (a) Narrow the write to a re-selection whose target is the side's OWN typed size, or the 100 ml flagship basis an untyped key shows anyway (P2R-5's first clause), and add a RED row for the mixed pair.
  - (b) Keep the write, and rewrite SL5 and the flip note with the cross-pair and post-rollback effects plus the owner-side purge option.

## 3. Mutants (byte copy, one exact edit matching once, both frozen files, flag ON in the runner env, --maxfail=4, restore, sha256 compare; 45/45 restores verified)
Every kill is an AssertionError (`E   AssertionError` / `E   assert` in the log); none relies on an escaped exception.
- Gate-assigned: N01 KILLED (a04_a05 cap0), N02 KILLED (a09 cap0; price_size_cap() forced True), N04 KILLED (r4 a30_whatnot_cand cap0), N06 KILLED (r1c), N07b KILLED (a08 gate_off), N08 KILLED (a09 cap0), N09 KILLED (f06).
- B's set:
  - M01 KILLED (a01); M03 KILLED (a06, a19); M06 KILLED (a04_a05); M08 KILLED (a46); M10 KILLED (a08); M14 KILLED (a04_a05); M15 KILLED (a04_a05); M18 KILLED (a04_a05).
  - M21 KILLED (a25); M25 KILLED (a29); M29 KILLED (b04_b05); M36 KILLED (b02); M44 KILLED (h1); M45 KILLED (h2); M46 KILLED (a09); M47 KILLED (a09).
  - M49 KILLED (f2); M57 KILLED (b06); M59 KILLED (a38); M65 KILLED (r01).
  - Re-expressed: X06 = M17 KILLED (a22); X10 = M27 KILLED (b10); X12 = M39 KILLED (a20); X14 = M63 KILLED (b08); X15 = M51 KILLED (l1); X19 = M56 KILLED (b22); X23 = M40 KILLED (a37).
- Mine: X11 (the alias keeps _p2 keys) KILLED (a04_a05); X20 (the cache writes every side) KILLED (b06); X21 (the v2 estimate skip removed) KILLED (a16); X22 (RB cap forced False) KILLED (a09); X24 (the v2 candidate marketplace filter removed) KILLED (a30).
- SURVIVED, test gaps:
  - X01 `_P2_FLOOR_ML` 30 -> 20: no row between 20 and 29 ml.
  - X04: the X1-R12 url condition of `_p2_stamp_size` (DG3) is unpinned.
  - X05: the region-currency guard on the restore is unpinned.
- SURVIVED, equivalent:
  - X02 / X03 / X07 (the floor and marketplace checks in the cache write, the wire floor): the re-selected or stashed price already passed `_p2_usable_candidates` and the v2 floor.
  - X16 (the bind ignores the flag): the routes pass the keyword only with the flag ON, and the wire is gated.
- Totals: 45 run, 38 KILLED, 7 SURVIVED (3 gaps, 4 equivalent).

## 4. Runtime truth of the claims
- Flag-OFF identity: the RED OFF run is green, including the A34 / B17 digests. Two exceptions: MAJOR-2 (a non-str variant on an L1 hit) and MAJOR-1 (a flip between the reconcile and the build).
- Wire states against RED_AMEND_REPORT section 4 (both fix cells, OFF / cap0 / cap1): T3-01, A19, A08, YSL / Lancome, the mixed pair in both orders, and A30 all match. A30: OFF shows Whatnot 50.76 + Bleu 91.78; cap0 and cap1 show Dior 70.000 at 75 ml + Bleu at 100 ml, and the consumers see both sides pending (P2R-31). On the normal path no `_p2` key reaches the body in any cell.
- P2-4 prompt: `_verdict_safe_product` drops every `_`-prefixed key before json.dumps, and `build_verdict_prompt` reads only the category, so the stash never reaches the prompt.
- Error-handler mapping: no new exception class and no change to error_handler.py. The only new raise is MAJOR-2, inside the price task: `_fetch_product_data` absorbs it as a missing price, and no 5xx follows.
- Billing R-A3: no abstain, refund or quota path is touched.
- Contract freeze: with the flag ON, only additive keys appear (size_ml, per_ml, offsize_listing, pair_price_sizes), except MAJOR-1's private keys. No existing key is renamed or retyped.

## 5. Minors (documentation rulings)
- m1 The PR body proof table is stale against GATE sections 6-8. "Today's bundles ... send no price_size token" is false: the fourth update (c5a02157, from 2e7a1229) has been live since 23:46 AST and sends it. The table does not name the cap1 / cap0 cell per section 8. The P2R-37 sentence is paraphrased rather than stated.
- m2 "Bounded at 1.0 s" holds only with ENABLE_ASYNC_REDIS_OFFLOAD on. In production (absent), the Upstash GET / SET is synchronous on the loop, and wait_for cannot preempt it. B06d hangs an async stub only.
- m3 CLAUDE.md row and PR body: "is never pended for size" is inaccurate (a typed side at another size, and an untyped side held without the token, stay pending size_mismatch). "Every price-comparing consumer receives exactly the flag-OFF pending inputs" is false where rule 4 projects a side flag OFF shows (A19 / A30).
- m4 Miss-ledger key mismatch: notes are keyed by `_shopping_cache_key(brand, name, variant)`, while PRICE_OUTCOME reads by `pd["full_name"]` = dedup_brand_name(brand, name + variant). ('', 'Sauvage EDP', 'EDP') -> 'Sauvage EDP' vs 'Sauvage EDP EDP'; ('Dior', 'Dior Sauvage', 'EDP') -> 'Dior Dior Sauvage EDP' vs 'Dior Sauvage EDP'. For those shapes the canary reads miss=none.
- m5 A floor pend logs reconcile=reselect (`_p2_trace_reconcile` labels any non-size_mismatch change as "reselect"); miss_rule=floor is still printed.
- m6 The three unpinned guards: X01, X04, X05.
- m7 GATE section 1 gives 98,120 B for the pure RED file; the file is 93,227 B (the sha matches).
- m8 PRICE_OUTCOME prints once per product per build (4 lines when a partial is built); this is stated.

## 6. Prove-nothing rows
- B18: the overview only, not the alias or History (MAJOR-1).
- B06d: the async stub only (m2).
- B04 / B05 / B06: the same pair reads back; no cross-pair or flag-OFF re-read (MAJOR-3).
- A22: no currency cell (X05).
- The F rows: no listing between 20 and 29 ml (X01).
- The A21 stamp rows: every fixture has a url (X04).

## 7. GREEN report claims checked
- Verified: HEAD and the frozen hashes; the file SHA256s (the four app files and CLAUDE.md); ON / OFF 495 / 495; CRLF kept (the CR count equals the line count); 0 new bytes > 127; the CLAUDE.md block sits after INC-I2e and before `## Tests`; the SCS hunks are outside 6030-6450; text_routes changes only the three call sites; DG1-DG6 read as described.
- Not re-measured: the comm set and the jest fences (the engineering lens).

Files under <SP>/INC-P2_adv/: test_zz_p2adv_probe.py, test_zz_p2adv_wire.py, probe_out/{p1,p3base,wire}.json, mutants_adv.py, mutdrive_adv.py, mutants_result.jsonl, mut_<ID>.log, killtype.py, p3base.py.
