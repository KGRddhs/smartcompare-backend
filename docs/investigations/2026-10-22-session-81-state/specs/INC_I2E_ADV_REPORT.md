# INC-I2e GUARD-SHORT-LINE: adversary report (LC-1, correctness lens + second lens folded in)

Head c070d1366723f18b4772f1eaac393af8f6e7d9ad on fix/inc-i2e-guard-short-line, base b0ad260363e0cf0074e4ee596b140d073466e92a. Read-only toward W; no scratch worktree was needed (base module read by `git show` into this folder, loaded by path in the probe).

## VERDICT: SOUND (no BLOCKING, no MAJOR; 5 MINOR -> stated limits / PR-body wording)

## 0 The commit
`git show --stat`: exactly four paths (.github/black-clean-paths.txt +1, CLAUDE.md +17/-1, app/services/image_relevance.py +159, tests/test_inc_i2e_guard_short_line.py +662). RED file sha256 38090ba9... on disk = frozen. Working tree clean. ruff E9,F63,F7,F82 "All checks passed!", black --check "2 files would be left unchanged" (re-run by me). `zip(..., strict=False)`: runtime.txt python-3.12.9, pyproject >=3.12, CI 3.12: safe.

## 1 OFF byte identity
- Text: `diff` of base `check` vs head `check` = only the two added lines `if short_line_enabled(): return _check_short_line(...)` (image_relevance.py:502-503); the rest of `check` (504-521) is the base text byte for byte. `_line_tokens` unchanged; `identity()` adds the `_line_keys` call (:481) and four NEW defaulted fields at the END of the frozen `Identity` (:357-360), read only in `_check_short_line`. No Identity constructor outside identity() (git grep app tests scripts).
- Runs (flag unset): `[pyt] tag=s96e-adv-red-off start=2026-11-16 20:49:53 end=2026-11-16 20:49:56 elapsed=3s bound=600s status=OK rc=0` 20 passed; [hermeticity] sentinel checked 20 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
- Flag exported true for one call: `[pyt] tag=s96e-adv-red-on ... elapsed=3s bound=600s status=OK rc=0` 20 passed; [hermeticity] 20; [netguard] 0.
- Extra (S exported true): the INC-I1 / INC-R1 suites `[pyt] tag=s96e-adv-i1-on start=2026-11-16 20:49:59 end=2026-11-16 20:50:12 elapsed=13s bound=1200s status=OK rc=0` 364 passed; [hermeticity] 364; [netguard] 0 (no INC-I1 accept/reject row changes under S ON).
- Probe OFF: 426 rows, head == base on all 426 (probe_table.txt line 1).

## 2 Flag-mix walk (G = ENABLE_IMAGE_RELEVANCE_GUARD, S = this flag, R = ENABLE_PRODUCT_RESOLVER)
Seams at the commit: relevance_kwargs image_relevance.py:592-610 (`if not guard_enabled(): return {}` :597, `if is_vision: return {}` :599); the ONE call site structured_comparison_service.py:6338 inside `_fetch_product_data` (:6018; brand/name :6031-6032, is_vision :6039); the KB-served branch :6326 (`kb_serve.served(_kb["image_url"]) if (_kb and _kb["image_url"]) else get_product_image_url(...)`: never builds a RelevanceCall); image_service.py:357-358 builds RelevanceCall only when `relevance is not None and guard_enabled()`; `check` reached only by RelevanceCall.accept :668 (search_payload, serper_images), _organic_reason :684 (organic_passes :686, accept_pick related items), accept_pick no-related :712 `check(self.ident, (), ())`; accept_scheme :670-678 (piggyback) never calls check; Tier-1 query image_query :566 / RelevanceCall.query :630 unchanged (uses product_name only). Explicit typed pair: brand "" at scs :4490 (sync) and :5204 (stream) (also :1975); apply_resolution product_resolver.py:1303, brand = side.brand :1323, name = side.line :1324. Only get_product_image_url caller: scs :6326; no app module other than image_service calls check.
- G OFF, any S, any R: relevance_kwargs -> {} at :597, image_service never builds RelevanceCall, check (and so short_line_enabled) never runs; S never read (P3). Unchanged.
- G ON, S OFF, R OFF (production today): check :502 reads S false -> base body :504-521; typed pairs (brand "") take the base empty-brand rule; q= parser path takes the base brand-known rule (short lines refused). Byte-identical (P1, probe OFF).
- G ON, S OFF, R ON: apply_resolution sets brand = house, name = line -> brand-known base rule: `name_tokens` empty for Y / M / N(deg)5 / L'Eau d'Issey -> "name" at every tier (P2 pins it). The hazard; unchanged by this unit.
- G ON, S ON, R OFF: typed pairs -> _check_short_line rule 2 (:550-564: every sig2 token covered by a token or a join; short2 only when sig2 empty; then the fragrance word); q= -> rule 1 (:533-549).
- G ON, S ON, R ON: resolver lines -> rule 1; probe "known" rows: Y, M, N(deg)5, No 5, J'adore, Light Blue, L'Eau d'Issey right titles all move rej:name -> ACC.
- Camera: is_vision -> {} at :599 (and scs :6479 page-image guard is `not is_vision`): never reaches check. accept_pick with no related item: check(ident, (), ()) -> S ON brand known: brand test on empty t|h -> "brand" (:536-539); brand empty: sig uncovered or short not <= {} -> "name"; same reasons as base.

