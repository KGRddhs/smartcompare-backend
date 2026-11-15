## S95-LG URL-WINNER-GUARD: link compares get the scorer's winner and the prose reconcile (dark)

New flag `ENABLE_URL_WINNER_GUARD`, default OFF and read per call. With the flag OFF, the link path is byte-identical to main.

### Why
With `ENABLE_ANTHROPIC_VERDICT` on, the text path hands the verdict the deterministic scorer's winner (the S81-07c fixed winner block) and then reconciles the prose. The link path did neither: a link compare's winner was the model's own pick, unscored and unmeasured.

### What the flag does
In `compare_from_urls`, after the category and links-gate decisions:
- The deterministic scorer runs on per-product SHALLOW COPIES of the link products. Each copy carries `reviews.rating` and `reviews.count`, lifted to the top level and parsed exactly as `result_gate._url_number` parses them: numeric JSON-LD strings are accepted, `0 < rating <= 5`, and the count is a whole number `>= 0`. The delivered products are never changed.
- The verdict call receives the scores summary and the scorer's winner index through one `**verdict_kwargs`. On the Claude verdict, the existing S81-07c fixed winner block applies.
- After a DELIVERED verdict only, `reconcile_winner_prose` runs on a snapshot. If it raises, the delivery is restored to the verdict exactly as the model wrote it.
- The guard SKIPS a cross-currency pair, because the scorer compares raw amounts: when both prices carry an amount and their currency codes differ, the base call runs and one constant line is logged, `[URL_GUARD] skipped reason=currency_mismatch`.
- A scorer or reconcile exception degrades to the base behaviour with one constant warning that carries the type name only.

### Tests (four files, written before the code at each round)
- `tests/test_s95_lg_url_winner_guard.py`, the RED file. At base, 14 RED nodes fail on assertions and 8 PINs pass. P1 proves OFF identity with the full configuration and a base golden.
- `..._adapter.py`, the rating lift and non-mutation rows.
- `..._fix2.py`, the cross-currency skip, the validated lift, the snapshot restore, the two warning arms, and the JSON-LD string ratings (G10 / G10c against `_url_number` on 36 values, and G13 from the re-verifier's probe cases).
- E1, `tests/test_s81_s07c_role_fix.py::test_v09_url_caller_unchanged`, is re-pinned to the new call shape: exactly one verdict call, plus `**verdict_kwargs`, bound empty unless the guard is on.

### The chain (the leaner chain, SAFE: one adversary, then a re-verifier after each app/ fix round)
1. RED.
2. GREEN, blocked correctly on the orchestrator's lift ruling against a frozen row (a ruled one-line pin-fix).
3. FIX-1, then the adversary: NOT READY. MAJOR-1: a BHD 45 / AED 380 pair shipped the dearer product.
4. FIX-2 (the currency skip and three hardenings), then the re-verifier: NOT READY. MAJOR-R1: the orchestrator's "never a string" lift rule dropped JSON-LD string ratings, so mixed pairs shipped the worse-rated product.
5. FIX-3 (main 6104eebd merged in, with `CLAUDE.md` resolved by a proven union with INC-I1's block, and the `_url_number` parse), then the re-verifier: SOUND.

The comm set at the head is 138 files; its failing set equals the base record recomputed at 6104eebd (9 known environment nodes). Every mutant of each round is killed (M1-M23, MF1-MF7).

### Stated limits
- Link products carry less evidence than text-path products; `fact_check` is not lifted. An exact scorer tie resolves to index 0, as on the text path.
- No preferences, behaviour or cohort input in link mode (as at base). `ENABLE_WINNER_PROSE_RECONCILE` governs the template restore as on the text path.
- Same-currency non-BHD pairs are scored on raw amounts against the BHD price-tier breakpoints. The re-verifier's grid found electronics affected and fragrances not; the text path does the same in a non-BHD region.
- Two pages with no extracted currency both default to their retailer's code.
- Link ratings are read on the 5-point scale, as the result gate reads them, so a 10-point page's rating at or under 5 is misread.
- Under ON, the existing `WINNER_INDEX_MISMATCH` warning names the two products' display names, as on the text path.
- The three new test files are not black-clean, so they are not on `.github/black-clean-paths.txt`. CI is unaffected.
- Link verdicts are not covered by the S81-07 measurement harness.

### After the merge (the relay's window, nothing flips here)
- Set `ENABLE_URL_WINNER_GUARD=true` on web in its own window.
- Canary on real link compares: the count of `WINNER_INDEX_MISMATCH` on the url path; zero `[URL_GUARD] scorer failed` / `reconcile failed`; the count of `skipped reason=currency_mismatch`; no rise in 4xx / 5xx on `/api/v1/url/compare`; the declaration names the shipped winner.
- Rollback: unset the variable (read per call).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
