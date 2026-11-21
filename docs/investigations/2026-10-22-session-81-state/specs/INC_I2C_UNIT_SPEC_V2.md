# INC-I2c GUARD-RECALL: unit spec V2 (S98 main lane, 2026-11-21)

Unit INC-I2c GUARD-RECALL; new switch `ENABLE_IMAGE_GUARD_RECALL` (RC, default OFF). Worktree <local path> branch fix/inc-i2c-guard-recall, base aa35e9594fd783de1505076732c5b6b4e27ace4c (R-0; IR and IMG byte-identical to d0b5a761). Read with `git show HEAD:`; run from byte copies (`git archive`, 167 files equal to their blobs). IR = app/services/image_relevance.py, IMG = image_service.py, SCS = structured_comparison_service.py, SR = source_router.py, MR = merchant_registry.py. Probes: <i2c>/spec/v2measure (v00..v15; harness v2rules.py from the rule text). Prototype <i2c>/tree_v2 (v00_build.sh); diffs v2measure/v2_image_relevance.diff, v2_image_service.diff. Every probe removed ENABLE_*, set flags in-process, guarded sockets: 0 network attempts. No pytest, jest, mutants or OFF walk (R-15). roff = the phone dict (brand "", line = typed; typed only with W ON, IR:886-888); kb = brand known.