## 3 False-accept / false-reject probes (probe.py, probe_off.json, probe_on.json, probe_table.txt)
17 line groups (Y, M, N(deg)5 with typed N(deg)5 / No 5 / No.5 / N5 / N(ord)5, No 5, J'adore, Light Blue, L'Eau d'Issey, Bleu de Chanel, Sauvage, 212, CK One, Si, 1 Million, Eau de Parfum, brand-only, L'Eau, 5), brand known AND the typed empty-brand shapes, right / flanker / wrong-same-house / wrong-house titles, texts (title, "Sephora"), host sephora.ae. 426 rows. Base column identical in both runs.
ON vs base, cases flagged:
- NEW false-accept, inside stated limits: L'Eau d'Issey known accepts `L'Eau Majeure d'Issey`, `Pleats Please L'Eau`, `Eau d'Issey` (L-3); typed `Issey Miyake Leau Dissey` accepts `L'Eau Majeure d'Issey` (L-3 by joins); Si known accepts `Giorgio Armani's I Love Gift Set` (L-7, s+i).
- NEW false-accept, OUTSIDE L-1..L-7 (MINOR, see F-1 / F-3): line `Eau de Parfum` (Chanel) accepts `Chanel Coco Mademoiselle Eau de Parfum` and `Chanel Chance Eau Tendre`; brand-only (line blank -> product name = brand) accepts `Chanel Coco Mademoiselle Eau de Parfum`; line `L'Eau` (Chloe) accepts `Chloe Nomade L'Eau de Parfum`; line `5` (Chanel) accepts `Chanel Chance Eau Tendre 5 ml` and `Chanel Coco 5 oz`.
- NEW false-reject (MINOR, F-2): typed `Chanel N(deg)5` (brand empty) refuses `Chanel Number 5 Eau de Parfum` and `Chanel #5 Eau de Parfum`, which base accepted (base accepted ANY Chanel title for that typed name, Coco Mademoiselle and Bleu de Chanel included, which ON now correctly refuses).
- Unchanged false accepts (base = ON): typed `YSL Y` accepts `YSL L'Homme`, `YSL MYSLF`; typed `Yves Saint Laurent Y` accepts Libre / Black Opium / Kouros; typed `Ted Baker M` accepts Woman / Tonic / Polly / W; Light Blue known accepts `Dark Blue`; Sauvage <-> `Eau Sauvage`; 1 Million known accepts `Lady Million`; typed `L'Eau d'Issey` accepts every `... d'Issey` title. (F-4)
- Unchanged false rejects: Light Blue / CK One / Si / 212 / Sauvage flankers without a fragrance word on the typed path (fragrance_word); `D&G` titles fail the brand test; brand-known `CK One` vs `CKOne` (ck is a brand form, so no join) (F-5).
- No case where ON accepts a wrong-HOUSE title (every X row rejected both states).

