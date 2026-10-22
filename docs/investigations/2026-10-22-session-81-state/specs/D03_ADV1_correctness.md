# D03 DENY-AND-GUARDS - adversary report, lens CORRECTNESS

- Unit D03 (`ENABLE_DATA_GUARDS_V2`), worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-d03`, branch `feature/s81-d03-deny-and-guards`.
- HEAD verified `5244f7165dbde49579a9f4147229b20050427c18` at start (19:36 AST) and at the end (20:23 AST); `git status --short` of the unit worktree EMPTY at the end; the unit worktree was never edited.
- RED file `tests/test_s81_d03_deny_and_guards.py` sha256 `ae8fffc7ffe50205af9170a82f1de22ca38e629482b1afc93bf1c0181610449c`: MATCH at start and at the end.
- All probes and mutants ran in my own detached scratch worktree `<scratchpad>/D03_adv_correctness` at 5244f716 (removed with `git worktree remove --force`; `git worktree list` no longer shows it). A fresh checkout writes the two NEW files (`app/services/deny_hosts.py`, the RED file) as CRLF (core.autocrlf), so both were byte-copied (shutil) from the unit worktree; all 10 diff files then sha-identical to the unit worktree (deny_hosts `750ea9ed...`, image `31d67f16...`, price `25416489...`, rating `64abc44c...`, review `05d7c079...`, descriptor `f627e4e9...`, router `afd3dd24...`, scs `ec5b8d2b...`, CLAUDE.md `4cc69418...`, RED `ae8fffc7...`); the 8 app shas re-verified identical after the last mutant restore.
- Model: Opus 5.5. Lock `.qa-mutation.lock` held only during the two mutation batches, removed. No orphan pytest of mine (one foreign `pyt.py` precommit-hook run seen at the end, not mine, untouched). No .env read or copied; no secret value anywhere.
- No `X19` mutant exists for D03: the "X19 block-move" phrase is a template leftover in `scripts/wf_unit_green.js:75`; I applied three hand block-move mutants instead (C6, D6, E11 below).

## Verdict: NOT_READY (0 blocking, 1 major, 7 minor)

## Runs ([pyt] lines; summaries after ::)

```
[pyt] tag=d03adv-c-unit-off start=2026-10-22 19:44:34 end=2026-10-22 19:44:43 elapsed=8s bound=600s status=OK rc=0 :: 250 passed; [hermeticity] sentinel checked 250 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=d03adv-c-unit-on start=2026-10-22 19:45:00 end=2026-10-22 19:45:09 elapsed=9s bound=600s status=OK rc=0 :: 250 passed (ENABLE_DATA_GUARDS_V2=true exported for the runner only); hermeticity 250; netguard 0
[pyt] tag=d03adv-c-probe-catoff start=2026-10-22 19:52:27 end=2026-10-22 19:52:30 elapsed=3s bound=600s status=OK rc=0 :: 6 passed (probe file, scratch only)
[pyt] tag=d03adv-c-probe-catoff2 start=2026-10-22 19:52:58 end=2026-10-22 19:53:01 elapsed=3s bound=600s status=OK rc=0 :: 6 passed (review probe re-run with deep-copied inputs)
[pyt] tag=d03adv-c-probe-caton start=2026-10-22 19:53:15 end=2026-10-22 19:53:18 elapsed=3s bound=600s status=OK rc=0 :: 1 passed (ENABLE_BH_GCC_CATALOG_SOURCES=true)
[pyt] tag=d03adv-c-probe-w41 start=2026-10-22 20:19:52 end=2026-10-22 20:20:05 elapsed=13s bound=600s status=OK rc=0 :: 1 passed (W4-1 shopping probe)
[pyt] tag=d03adv-c-onreds-on start=2026-10-22 20:20:40 end=2026-10-22 20:21:04 elapsed=23s bound=600s status=FAIL rc=1 :: 3 failed, 113 passed, 1 deselected (flag ON)
[pyt] tag=d03adv-c-onreds-off start=2026-10-22 20:21:20 end=2026-10-22 20:21:38 elapsed=18s bound=600s status=OK rc=0 :: 116 passed, 1 deselected; hermeticity 116; netguard 0
```
Plus the 47 mutant runs in the mutation table (each its own [pyt] line, bound 600, flag unset in the runner env, the whole unit file). One pytest at a time throughout.

## Runtime truth of the claims (GREEN report, CLAUDE.md row, PR body)

| Claim | Measured | Verdict |
|---|---|---|
| Unit file 250 nodes green ON and OFF | 250/250 both | TRUE |
| `COUNTERFEIT_KEYWORDS` 21, `LUXURY_BRAND_KEYWORDS` 29 | 21 / 29 at runtime | TRUE |
| ON the global fragrance discovery query loses `site:fragrantica.com` in BOTH catalog states | catalog OFF (44 rows -> 43 routable) and ON (319 -> 318): OFF `... OR site:walmart.com OR site:fragrantica.com`, ON `... OR site:walmart.com` | TRUE |
| `score_source(<fragrantica url>)` 1.0 -> 0.5; `registry_tier` `global` -> None | measured both catalog states | TRUE |
| Flag OFF `_routable_registry() is SOURCE_REGISTRY` | True OFF, False ON | TRUE |
| `validate_scrape_url` denies a fragrantica URL ON only | OFF True, ON False | TRUE |
| `get_rating_tier` 3 for a denied source ON | Fragrantica 2->3, fragrantica.com 2->3, Parfumo.de 3, Sephora 1 | TRUE |
| fimgs.net image invalid ON (padded too); allowed CDN kept | OFF True / ON False; CDN True both | TRUE |
| "exactly three unedited pins go red ON"; `test_review_paraphrase.py` green ON | the 4 named files: ON 3 failed = exactly `test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2`, `test_retailer_quotes_from_reviews.py::TestRetailerQuotesGraceful::test_bare_numeric_citation_also_mapped`, `test_fragrance_content_quality.py::test_review_praise_no_interior_per_domain_artifact` (AssertionError); OFF 116 passed | TRUE (for these 4 files; the 409-file ON sweep is GREEN's, not re-run) |
| Calvin Klein designer floor: 18 BHD no longer rejected ON | implausible OFF True / ON False | TRUE |
| Flag-OFF byte identity | every hunk is flag-first with the base body as the else (read line by line); OFF reader spellings pinned by P1-P14; mutants that ungate any branch (A1, C1, D5, E7, E8, E10, F1, G1, H3) all KILLED by OFF pins | TRUE (by construction + pins; no base differential run: NOT MEASURED independently) |
| Error-handler mapping / billing R-A3 / contract freeze (PLAN section 0) | the diff touches no `app/api/*`, no middleware, no `text_routes` / usage / refund code; no new error code, refusal or envelope; every new function never raises (probed with non-str / malformed inputs), so no new 500 path; response keys unchanged (ON only changes VALUES: fewer discovery hosts, `rating_source`, `retailer_quotes`, attribution text, `image_url`, guard verdicts) | TRUE: unaffected |
| Limit 5: "with `ENABLE_SHOPPING_CURRENCY_TRUTH` ON a Fragrantica Shopping link's W4-1 relabel reason reads `no_bh_evidence` instead of `global_tier`" (GREEN Q2: quoted, not measured) | TRUE for a plain fragrantica.com link; FALSE for a `/bh-en/` one: OFF `[False, ['global_tier']]` -> ON `[True, []]`, and the shopping price is relabelled `converted_usd` -> `local_bhd` | PARTLY FALSE (MAJ-1) |
| Row (8): `lv` never inside "Salvatore" etc. presented as false positives | Salvatore Ferragamo is in NEITHER brand table (grep: 0 hits in `app/`); see MIN-4 | documentation (MIN-4) |
| PR body: the flag is "the FIRST statement of every gated predicate" | 5 sites read it after a base pre-check (`if not url`, `if not source`, `.lower()` in the two guards, the base image verdict); the spec's wording is "first statement of the new branch" | wording (MIN-6) |
| GREEN Q1: in-place mutation of `SOURCE_REGISTRY` not seen by the memo | grep over app/ scripts/ tests/ for append/extend/insert/remove/pop/clear/sort/reverse/item-assign/`+=` on `SOURCE_REGISTRY`: 0 hits | accept as stated limit |

## MAJOR

**MAJ-1 - the Serper-Shopping price rung never consults the deny list, and under `ENABLE_SHOPPING_CURRENCY_TRUTH` ON D03 ON relaxes its fail-closed global-tier refusal into a genuine `local_bhd` label for a denied host (the ruling-B2 / RC1 class), contrary to the row's stated limit 5.**
- Measured (scratch probe, real functions, `price_service._shopping_bh_host_evidence(link, ask_currency="BHD", reason_out=r)` and `extract_price_from_shopping("Tom Ford Oud Wood Eau de Parfum 100ml", [{"title": <same>, "price": "BHD 45.000", "source": "Fragrantica", "link": L}], "BHD", category="fragrances")`):
  - L = `https://www.fragrantica.com/bh-en/perfume/Tom-Ford/Oud-Wood-1826.html` (the RC1 / G11b shape), W4-1 ON: evidence OFF `False ['global_tier']` -> ON `True []`; price OFF `source_method converted_usd` -> ON `source_method local_bhd`, `retailer Fragrantica`, `url` the fragrantica link, amount 45.0 BHD in both.
  - L = plain `https://www.fragrantica.com/perfume/...`, W4-1 ON: OFF `global_tier` -> ON `no_bh_evidence` (the sentence in limit 5 holds only here), price `converted_usd` both.
  - W4-1 OFF: the denied-host row is priced and shown as `local_bhd` with the fragrantica url and retailer in BOTH D03 states (the rung has no deny check at all, while the rating rung over the same shopping items skips it).
- Why it matters: ruling B2 exists so that "as if absent" (`registry_tier` None ON) can never turn a fail-closed global-tier refusal into a weaker verdict; the chokepoint (`validate_scrape_url`) covers FETCHES only, and the shopping rung (both W4-1 doors, `extract_price_from_shopping` and the scs `_seed_shortcircuit_candidates` stash) is priced from Serper data without a fetch. The row's limit 5 states the outcome of only the plain-link case; the `/bh-en/` case (the one the RED file pins for the harvest in G11b) is the opposite (a genuine label). The deny_hosts docstring also says a denied host is never "shown" by a path that consults the module; the shopping rung is a display path that does not consult it.
- Reachability (stated honestly): needs a Google Shopping row whose link is on a banned host (Fragrantica / Parfumo / Basenotes sell nothing, so practically unseen) and, for the genuine-label upgrade, W4-1 ON (production state UNKNOWN per R-A15; not a D03 precondition). The same reachability argument was not accepted for the harvest (B2 / G11b), hence MAJOR.
- Smallest fix (flag-first, OFF byte-identical): in `extract_price_from_shopping`'s candidate loop (and so the seed stash, which shares it) skip an item whose `link` `is_denied_url` or whose `source` `is_denied_source` under the flag, exactly as `rating_service.extract_rating_from_shopping` does; or, minimally, `_shopping_bh_host_evidence` returns `_no("denied_host")` under the flag before the `registry_tier` read. Add RED rows (the two links above, W4-1 ON and OFF) and a P row pinning today's OFF output. Alternative by ruling: keep the code, rewrite limit 5 to state the `/bh-en/` upgrade and the always-priced shopping row.

## MINOR (documentation / test-strength rulings)

- **MIN-1 (surviving mutant A9, prove-nothing gap for GC-3):** `_registrable_label`'s two-level branch `return labels[-3]` -> `labels[-2]` keeps all 250 nodes green. Measured at HEAD: `fragrantica.co.uk`, `www.parfumo.com.au`, `basenotes.co.uk` are denied (True); under the mutant they are not. No RED row carries an UNLISTED edition under a two-level suffix (the two-level rows in R1E_TRUE, `fragrantica.com.br` / `fragrantica.co.il`, are caught by the suffix arm first). Recommend one PIN row (those three True, plus a False row such as `co.uk` alone / `notfragrantica.co.uk`).
- **MIN-2 (surviving hand block-move D6):** moving the `collect_retailer_ratings` deny skip AFTER `seen.add(source_key)` keeps all nodes green. Under it a link-denied item with a neutral source name (ruling C12 shape: `somestore.com` + a fimgs.net link) shadows a later LEGITIMATE rating with the same source name. HEAD's order (deny before dedup) is the correct one; it is unpinned. Recommend a row: `[neutral_denied_link_item, same-source item with an allowed link]` -> the second is listed.
- **MIN-3 (review display deny bypassed by a userinfo netloc):** `review_service` checks `is_denied_host(_extract_domain(link))`, and `_extract_domain` returns the NETLOC (userinfo kept, only `www.` removed). Measured ON: a cited organic link `https://u@www.fragrantica.com/perfume/x-1.html` still renders `Per u@fragrantica.com:` and is quoted (`retailer` `u@fragrantica.com`); upper-case and `:443` netlocs ARE blanked. `rating_service` uses `is_denied_url(link)`, which ignores userinfo. Serper organic links do not carry userinfo, so unrealistic; fix is `is_denied_url(result.get("link"))` in both review sites.
- **MIN-4 (row (8) mislabels a real luxury brand as a false positive):** "never inside ... Salvatore" - Salvatore Ferragamo appears in neither `LUXURY_BRAND_KEYWORDS` nor `FRAGRANCE_BRAND_KEYWORDS`, so at base it was luxury/designer only through the `lv` substring. Measured ON: `is_luxury_brand`, `_is_designer_fragrance_name` True -> False for "Salvatore Ferragamo Uomo Eau de Toilette 100ml" and "... Signorina Eau de Parfum 100ml"; `is_implausible_low_fragrance_price(<Uomo 100ml>, 8.0)` True -> False (an 8 BHD decant-class listing now passes as the full-bottle price) and the flagship pair basis is lost; "Creed Silver Mountain Water" keeps the designer floor (creed is a fragrance house) but loses `is_luxury_brand` (shopping sort / flagship bonus). Pinned deliberately by R6a, so a ruling item: state the cost in the row and give Ferragamo a home in D03d (an ON-only token keeps OFF identical); add Ferragamo / Creed Silver pairs to the canary list next to Calvin Klein / Elvive / Centrum Silver.
- **MIN-5 (surviving mutant G3):** the ON piggyback branch's `.strip()` (`result["image_url"] = page_img.strip()`) can be dropped with all nodes green (G9c uses an unpadded url); GREEN deviation 5 / limit 8 say a padded image is taken ON, but its stored value is unpinned. One padded-input row closes it.
- **MIN-6 (PR body wording):** "the FIRST statement of every gated predicate" - true of the new BRANCH (spec 2.1), not of the predicate in `validate_scrape_url`, `get_rating_tier`, `is_counterfeit_listing`, `is_luxury_brand` and `_is_valid_image_url` (each keeps a base pre-check first); OFF identity is unaffected. Reword to "the first statement of the new branch".
- **MIN-7 (pre-existing, recorded, not D03):** `clean_review_citations` copies `reviews` shallowly (`cleaned = dict(reviews)`) and rewrites `review_summary` IN PLACE, so calling it twice on the same dict loses the citation markers (found because my first probe aliased its input). Nothing in D03 relies on it; a follow-up hygiene item only.

## Mutation table (47 on sha-verified byte copies of the GREEN bytes; 44 KILLED by AssertionError, 3 SURVIVED non-equivalent; restore sha-identical every time)

Spec ids in the second part of each name (Mxx); N = mine; X = hand block-move. Killers = the first failing test functions.

| id | status | n failed | killed by | [pyt] |
|---|---|---|---|---|
| A1-M1 reader returns True | KILLED | 88 | p11, p12, p13 (+ p1 ...) | tag=d03adv-c-A1-M1 start=2026-10-22 19:56:08 end=2026-10-22 19:56:16 elapsed=8s bound=600s status=FAIL rc=1 |
| A2-M2 reader without strip/lower | KILLED | 3 | r1h_reader_truthy | tag=d03adv-c-A2-M2 start=2026-10-22 19:56:17 end=2026-10-22 19:56:33 elapsed=17s bound=600s status=FAIL rc=1 |
| A3-M3 substring match | KILLED | 13 | g2a, r1e_false, r1f | tag=d03adv-c-A3-M3 start=2026-10-22 19:56:35 end=2026-10-22 19:56:58 elapsed=24s bound=600s status=FAIL rc=1 |
| A4-M6 port kept | KILLED | 1 | r1e_true | tag=d03adv-c-A4-M6 start=2026-10-22 19:56:59 end=2026-10-22 19:57:24 elapsed=25s bound=600s status=FAIL rc=1 |
| A5-M7 no schemeless fallback | KILLED | 1 | r1f | tag=d03adv-c-A5-M7 start=2026-10-22 19:57:25 end=2026-10-22 19:57:47 elapsed=22s bound=600s status=FAIL rc=1 |
| A6-M8 label match without boundaries | KILLED | 1 | r1g | tag=d03adv-c-A6-M8 start=2026-10-22 19:57:48 end=2026-10-22 19:58:12 elapsed=24s bound=600s status=FAIL rc=1 |
| A7-M9 KB guard reads the flag | KILLED | 8 | r9b | tag=d03adv-c-A7-M9 start=2026-10-22 19:58:12 end=2026-10-22 19:58:40 elapsed=28s bound=600s status=FAIL rc=1 |
| A8-M37 label rule dropped | KILLED | 3 | r1e_true, r1f | tag=d03adv-c-A8-M37 start=2026-10-22 19:58:42 end=2026-10-22 19:59:09 elapsed=28s bound=600s status=FAIL rc=1 |
| A9-N1 two-level suffix branch -> labels[-2] | SURVIVED | 0 | - (MIN-1) | tag=d03adv-c-A9-N1-two-level-suffix start=2026-10-22 19:59:10 end=2026-10-22 19:59:38 elapsed=28s bound=600s status=OK rc=0 |
| A10-N2 trailing dot kept | KILLED | 1 | r1e_true | tag=d03adv-c-A10-N2-trailing-dot start=2026-10-22 19:59:39 end=2026-10-22 19:59:59 elapsed=20s bound=600s status=FAIL rc=1 |
| A11-M5 fimgs.net removed | KILLED | 1 | r1d | tag=d03adv-c-A11-M5 start=2026-10-22 19:59:59 end=2026-10-22 20:00:19 elapsed=20s bound=600s status=FAIL rc=1 |
| B1-M10 descriptor DENY_HOSTS = full list | KILLED | 10 | p4, p4b, r1i | tag=d03adv-c-B1-M10 start=2026-10-22 20:00:21 end=2026-10-22 20:00:43 elapsed=21s bound=600s status=FAIL rc=1 |
| B2-M11 _deny ignores the flag | KILLED | 8 | r2a, r2b | tag=d03adv-c-B2-M11 start=2026-10-22 20:00:44 end=2026-10-22 20:01:04 elapsed=20s bound=600s status=FAIL rc=1 |
| C1-M12 _routable_registry filters OFF | KILLED | 28 | g11b, p11, p1 | tag=d03adv-c-C1-M12 start=2026-10-22 20:01:05 end=2026-10-22 20:01:28 elapsed=23s bound=600s status=FAIL rc=1 |
| C2-M13 score_source not routed | KILLED | 3 | r3a, r3b | tag=d03adv-c-C2-M13 start=2026-10-22 20:01:29 end=2026-10-22 20:01:50 elapsed=21s bound=600s status=FAIL rc=1 |
| C3-M14 get_sources_for_category not routed | KILLED | 15 | r3a, r3b, r3c | tag=d03adv-c-C3-M14 start=2026-10-22 20:01:51 end=2026-10-22 20:02:14 elapsed=23s bound=600s status=FAIL rc=1 |
| C4-M15 _registry_row_for_host not routed | KILLED | 9 | r3a, r3b | tag=d03adv-c-C4-M15 start=2026-10-22 20:02:15 end=2026-10-22 20:02:41 elapsed=26s bound=600s status=FAIL rc=1 |
| C5-M16 filter in place | KILLED | 11 | p11, p2, r3c | tag=d03adv-c-C5-M16 start=2026-10-22 20:02:42 end=2026-10-22 20:03:00 elapsed=19s bound=600s status=FAIL rc=1 |
| C6-M17 / X block-move: flag gate moved below the memo | KILLED | 3 | p2, r3c, r3d | tag=d03adv-c-C6-M17-blockmove-flag-below-memo start=2026-10-22 20:03:02 end=2026-10-22 20:03:29 elapsed=28s bound=600s status=FAIL rc=1 |
| C7-M38 memo keyed on len, no identity | KILLED | 1 | r3e | tag=d03adv-c-C7-M38 start=2026-10-22 20:03:31 end=2026-10-22 20:03:55 elapsed=23s bound=600s status=FAIL rc=1 |
| C8-M39 is_render_only_domain not routed | KILLED | 2 | r3a | tag=d03adv-c-C8-M39 start=2026-10-22 20:03:56 end=2026-10-22 20:04:21 elapsed=25s bound=600s status=FAIL rc=1 |
| D1-M18 no skip in extract_rating_from_shopping | KILLED | 3 | r4b, r4d, r4e | tag=d03adv-c-D1-M18 start=2026-10-22 20:04:22 end=2026-10-22 20:04:45 elapsed=23s bound=600s status=FAIL rc=1 |
| D2-M20 collect_retailer_ratings not filtered | KILLED | 1 | r4f | tag=d03adv-c-D2-M20 start=2026-10-22 20:04:47 end=2026-10-22 20:05:13 elapsed=26s bound=600s status=FAIL rc=1 |
| D3-M21 link not checked | KILLED | 2 | r4d, r4f | tag=d03adv-c-D3-M21 start=2026-10-22 20:05:15 end=2026-10-22 20:05:44 elapsed=29s bound=600s status=FAIL rc=1 |
| D4-M43 get_rating_tier not routed | KILLED | 1 | r4a | tag=d03adv-c-D4-M43 start=2026-10-22 20:05:46 end=2026-10-22 20:06:10 elapsed=24s bound=600s status=FAIL rc=1 |
| D5-M44 _rating_source_denied ungated | KILLED | 8 | p3 | tag=d03adv-c-D5-M44 start=2026-10-22 20:06:11 end=2026-10-22 20:06:33 elapsed=22s bound=600s status=FAIL rc=1 |
| D6-X block-move: deny skip after the dedup | SURVIVED | 0 | - (MIN-2) | tag=d03adv-c-D6-X-blockmove-deny-after-dedup start=2026-10-22 20:06:34 end=2026-10-22 20:07:05 elapsed=31s bound=600s status=OK rc=0 |
| E1-M23 no plural | KILLED | 2 | p6 counterfeit | tag=d03adv-c-E1-M23 start=2026-10-22 20:07:53 end=2026-10-22 20:08:25 elapsed=32s bound=600s status=FAIL rc=1 |
| E2-M46 alnum boundary | KILLED | 2 | p6 counterfeit | tag=d03adv-c-E2-M46 start=2026-10-22 20:08:27 end=2026-10-22 20:08:56 elapsed=29s bound=600s status=FAIL rc=1 |
| E3-M47 copycat dropped | KILLED | 1 | p6 counterfeit | tag=d03adv-c-E3-M47 start=2026-10-22 20:08:58 end=2026-10-22 20:09:32 elapsed=34s bound=600s status=FAIL rc=1 |
| E4-M24 margiela neutralises every keyword | KILLED | 2 | p6 counterfeit | tag=d03adv-c-E4-M24 start=2026-10-22 20:09:34 end=2026-10-22 20:10:00 elapsed=27s bound=600s status=FAIL rc=1 |
| E5-M26 lv removed | KILLED | 4 | p6 luxury, r6b | tag=d03adv-c-E5-M26 start=2026-10-22 20:10:02 end=2026-10-22 20:10:32 elapsed=31s bound=600s status=FAIL rc=1 |
| E6-M27 lv regex without dots | KILLED | 2 | r6b | tag=d03adv-c-E6-M27 start=2026-10-22 20:10:35 end=2026-10-22 20:11:05 elapsed=30s bound=600s status=FAIL rc=1 |
| E7-M28 counterfeit V2 ungated | KILLED | 17 | p11, p5, r5d | tag=d03adv-c-E7-M28 start=2026-10-22 20:11:06 end=2026-10-22 20:11:34 elapsed=28s bound=600s status=FAIL rc=1 |
| E8-M45 luxury V2 ungated | KILLED | 16 | p11, p5 | tag=d03adv-c-E8-M45 start=2026-10-22 20:11:37 end=2026-10-22 20:12:06 elapsed=28s bound=600s status=FAIL rc=1 |
| E9-M48 validate_scrape_url deny dropped | KILLED | 2 | g11b, r11a | tag=d03adv-c-E9-M48 start=2026-10-22 20:12:08 end=2026-10-22 20:12:47 elapsed=39s bound=600s status=FAIL rc=1 |
| E10-M49 validate_scrape_url deny ungated | KILLED | 16 | p11, p13 | tag=d03adv-c-E10-M49 start=2026-10-22 20:12:49 end=2026-10-22 20:13:24 elapsed=35s bound=600s status=FAIL rc=1 |
| E11-X block-move: V2 branch above `_jsonld_str` | KILLED | 1 | p6b | tag=d03adv-c-E11-X-blockmove-v2-before-jsonld-str start=2026-10-22 20:13:26 end=2026-10-22 20:14:02 elapsed=36s bound=600s status=FAIL rc=1 |
| E12-N3 lv whole-token exclusion dropped | KILLED | 10 | r5e, r6a, r6c | tag=d03adv-c-E12-N3-lv-guard-dropped start=2026-10-22 20:14:04 end=2026-10-22 20:14:40 elapsed=36s bound=600s status=FAIL rc=1 |
| F1-M29 image deny ungated | KILLED | 16 | p11, p9 | tag=d03adv-c-F1-M29 start=2026-10-22 20:14:44 end=2026-10-22 20:15:19 elapsed=35s bound=600s status=FAIL rc=1 |
| F2-M30 image deny removed | KILLED | 8 | r7a, r7b, r7c | tag=d03adv-c-F2-M30 start=2026-10-22 20:15:20 end=2026-10-22 20:15:54 elapsed=34s bound=600s status=FAIL rc=1 |
| G1-M50 piggyback validator with the flag OFF | KILLED | 1 | p9c | tag=d03adv-c-G1-M50 start=2026-10-22 20:15:57 end=2026-10-22 20:16:28 elapsed=32s bound=600s status=FAIL rc=1 |
| G2-M51 piggyback bypasses the validator ON | KILLED | 1 | r7e | tag=d03adv-c-G2-M51 start=2026-10-22 20:16:30 end=2026-10-22 20:17:06 elapsed=36s bound=600s status=FAIL rc=1 |
| G3-N4 ON piggyback without strip | SURVIVED | 0 | - (MIN-5) | tag=d03adv-c-G3-N4-on-no-strip start=2026-10-22 20:17:09 end=2026-10-22 20:17:40 elapsed=31s bound=600s status=OK rc=0 |
| H1-M52 attribution not filtered | KILLED | 1 | r10b | tag=d03adv-c-H1-M52 start=2026-10-22 20:17:43 end=2026-10-22 20:18:19 elapsed=36s bound=600s status=FAIL rc=1 |
| H2-M54 quotes not filtered | KILLED | 1 | r10a | tag=d03adv-c-H2-M54 start=2026-10-22 20:18:21 end=2026-10-22 20:18:51 elapsed=30s bound=600s status=FAIL rc=1 |
| H3-M53 attribution deny ungated | KILLED | 8 | p12 | tag=d03adv-c-H3-M53 start=2026-10-22 20:18:54 end=2026-10-22 20:19:22 elapsed=28s bound=600s status=FAIL rc=1 |

Spec / RED-gate mutants re-applied on the GREEN bytes: 41 (M1-M3, M5-M18, M20, M21, M23, M24, M26-M30, M37-M39, M43-M54; C6 is M17 written as a block-move), all KILLED; M19, M22, M25, M35, M36, M40-M42 not re-run (the RED gate killed them on the prototype); M31-M34 belong to D03b (no url_* change); M4 equivalent by GC-2 (not re-run). Mine: N1-N4 plus the block-moves D6 and E11 (6), 3 of which survive.

## Prove-nothing rows

- No RED / PIN / G row passes vacuously: every applied mutant of a pinned rule reddens an AssertionError row, and the RED gate's base run had every R row failing on AssertionError.
- Three behaviours have NO row (the survivors): the GC-3 two-level suffix branch (MIN-1), the deny-before-dedup order of `collect_retailer_ratings` for the C12 shape (MIN-2), the ON piggyback strip (MIN-5).
- Coverage gaps by surface (no row and, for MAJ-1, a behaviour gap): the Serper-Shopping price rung (MAJ-1); a userinfo-carrying cited link on the review display (MIN-3).

## Questions for the orchestrator

1. MAJ-1: fix in D03 (one flag-first skip in `extract_price_from_shopping` / `_shopping_bh_host_evidence`, rows both W4-1 states) or rule it a stated limit with limit 5 rewritten to the measured `/bh-en/` upgrade?
2. MIN-4: keep "Salvatore" as an intended `lv` false positive, or route Ferragamo into D03d with an ON-only token?

## NOT MEASURED

- An independent flag-OFF differential against base bytes (no base worktree in this lens; identity rests on the code read + the OFF pins + GREEN's comm set).
- The 409-file comm set ON sweep (GREEN's measurement; I re-ran only the four named ON-red files).
- The engineering lens items (comm-set re-derivation, ruff, hook tests, CLAUDE.md readers) are the other adversary's.

## Files written (all in my notes folder; nothing in the unit worktree)

`<scratchpad>/D03_adv/`: `notes.md`, `mutate_adv.py`, `mutation_results_AD.json`, `mutation_results_EH.json`, `mut_EH.out`, `mut/*.log`, `mutbak_*` (byte copies), `test_zz_d03_adv_probe.py` (the probe file, copied out of the removed scratch worktree), `probe_catoff.json`, `probe_caton.json`, `probe_w41.json`, `unit_off.log`, `unit_on.log`, `probe_*.log`, `onreds_on.log`, `onreds_off.log`, this report.