## Changes from the draft (ruling -> where)
- R-0: base aa35e959; CLAUDE.md re-cited at HEAD (:341, :711, :729, :747-752, :852; its +2 lines sit at :770-771).
- R-1: 2.2, 2.3, E4 inverted (rescued BODY MIST -> `form`, W unset), 8.
- R-2: R2 dropped (a base `name` stands): 2.2, E3, L2.
- R-3: R1 / R3 as drafted, empty brand, S ON, base `fragrance_word` only: 2.2.
- R-4: 2.2, 2.4 (each word; tola OUT by the ruling's rule), E11, M10-M15, L9.
- R-5: reads `source_router.SOURCE_REGISTRY`, DEVIATION D-1 (the named fallback): 1.6, P6, walk 11, L8; C9 in 1.6.
- R-6 design B: 2.6. R-7 RECALL_SET text, NAME= prefix: 2.6, E9. R-8 carried: 8, 10. R-9 floor: 2.2, L3. R-10 function-level import: P5.
- R-11: 0, 1.5.
- R-12: 1.4 (RC-2, RC-3), 1.2 (493, C11), walk 14, 2.5 (RC-9, RC-10), 8 (C9, C12, C13), 1.5 (C10).
- R-13: 5 (draft E10 / E11 -> P7 / P8; E5 spellings; E6d; P9; E8 / E9 presence first; E11; E13); OFF walk at the box.
- R-14: 7. R-15: header, 7. R-16: 11. Added: RECALL_SET hashes `_host` and all of `_RecallCall`.

## 0. Verdict
- 1,675 of 6,800 right typed pairs are refused (name 859, fragrance_word 816). V2 rescues only `fragrance_word` refusals, by R1 (vocabulary) and R3 (perfume-shop host, two-word floor); a rescue naming a home-scent good is refused `form` (R-4); every rescue takes the words test (R-1). check(), every GUARD_SET member, PICK_GUARD_RULES 7f9e0f4f and every OFF name unchanged.
- KB-title shape (roff; W OFF = W ON, measured): right refused 1,675 -> 1,273 (+402: BOTTLES +364 = Latin 326 + Arabic 38; non-perfume self rows +38), 0 right newly refused. Wrong added: cross +2, wrong-form self +34, NP-X +2 of 1,588, XB 0 of 10,542, SB 0 of 11,034, unsure 0; ambiguous line-only +50 of 3,759; kb 0 (v05).
- Live tiers (a MODEL, v07, title + site name): bottles +687 / +572 / +428 / 0 (site-name models M1..M4), non-perfume +75 / +75 / +73 / 0; costs wrong-form +69 / +69 / +67 / 0, cross +18 / +8 / +6 / 0, NP-X +4 / +4 / +4 / 0. Live bottle gain 0..687; the flip-window counts decide.
- Prototype = harness on every case (accept and _organic_reason, roff and kb, both W: 0 mismatches).

## 1. The defect, measured (aa35e959, G S ON; v15)
### 1.1 Base
- roff right 6,800: refused 1,675 (name 859, fw 816); Latin 6,613: name 859, fw 641; Arabic 187: fw 175, 12 accepted; W ON the same. kb right 6,613: brand 1,097, fw 24. Wrong accepted roff W OFF [ON]: cross 792 [417] of 1,077; wrong-form self 738 [200] of 1,086.
- By shop (refused / right) as the draft (e.g. taifalemarat 292/292, jashanmal 467/3,699; no host 16; v15). Bare: name 660 (608 self); line_only: fw 520.

### 1.2 Classes (the guard's tokenizer)
- name 859: typed brand words absent 846, years 9, short line 3, other 1; the host label covers the 846 as a token 178, a joined run 175, none 493 (RC-4). V2 rescues none (R-2); the years class (C11) is rightly untouched.
- fw Latin 641: no signal 432, non-proof word 125 (musk, oud, spray, intense, scent, elixir, attar, mist), size only 45, edc 39. Arabic 175: an R1 transliteration 38, none 137.
- `_cg.normalize` (category_gate.py:144-199) as the draft says (x03 on the R-4 words: U+0629 -> U+0647, a leading article stripped).

### 1.3 Which tiers feed check()
- Callers: IR:949 accept, IR:965 _organic_reason, IR:993 accept_pick; none in app/ outside IR. accept: Tier 1.5b (IMG:263-298), Tier 1 (IMG:301-315), Phase 1 (IMG:364-366) and late (IMG:630-643, 676, 693-694); _organic_reason: llm_pick (IMG:443, 451-452; 706, 714-715); accept_thumb: tier B (IMG:855-877), CLOSED.
- Never reach check(): piggyback (IMG:373-374; SCS:6592), the page-image override (SCS:6752-6786, SCS:1508), the KB card (SCS:6382, 6590), tier A (IMG:814).

### 1.4 The production identity shape (RC-2, RC-3)
- Home sends `{product_a, product_b}` (HomeScreen.tsx:458-459) via streamComparison (api.ts:679); ENABLE_EXPO_FETCH_SSE ships false (features.ts:52; api.ts:787): ONE GET /api/v1/text/compare (api.ts:716, 738-742; text_routes.py:964, pair :1001-1003); flag true: GET /compare/stream (api.ts:899; text_routes.py:1177, :1216-1218). Both -> brand "", name = the typed half (SCS:4609-4617; R OFF no rewrite, SCS:4622). POST /compare (text_routes.py:738) has no app caller.
- q= callers take the kb shape EXCEPT a query split on " vs " under ENABLE_PARSE_PRESPLIT or the ENABLE_PARSE_BUDGET fallback (SCS:4198-4220 via `_explicit_pair_products` SCS:2074-2086; CLAUDE.md:852): brand "", second look applies (v13: base fw, V2 accepted).
- brand / name reach `relevance_kwargs` (SCS:6252-6253, 6385, 6602, 6801); resolved pairs carry a brand (CLAUDE.md:711).

### 1.5 Reach
- KB titles meet check() verbatim only on tier B. The v07 model appends a site name (M1 merchant_labels.json else the label; M2 + two captured PDP names; M3 + split names; M4 "... Perfumes"); base refuses 1,618 / 1,461 / 1,310 / 427 right pairs with a host.
- C10: ENABLE_KB_FIRST_SERVE is OFF in production (relay state file 2026-11-17, R-12); ON, a KB card image (https, valid, allowed; kb_serve.py:320-326) is served before any guard, so the second look reaches only products without one.
- The one production reading predates S and L. `reason=` is the last rejection's (IR:1014-1020).

### 1.6 The registry read (R-5, C9)
- No SR function reads rows without possibly scheduling a refresh: `registry_rows` / `registry_lookup_rows` (SR:625-644) call MR `_serve` (MR:235-248), which with ENABLE_MERCHANT_REGISTRY_DB ON and a stale memo runs `_schedule_refresh` (MR:206-232, a kb_merchants read task); `_lookup_registry`, `_routable_registry`, `_registry_row_for_host` (SR:667-677, 726) sit on them. The I/O-free read is the global `SOURCE_REGISTRY` (SR:611, built at import, SR:552-605), what `registry_lookup_rows` returns with the DB flag OFF. v08 (running loop, DB ON, memo empty): V2 0 tasks / 0 refreshes / 0 opens; draft prototype 1 / 1.
- C9: IR is NOT a fourth direct reader of `registry_lookup_rows`: SR's "three direct readers" (SR:641-643) stays true, r21 (tests/test_s81_s15_registry_robots.py:1348-1362) green unedited; IR is the second SOURCE_REGISTRY reader outside SR (SCS:3055-3064).
- v11: catalog ON 319 rows, 68 fragrance-only hosts (56 labels), 9 of 11 evidence shops (not jashanmal, goldencollections: multi-category); OFF 44 rows, 5 hosts, no evidence shop. fragrantica.com is fragrance-only and denied first.

## 2. The contract
### 2.1 The switch
`RECALL_FLAG_ENV = "ENABLE_IMAGE_GUARD_RECALL"`, `recall_enabled()` the house idiom (IR:343-360). Read once per RelevanceCall construction (in `__new__`, after `guard_enabled()`) and once per `pick_cache_name` (only under G, IMG:630-631); the late path reads it twice (RC-10). OFF = unset, "false" or any non-truthy value.

### 2.2 The rules (exact; v2_image_relevance.diff)
The second look runs only when ALL hold: class `_RecallCall`; base reason `fragrance_word` (RECALL_REASONS = ("fragrance_word",)); `ident.brand_empty`; `short_line_enabled()`. Every other reason (name, brand, denied, scheme, form, concentration) stands.
- R1 rescues when `RECALL_FRAGRANCE_WORDS & (_candidate_keys(texts) | _text_tokens(fragrance_texts))`; RECALL_FRAGRANCE_WORDS = `_fold("edc", ...)` + eight code-point words: U+0628 0627 0631 0641 0627 0646; U+062A 0648 0627 0644 064A 062A; U+0628 064A 0631 0641 064A 0648 0645; U+0628 0631 0641 064A 0648 0645; U+0628 0627 0631 0641 064A 0648 0645; U+0628 0627 0631 0641 0648 0645; U+0643 0648 0644 0648 0646; U+0643 0648 0644 0648 0646 064A 0627.
- R3 rescues when `len(ident.line_sig) >= RECALL_SHOP_MIN_WORDS` (2) and `_perfume_shop(hosts)`: a candidate `_host(h)` with `h == d or h.endswith("." + d)` for d in `_perfume_domains()` = `_host` of every `source_router.SOURCE_REGISTRY` row with `tuple(categories or ()) == RECALL_SHOP_CATEGORIES` ("fragrances",); source_router imported inside the function; total (`_seq(None)` -> no rows, a raise -> frozenset()); read once per call.
- R-4 (rescues only): `_home_reason` = `form` when the FIRST text, `fold_numero(_cg.normalize(t[:512]))`, holds a RECALL_HOME_WORDS token, a token matching RECALL_WEIGHT `[0-9]+(?:grams|gram|gms|gm|gr|g)`, an adjacent RECALL_HOME_JOINS pair, or a number then a RECALL_GRAM_UNITS token (g, gm, gms, gr, gram, grams); exempt = `ident.query_words | ident.brand_forms` (IR:819): an exempt token never counts, a pair counts unless both are exempt.
- R-1: then `_words_reason(ident, texts)` whatever W reads (I-12, IR:1003-1012).

### 2.3 Order
`_RecallCall.accept`: base `accept` (n += 1, deny, https, check, record); False with `last_reason` in RECALL_REASONS -> `_record(tier, _second_look(...))` (n once; a refusal records its own reason). `_organic_reason`: base (deny first), then the second look on (title,), (link,). `_second_look` = `_recall_reason`, `_home_reason`, `_words_reason`. organic_passes / accept_pick use the override (no-related branch IR:992-993 unchanged); accept_thumb: the override, then its words test.

### 2.4 R-4 words and each word's effect (v01 / v05; roff, W OFF = ON; refused alone inside V2)
| word (spellings) | wrong refused (wrong-form / NP-X) | right bottles | right non-perfume | ambiguous | kept |
|---|---|---|---|---|---|
| grams (`36g`, `12grams`, `500gr`; `12 Grams`, `20 gm`) | 41 (35 / 6) | 0 | 15 | 8 | yes |
| room spray | 0 | 0 | 5 | 0 | yes |
| linen spray | 8 (8 / 0) | 0 | 0 | 0 | yes |
| air freshener | 1 (1 / 0) | 0 | 0 | 0 | yes |
| chips | 1 (0 / 1) | 0 | 0 | 1 | yes |
| bakhoor, bakhour, bukhoor, bukhour, bakhur, bukhur; incense; burner(s); charcoal | 0 | 0 | 0 | 0 | yes (no effect in the sets) |
| Arabic U+0628 062E 0648 0631; U+0645 0628 062E 0631 (and + U+0629); U+0641 062D 0645; U+062F 062E 0648 0646; U+0645 0639 0645 0648 0644; pair U+0645 0639 0637 0631 + U+062C 0648 | 0 | 0 | 0 | 0 | yes (no effect in the sets) |
| tola (`tola`, `tolas`, `1tola`) | 14 (10 / 4) | 1 ("Sheikh Abdullah - (1tola)", the oil of a line also sold as 60 ml) | 0 | 3 | NO |
- R-4 removes wrong-form 44, NP-X 7, ambiguous 9, 20 non-perfume self rows, 0 bottles (V2 without it: right 422, wrong-form 78, NP-X 9, ambiguous 59). R-1 at W OFF removes wrong-form 32, NP-X 21, ambiguous 15, 0 right (without it: 66 / 23 / 65).
- Per rule: R1 alone +77 right (Latin 39, Arabic 38), cross +2, ambiguous +29; R3 alone +360 (bottles 322), wrong-form +34, ambiguous +26, NP-X +2; no floor +517 (+115 bottles), ambiguous 246, NP-X 12. R-4 only restores base refusals: lost 0 in every set (P10).

### 2.5 Reasons, lines, OFF
REASONS (IR:191-200), TIERS and line grammars unchanged; a refused rescue logs `form` / `concentration`. OFF: the base verdicts, lines and names (RC-9: `__new__` adds a G read, and under G an RC read, per construction; no recorder counts them: they count IMAGE_LATE* / IMAGE_PICK* (tests/test_inc_i2a_picture_not_cut.py:1729-1734), W_FLAG, A_FLAG). Measured: RelevanceCall for RC unset / "false" / "0" / "garbage" / "" and G unset; 48 base members byte-identical (v09); check() reads RC 0 times. OFF walk at the box (R-13).

### 2.6 Versions and cache (design B)
- v04: GUARD_SET digest (tests/test_inc_i2a_picture_not_cut.py:1387-1452) 7f9e0f4f = PICK_GUARD_RULES; get_product_image_url sha 3f3b8ad5... (I2a P3, :1781-1789) and _late 17b90f4f... (I2b P2, :1481) unchanged; v10: pick_cache_name equals base in 30 of 40 mixes (S x W x 10 RC spellings), differs only with S ON and RC truthy, no ON name equals an OFF name.
- NEW `IMG.PICK_RECALL_RULES` = `sha256(text.encode("utf-8")).hexdigest()[:8]`, text = `"\n".join(parts)` in this order: `inspect.getsource` of recall_enabled, RelevanceCall.__new__, _host, _perfume_domains, _perfume_shop, _recall_reason, _home_reason, _RecallCall (the whole class); `NAME + "=" + repr(sorted(getattr(ir, NAME)))` for RECALL_FRAGRANCE_WORDS, RECALL_HOME_WORDS, RECALL_HOME_JOINS, RECALL_GRAM_UNITS; `"RECALL_WEIGHT=" + ir.RECALL_WEIGHT.pattern`; `NAME + "=" + repr(getattr(ir, NAME))` for RECALL_SHOP_CATEGORIES, RECALL_SHOP_MIN_WORDS, RECALL_REASONS, RECALL_FLAG_ENV. Prototype (black 26.5.1): 3d138a86 (175 lines); without the NAME= prefix on the four repr lines 895a0c56. GREEN recomputes.
- Axis (IMG:556-558) gains `+ ("r" + PICK_RECALL_RULES if _relevance.recall_enabled() and _relevance.short_line_enabled() else "")`. R-7: meets R-13 for code and tables; the registry is L6.
- Cost: merge 0 cache rounds; flip 1 round (one Serper Images credit per product, llm_pick where Serper misses). C12: RC ON widens the llm_pick precondition (IR:967-973; IMG:443, 706): more paid tier-3 calls in steady state (E6e: 1 GPT call vs 0). Diff: IR +231 / -1, IMG +12 / -2.

## 3. Change list (GREEN order)
1. IR (leaf shape kept; black-clean, .github/black-clean-paths.txt:69): (a) an INC-I2c docstring paragraph after IR:37-42; the leaf sentence (IR:44-48) names source_router; (b) after SHOPPING_TIER (IR:337) the nine RECALL_* names of 2.1, 2.2 and 2.4 (joins via `_phrase`, IR:296-297); (c) `recall_enabled()` after IR:358-360; (d) `RelevanceCall.__new__(cls, product_name=None, relevance=None)` before `__init__` (IR:900): `if cls is RelevanceCall and guard_enabled() and recall_enabled(): cls = _RecallCall`; `return super().__new__(cls)`; (e) after summary (IR:1014-1020): `_perfume_domains`, `_perfume_shop`, `_recall_reason`, `_home_reason`, `class _RecallCall(RelevanceCall)` (`_second_look`, `accept`, `_organic_reason`). No GUARD_SET member or table edited.
2. IMG: PICK_RECALL_RULES after PICK_CACHE_PREFIX (IMG:490); axis and docstring of pick_cache_name (IMG:549-560).
3. CLAUDE.md: `### INCIDENT LANE unit (INC-I2c GUARD-RECALL, S98 main lane)` after the INC-I2b block (:747-752) with the section 8 row and Rule.
4. NEW tests/test_inc_i2c_guard_recall.py; added to .github/black-clean-paths.txt.
No edit: SR, MR, SCS, price_service, product_resolver, data/*, category_gate, deny_hosts, client, migrations.

## 4. Flag-mix walk
| # | Mix | Behaviour | Proof |
|---|---|---|---|
| 1 | G OFF | no RelevanceCall; RC never read | P4 |
| 2 | G S ON, RC OFF, any W A B R L | base verdicts, lines, names | P1 P2, OFF walk |
| 3 | G S ON, RC ON, R W OFF, L ON | second look Phase 1 and late; ON names | E1-E8 E11 |
| 4 | RC ON, S OFF | subclass inert; names unchanged | P8 E8 |
| 5 | RC ON, W any | every rescue takes home + words tests | E4 E11 |
| 6 | RC ON, R ON | resolved (brand) untouched; unresolved typed pair gets it | P7 E2 |
| 7 | RC ON, A ON | A = words_reason_for only (IMG:814) | stated |
| 8 | RC ON, B ON | thumb: override, then its words test | E7 |
| 9 | KB card, piggyback, page override, camera | never reach check() | 1.3 |
| 10 | catalog flag OFF | 5 literal hosts: R3 nearly inert, R1 works | v11 |
| 11 | ENABLE_MERCHANT_REGISTRY_DB ON | still SOURCE_REGISTRY: no task, no I/O | P6 v08 |
| 12 | ENABLE_DATA_GUARDS_V2 any | the deny precedes check() | P9 |
| 13 | q= through the LLM parse | brand known: untouched | P7 |
| 14 | q= under ENABLE_PARSE_PRESPLIT / the ENABLE_PARSE_BUDGET fallback | brand "": second look applies | E13 v13 |
| 15 | RC flips mid-process | read per construction and per name | L13 |

## 5. RED rows (tests/test_inc_i2c_guard_recall.py)
Fixtures (concatenated, no real shop host): SHOP = "shop." + "nimbus" + ".test"; SUBROW = "bh." + "cedar" + ".test"; PARENT = "cedar" + ".test"; MULTI = "multi" + "store" + ".test"; VAN = "vanilla" + ".test"; BLOG = "blog" + ".test"; BAN = "Fragr" + "antica" (a banned site name, the pattern of tests/test_inc_i1_picture_must_match.py:90); IMG = "https://cdn." + "example" + ".test/a.jpg"; U(p) = "https://" + SHOP + p. Registry: `monkeypatch.setattr(source_router, "SOURCE_REGISTRY", ROWS)`, SimpleNamespace rows (SHOP, ("fragrances",)), (SUBROW, ("fragrances",)), (VAN, ("fragrances",)), (MULTI, ("fragrances", "makeup")). Flags by monkeypatch: G, S, RC "true", W unset unless stated. rel(q) = {"brand": "", "line": q, "category": "fragrances", "slot": 0} (+ "typed": q with W "true"). v(q, title, host): c = RelevanceCall(q, rel(q)); c.accept("serper_images", IMG, texts=(title,), hosts=("https://" + host + "/p/1",)) -> None if True else c.last_reason. Arabic by chr(). New symbols via `getattr(mod, name, None)` asserted not None before use; presence asserts come first, so each E row fails at base on an AssertionError only. "Base" = measured on the base tree (v12).
| # | Inputs / flags -> expected | Base |
|---|---|---|
| E1 | v("Nimbus Velvet", "Nimbus Velvet for Women, edC 100ml", BLOG) -> None (RC unset -> "fragrance_word"); v("Nimbus Velvet", "NIMBUS VELVET " + w, BLOG) -> None for each 2.2 word; title "NIMBUS VELVET" -> "fragrance_word" | fw |
| E2 | v("Velvet Rain", "VELVET RAIN", SHOP) and host "bh." + SHOP -> None; MULTI, BLOG, PARENT -> "fragrance_word"; v("Velvet", "VELVET", SHOP) -> "fragrance_word" (floor) | fw |
| E3 | assert type(RelevanceCall("Vanilla Musk", rel(...))).__name__ == "_RecallCall" first; v("Vanilla Musk", "WHITE MUSK", VAN) -> "name"; v("Nimbus Velvet Rain", "VELVET RAIN", SHOP) -> "name"; W unset and "true" | class RelevanceCall |
| E4 | v("Velvet Rain", "VELVET RAIN BODY MIST", SHOP) -> "form", W unset and "true"; v("Velvet Rain Body Mist", same, SHOP) -> None; v("Velvet Rain", "VELVET RAIN INTENSE", SHOP) -> "concentration" | fw |
| E5 | G "true": RC "true", "1", "yes", "on", " TRUE " -> "_RecallCall"; unset, "false", "0", "garbage", "" -> "RelevanceCall"; G unset + RC "true" -> "RelevanceCall" | RelevanceCall |
| E6 | get_product_image_url("Velvet Rain", relevance=rel("Velvet Rain"), ...), the I2b tier fakes (search_images; credit True; GPT -> U("/pick.jpg")), caplog INFO on app.services.image_service: (a) images [{"imageUrl": U("/a.jpg"), "title": "VELVET RAIN", "source": "Nimbus Shop", "link": U("/p/1"), "domain": SHOP}] -> U("/a.jpg"), "[IMG_RELEVANCE] product=0 tier=serper_images outcome=accepted candidates=1 reason=none" (RC unset: None, "outcome=rejected candidates=1 reason=fragrance_word"); (b) search_payload {"organic": [{"title": "VELVET RAIN", "link": U("/p/1"), "imageUrl": U("/o.jpg")}]} -> U("/o.jpg"), "[IMG_RELEVANCE] product=0 tier=search_payload outcome=accepted candidates=1 reason=none"; (d) {"knowledgeGraph": {"title": "Velvet Rain", "type": "EDC", "imageUrl": U("/k.jpg")}} -> U("/k.jpg"), the (b) line; (e) organic_results [{"title": "VELVET RAIN", "link": U("/p/1")}] -> U("/pick.jpg"), 1 GPT call, "tier=llm_pick outcome=accepted candidates=1 reason=none" (RC unset: 0 calls, "tier=none outcome=none candidates=0 reason=none") | None |
| E7 | shopping_thumbnail([{"thumbnail": U("/t.jpg"), "title": T, "source": "Nimbus Shop", "link": U("/p/1")}], "Velvet Rain", 0, rel("Velvet Rain")), W unset: T "VELVET RAIN" -> U("/t.jpg"), "IMG_SHOP thumb product=0 outcome=accepted candidates=1 reason=none"; T "VELVET RAIN GIFT SET" -> None, "... reason=form" | None, fw |
| E8 | rules = getattr(img, "PICK_RECALL_RULES", None) matches [0-9a-f]{8} first; `_expected_name` (tests/test_inc_i2b_guard_words_shop_image.py:921-933), rel("Velvet Rain"), variant None: RC ON -> axis "s1w0r" + rules; RC unset -> "s1w0"; S unset + RC ON -> "s0w0"; W "true", typed "Velvet Rain EDP" -> "s1w1:EDPr" + rules; get_product_image_url_late (E6a images, done payload future, cache fakes) reads and stores exactly the ON name | rules None |
| E9 | every RECALL_SET member and table present first; the 2.6 digest == PICK_RECALL_RULES != "00000000" | missing |
| E10 | E1's first case first; SOURCE_REGISTRY = a list subclass whose `__iter__` raises -> E1 None, E2 first "fragrance_word", no raise; = None -> E2 fw; = [SN(domain=None, categories=None), SN(domain=SHOP, categories=None), SN(categories=("fragrances",)), SN(domain=SHOP, categories=("fragrances",))] -> E2 None | fw |
| E11 | on SHOP: v("Velvet Rain", "VELVET RAIN " + w.upper()) -> "form" for each of the 17 kept single words of 2.4 (parametrized; W unset and "true"; RC unset fw); suffixes "ROOM SPRAY", "LINEN SPRAY", "AIR FRESHENER", the Arabic pair -> "form"; "(36g)", "12 GRAMS", "500GR", "20 gm", "3 g", "100 Gram", "40gms" -> "form"; typed: v("Velvet Rain Incense", "VELVET RAIN INCENSE") None, v("Velvet Rain Room Spray", "VELVET RAIN ROOM SPRAY") None, v("Velvet Rain Room", same) "form", v("Velvet Rain 36g", "VELVET RAIN (36g)") None, v("Velvet Rain 12", "VELVET RAIN 12 GRAMS") "form"; suffixes "(1 TOLA)", "ROOM", "LINEN", "WOOD", "100ML" -> None; texts ("VELVET RAIN", "Incense House") -> None | fw |
| E12 | 24 synthetic rows (one per class of E1-E4, E10, E11, a kb control): RC ON reasons, W unset and "true" equal | differ |
| E13 | p = scs._explicit_pair_products(scs._split_on_vs("Velvet Rain vs Cedar Moss"))[0] has brand ""; kw = relevance_kwargs(p["brand"], p["name"], "fragrances", 0, False); RelevanceCall(p["name"], kw["relevance"]) accepts "VELVET RAIN" on SHOP | False |
| P1 | RC unset == "false" == "0" == "garbage": E12 reasons; E6-E8 URLs, summaries, IMG_TIER / IMG_RELEVANCE / IMG_SHOP / IMG_LATE lines | green |
| P2 | GUARD_SET digest == PICK_GUARD_RULES == "7f9e0f4f"; PICK_CACHE_PREFIX "imgpick:v1:7f9e0f4f:" | green |
| P3 | check() over E12 reads RECALL_FLAG_ENV 0 times (getenv recorder) | green |
| P4 | G unset: cascade, late call, shopping_thumbnail read it 0 times; relevance_kwargs == {} | green |
| P5 | AST: source_router imported only inside _perfume_domains; IR text has no "registry_lookup_rows", "kb_merchants", "robots_registry" | green |
| P6 | ENABLE_MERCHANT_REGISTRY_DB "true", merchant_registry._reset_for_tests(), refresh_merchant_registry a counting stub, source_router.registry_lookup_rows a recorder; on a running loop E2 first: 0 new tasks, 0 stub runs, 0 recorder calls | green |
| P7 | brand "Nimbus", line "Nimbus Velvet Rain": titles "NIMBUS VELVET RAIN", "VELVET RAIN", "ACME VELVET RAIN", "NIMBUS CEDAR", "VELVET RAIN BODY MIST" x SHOP, BLOG: RC ON == unset | green |
| P8 | S unset + RC ON: E1 first, E2 first, E4 first, E11 "INCENSE" == RC unset (fw) | green |
| P9 | RC ON, deny on a SHOP candidate (a deny-skipping mutant would rescue it; v16): a Serper item with source BAN -> URL None, "reason=denied"; organic_results [{"title": "VELVET RAIN " + BAN, "link": U("/p/1")}] -> 0 GPT calls (without the word: `_organic_reason` None); KG without host -> "tier=search_payload outcome=rejected candidates=1 reason=fragrance_word" | green |
| P10 | v("Velvet Rain", "VELVET RAIN INCENSE EAU DE PARFUM", SHOP) -> None, RC unset and ON | green |

## 6. Mutants (KILLED by)
M1 brand_empty dropped (P7). M2 S dropped (P8). M3 floor dropped, M4 floor 3 (E2). M5 categories containing fragrances (E2 MULTI). M6 registry ignored (E2 BLOG). M7 subdomain proves parent (E2 PARENT). M8 a `name` rescue (E3). M9 rescue skips words with W unset (E4). M10 home test dropped (E11). M11 a home word dropped (E11). M12 typed exemption dropped (E11). M13 pair exemption one-sided or both-typed counted (E11 room spray). M14 tola added (E11 "(1 TOLA)"). M15 home test on every text (E11 second text). M16 second look on denied / scheme (P9). M17 `_organic_reason` not overridden (E6e). M18 n counted twice (E6a). M19 bool(getenv) or `== "true"` (E5). M20 `__new__` ignores G (E5, P4). M21 axis without S (E8). M22 axis part always (E8, P1). M23 PICK_RECALL_RULES not bumped (E9). M24 dispatch in check() (P2, P3). M25 an R1 word dropped (E1). M26 registry raise propagates (E10). M27 R1 gated by the shop (E1 BLOG). M28 R1 ignores fragrance_texts (E6d). M29 registry_lookup_rows read (P6). M30 kb rule changed (P7).

## 7. Class, gates, comm set
- FOCUS, TWO adversaries after GREEN (R-14): (1) RECALL AND PRECISION: corpus beyond the rows (XB, SB, NP-X, I2b; v2measure), Arabic, home scent, clones, the floor, displacement; (2) PRODUCTION AND IDENTITY: the OFF walk on every tier (RED on base, GREEN on head, R-13), `__new__`, the axis and both pins, leaf shape and no I/O under every registry flag, the walk, the llm_pick cost.
- Gates only after the relay's "box is yours" (R-15): RED as section 5; GREEN: the RED file green, the comm set no new failure against an LC-6 base record, black / ruff (CI tier clean on the prototype), pyt.py only, the fourteen client jest fences by path.
- Stay-green: the draft's list plus tests/test_s81_s15_registry_robots.py (R-5).
- Comm set (v2measure/comm_set_aa35e959.txt): 205 = the draft's 204 + tests/test_inc_t1c_refusal_visible.py (new; scans app/ for note_if_guard_refusal, :503-520; IR adds none); every path exists at aa35e959.

## 8. CLAUDE.md row, window, proof
Row: "`ENABLE_IMAGE_GUARD_RECALL` (INC-I2c GUARD-RECALL, `app/services/image_relevance.py::recall_enabled`, the house idiom, read once per RelevanceCall construction in `RelevanceCall.__new__` and once per `image_service.pick_cache_name`, only with `ENABLE_IMAGE_RELEVANCE_GUARD` ON). ON with `ENABLE_IMAGE_GUARD_SHORT_LINE` ON, a typed-pair (empty-brand) candidate refused with `fragrance_word` gets a second look: it passes on edc or an Arabic spelling of perfume, parfum, toilette or cologne in its text or knowledge-graph type, or, when the typed text has two significant words or more, on a candidate host that is a perfume shop of the code registry (`source_router.SOURCE_REGISTRY` rows whose categories are exactly fragrances, read inside the function: no refresh, no I/O). A rescued candidate is refused `form` when its title names a home-scent good (bakhoor and its spellings, incense, burners, charcoal, chips, a gram weight, room or linen spray, air freshener, six Arabic words; a typed word never counts), then takes the words test whatever `ENABLE_IMAGE_GUARD_WORDS` reads. Every other reason stands. OFF (unset, false or any other value): the base verdicts, lines and names; `check`, every base method, `PICK_GUARD_RULES` and every OFF pick-cache name unchanged. ON with S ON the axis gains `r` + `PICK_RECALL_RULES`: each product's first late compare after the flip pays one Serper Images credit, and more llm_pick calls pass their precondition. Brand-known identities, the KB card image, the piggyback, the page-image override, tier A and camera products are untouched." Rule (twin of CLAUDE.md:729, C9): "a unit that edits the RECALL_SET bumps `PICK_RECALL_RULES` (the I2c E9 fails until it does)."
- Owner steps: none to merge; the orchestrator sets RC=true on web in its own window (S ON). Rollback: unset.
- Window (plain words), 24 h before / after: `IMG_RELEVANCE` with `outcome=accepted`; `reason=fragrance_word`, `reason=name`, `reason=form`; `tier=llm_pick` (C12); `IMG_LATE cache outcome=miss` rises once.
- Phone proof (C13; merged NOT proven until seen): with RC OFF, record for two typed pairs at registry perfume shops, after a cache miss, `IMG_RELEVANCE ... outcome=rejected reason=fragrance_word`; flip; see both pictures; a one-word line alone unchanged.
- Gate line: L22 and the GUARD_SET gap carried to the next PICK_GUARD_RULES unit, at the latest before the W window (R-8, the relay may overrule); the R-16 questions.

## 9. Stated limits
- L1 The live effect is modelled (bottles 0..687), not measured.
- L2 A typed word the title lacks stays `name` (R-2): the 859 name refusals remain in the KB-title shape; live, the site name carries the house.
- L3 The floor keeps one-word lines on the fragrance-word rule (115 bottles; without it ambiguous 50 -> 246, NP-X 2 -> 12).
- L4 Flankers adding words to a bare or edc title pass (cross +2; I2b L1).
- L5 Own-name non-bottle listings typed with their form word pass, by the typed exemption (wrong-form self +34: 13 dehn oud oils, 16 All Over Spray, 5 other; non-perfume +38, one a bottle RC-6 calls home).
- L6 The registry is data read at import: a row change moves verdicts without a version bump; a pick accepted on a catalog host outlives the catalog flag up to the 7-day TTL.
- L7 fragrantica is fragrance-only; the deny runs first.
- L8 (R-5) With ENABLE_MERCHANT_REGISTRY_DB ON a host only in kb_merchants is no perfume shop, a blocked row still is. A bare process reads data/bh_gcc_sources.json once at the first call (v08 cold: 1 open, 0 tasks); the server imports SR at startup (SCS:1729).
- L9 tola OUT: oud wood sold by tola without grams passes (NP-X +2, wrong-form +1); agarwood sticks and diffusers outside FORM_WORDS are not covered. bakhoor, dukhoon, incense also name bottles in the export (a "No 9 Bukhoor" EDP, two Arabic titles, "Supremacy Incense"); R-4 spares them by acting on rescues only and exempting typed words.
- L10 A typed Arabic transliteration stays a significant line word. L11 With S rolled back the switch is inert. L12 kb untouched.
- L13 A flip between the two reads of one late call (tests only) could store an ON pick under an OFF name.
- L14 The GUARD_SET coverage gap (`_host`, `_line_keys`, `_line_tokens`, `alias_groups`, `dict_items`, `_related`, `_denied`) stays (carried, R-8); RECALL_SET hashes `_host`.
- L15 Cost: `_perfume_domains` 79 us per call (no memo); a rescued accept 148 us vs a base refusal 24 us (v14).
- L16 XB / SB / NP-X truths are construction rules (cross_brand/RULES.txt, rv04). "edc" also names non-perfume goods (R1 alone: ambiguous +29). Displacement (P-1) and clones (P-4) unmeasured.

## 10. Out of scope
- R2 (R-2); R4-R8 and the lexicon R1 as in the draft section 10 (measured at d0b5a761, not re-run). L22 and the GUARD_SET gap (R-8). Shopify stamp, tier B policy, the resolver, INC-M1b, client, app.json, migrations.

## 11. Questions for the relay (non-blocking, R-16)
- Q1 Production states of ENABLE_MERCHANT_REGISTRY_DB, ENABLE_PARSE_PRESPLIT, ENABLE_PARSE_BUDGET, ENABLE_BH_GCC_CATALOG_SOURCES (CLAUDE.md:341: ON since 2026-06-26).
- Q2 A read-only count of IMG_RELEVANCE lines by outcome and reason since the L flip (2026-11-17 02:36).
- Q3 tola: out by the R-4 rule (it refuses a right 1-tola oil); overrule only if oils sold by tola are judged rare.

## Deviations from the rulings
- D-1 (R-5): no SR function reads rows without possibly scheduling a refresh (1.6); the named fallback applied: R3 restricted to the I/O-free code registry `source_router.SOURCE_REGISTRY`; with ENABLE_MERCHANT_REGISTRY_DB ON the kb_merchants rows are not read (L8). SR not edited.