## 4 CLAUDE.md block vs the code
- Flag sentence and the INC-I2e block are the only CLAUDE.md change (word diff); the added text is ASCII.
- Effect bullet matches _check_short_line (:533-549 rule 1 with 1a/1b/1c/1d, :550-564 rule 2) and fold_numero / _line_keys / _candidate_keys.
- (a) input paths: HomeScreen.tsx:458 is the only streamComparison caller in SmartCompareApp/src and passes {product_a, product_b}; compareTextPair (api.ts:1041) has no screen caller; the Link-mode `/api/v1/url/compare` (HomeScreen.tsx:618) goes through the url_extraction_service URL compare (extract_from_url x2, :1473 onward), which never calls `_fetch_product_data` or get_product_image_url (the only call site is scs:6326); camera (identifyFromImages, ResultsScreen.tsx:305) -> `_vision` -> {}. Claim correct.
- (b) phone effect: all four sentences reproduced by the probe (typed `Chanel No 5` vs `CHANEL N(deg)5` rej->ACC; typed `Dior Jadore` vs J'adore titles ACC; `Light Blue` vs `Lightblue` ACC; typed `Chanel N(deg)5` vs `No 19` ACC->rej).
- (c) L-1..L-6 each confirmed by a probe row; L-6 confirmed (typed `YSL Y` vs a `Yves Saint Laurent Y` title rejected both states).
- The proof sentence names YSL Y vs Ted Baker M without "R ON" (F-4).

## 5 Comm set (union rule)
206 files (sha 84667417...) = GREEN chunks. Spot-check: CLAUDE.md readers by grep (`CLAUDE.md|CLAUDE_MD` under tests) all in the set except tests/.pre_impl_failures.txt (not a test); test_ci_gates.py and test_behavior_dimension_translation.py present; every named source-scanning pin present; every test_inc_* present; black-clean-paths readers: only tests/test_precommit_hook.py (excluded by rule; .githooks untouched); an independent grep of 430 candidate files (CLAUDE / image_relevance / image_service / ENABLE_IMAGE / black-clean / pkgutil / importlib) left out only the unit's own RED file and unrelated importlib users (scripts.eval_runner, sentry_service, price_service, app.main). Complete.

## 6 Findings
- F-1 MINOR (stated limit L-8): rule 1d, a line with nothing to match (`Eau de Parfum`, a blank line falling back to the brand) accepts ANY fragrance-word title of the house (`Chanel Coco Mademoiselle Eau de Parfum`); base refused every candidate. Reach today: q= API callers only (the resolver always supplies a line). Spec rule 1d by design and described in the CLAUDE.md effect text, but absent from L-1..L-7.
- F-2 MINOR (extend L-4): the numero fold covers n / no / nr only; with typed `Chanel N(deg)5` (or No 5) a `Chanel Number 5` or `Chanel #5` title is refused; base accepted them (only because it accepted every Chanel title for that typed name).
- F-3 MINOR (extend L-2): a one-character whole line keeps a DIGIT (line `5`: `Chanel Chance Eau Tendre 5 ml` passes, the number-before-unit rule applies to the line, not to t2) and an elision letter when it is the whole line (`Chloe L'Eau` -> `l`: `Chloe Nomade L'Eau de Parfum` passes).
- F-4 MINOR (PR body / flip note wording; optional one-line CLAUDE.md amendment): on the typed path (resolver OFF) a one-letter line token is ignored whenever the typed name has a significant token (spec rule 2): typed `YSL Y` / `Ted Baker M` accept any YSL / Ted Baker perfume picture in BOTH states. The CLAUDE.md proof sentence "until the phone shows both bottles for `YSL Y` vs `Ted Baker M`" omits spec section 8's "G ON, R ON and S ON" and "the picture is the named line": read right after the S window (R OFF) it cannot discriminate.
- F-5 MINOR (stated limit): a join is never made with a brand form, so a joined spelling of an alias-brand line (`Calvin Klein` line `CK One` vs title `CKOne`) stays refused on the brand-known path (base too).

## Files
probe.py, probe_off.json, probe_on.json, probe_table.txt, tab.py, adv_drive.sh, red_off.log, red_on.log, i1_on.log, ir_base.py, ir_head.py, comm_set.txt (this folder).
