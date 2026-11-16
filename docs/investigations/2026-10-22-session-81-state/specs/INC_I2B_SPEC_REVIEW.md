# INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER: spec adversary review (S96, 2026-11-17)

Base 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9, read with git show / git grep only. Spec: s96/i2b/spec/INC_I2B_UNIT_SPEC.md. Probe: s96/i2b/spec/rev/probe_adv.py (the spec's own prototype words.py / loader.py on the read-only src copies), output rev/probe_adv_result.txt.

VERDICT: AMEND (0 BLOCKING, 4 MAJOR, 7 MINOR).

## Verified (no finding)
- Every file:line in section 1 checks out: IR check 496-521, _check_short_line 524-563, identity 461-493, Identity 346-360, first_https_raster 573-589, relevance_kwargs G read 597; IMG _ORGANIC_IMAGE_KEYS 92, _first_image 246-259, RelevanceCall 365 / 640, comment 484-487, PICK_GUARD_RULES 488, axis 555; SCS 1287-1294, 1392, 1460-1479, 6125-6153, 6299-6300, 6503-6504, 6662-6696, anchor 6698, 6708, 6735-6739, 7039-7050, 8194; PS 15577, 15748-15771; WOO 148, 270-279 (280 is the in_stock if); noon 469-476; product_resolver 77-90, 1325; kb_ingest 183-187, 456-457; jsonld_widen 79; test_inc_i1 REL_LINE 66-71; test_inc_i2a GUARD_SET 1387-1396.
- R ON identity reaches the guard: apply_resolution writes name / variant before _fetch_product_data (SCS:4559 hook, fetch 4679-4680); full_name = dedup_brand_name(brand, name+variant) (SCS:1392; the brand is always prefixed), so query_conc carries the resolved label.
- First text = title at every guarded site (IMG:276, 286, 293, 310; IR:681-684); accept_pick with no related item calls check with () (IR:712).
- E1 / E2 reproduce from corpus_result_v2.json (S1 65->7, S0 59->7, no-conc 10->1, 0 right newly refused ON THE CORPUS).
- No consumer of REASONS in app/ or scripts/; only REL_LINE pins it. No flag-name collision. Axis covers W; A and B rightly off it.
- The inline override and _late_page_image_choice agree on a stamped image (SCS:6670-6696 vs 1467-1479). gstatic is not on DENY_HOSTS (deny_hosts.py:54-81); accept tests no raster (IR:646-668), so a /shopping?q=tbn thumb is not refused.
- The Shopify catalog is cached whole (PS:15426): product["images"] survives a cache hit.

## Findings
### F1 MAJOR: rule 2(a) refuses every right picture of a line whose concentration IS "EDT / EDP Intense"
Where: 2.1 rule 2(a), E3, M5. Evidence (probe): bare "Jean Paul Gaultier Ultra Male" (R OFF) vs "... Ultra Male Eau de Toilette Intense 125ml" -> concentration; the same with "EDT 125ml" typed; "Le Male Le Parfum" vs "... Eau de Parfum Intense" -> concentration; "Scandal Pour Homme Le Parfum" vs "... Eau de Toilette Intense" -> concentration; marketing "Long Lasting Intense Fragrance" -> concentration. The R4 corpus has no such line, so "0 right refused" does not cover it; under W ON these cards lose every candidate (worse than today). R ON does not help: the resolver has no "EDT Intense" label (product_resolver.py:77-90).
Fix: `intense` directly after a concentration phrase is part of that label ("EDT Intense", "EDP Intense"); rule 2(a) fires only for a free-standing `intense` (not after a conc phrase, not before fragrance / perfume); rule 2(b) treats "EDP Intense" != "EDP" only when the query states a concentration. "YSL Y Eau de Parfum Intense" under "Y EDP" and "Libre Intense EDP" stay refused; bare Ultra Male passes. Add the probe titles to E4 as KEPT; state the residual (typed or resolved EDT for an EDT-Intense line) in section 9.

### F2 MAJOR: bare gift / travel words refuse right marketplace titles
Where: FORM_WORDS gift and travel groups, E4. Evidence (probe): "Lattafa Khamrah Eau de Parfum 100ml Unisex - Perfect Gift for Him and Her" -> form; "1 Million Eau de Toilette Spray 100ml with Gift Bag" -> form; "Boss Bottled Eau de Toilette 100ml Travel Exclusive" -> form; "Versace Eros ... Set of 1" -> form. Gift-for-him phrasing is common in GCC marketplace titles; A applies the rule whatever W reads. The 109 synthetic corpus titles carry none of it.
Fix: drop bare gift / gifts (and the Arabic gift words) as single tokens; count giftset and the adjacent joins gift+set / gift+box / gift+pack (the leaf already joins pairs, IR _candidate_keys), coffret, set(s), kit, bundle, duo, trio; count travel only joined with size / spray / set / kit. Add the four titles to E4 as KEPT.

### F3 MAJOR: part 2(a)'s OFF path evaluates caller-side code inside two price adapters
Where: 2.3 callers, `stamp_shop_image(price, platform, image, product_name, title)`. The image expression (featured_image dict test, product["images"][0]["src"]) and the function-local `from app.services import image_service` run BEFORE the A read, on every improving Shopify candidate (PS:15716 arm) and every Woo candidate (WOO:285), with A OFF in production. A malformed shape (images a str, featured_image a str or int) then raises in _match_shopify_product / _match_woo_product and the price is lost; 2.6's try covers only the body after the A read. House rule: flag OFF = base behaviour.
Fix: pass raw objects, `stamp_shop_image(best, "shopify", product, variant, product_name, _signal_text)` / `(candidate, "woo", prod, None, product_name, title)`; A read first, extraction inside the try. Better: the A reader in the leaf IR and the call guarded `if _relevance.shop_page_image_enabled():` so image_service is imported only ON. Add a P row: A unset, images = "x", featured_image = 5 -> the base dict, no raise.

### F4 MAJOR: part 2(b) skips the word rule when W is OFF; A does not
Where: 2.4 "(T2; W applies when ON)" vs 2.3 "applied whatever W reads: A is a new path". B is a new path too, and the last resort where the card shows no picture today; Shopping items for a perfume lead with sets, minis, body products (R4 classes, base AW 65/169). B ON with W OFF (rolled back or flipped out of order) turns "no picture" into a wrong picture, the incident class.
Fix: shopping_thumbnail applies words_reason_for(product_name, item title) after rel.accept whatever W reads; E12 runs with W unset.

### F5 MINOR: Parfum and Extrait are separate labels in the share test
Probe: typed "Dior Sauvage Parfum 100ml" refuses "Eau de Parfum" (by design, E4) and "Coco Mademoiselle EDP" refuses "... Parfum 100ml"; "No 5 Parfum" would refuse "Extrait de Parfum" (one concentration). A user typing Parfum for "perfume" (French / Arabic habit) loses EDP pictures under R OFF. Fix: fold Extrait and Parfum into one class for 2(b); state typed-Parfum in section 9; OQ: should 2(b) apply under R OFF.

### F6 MINOR: a form word inside an alias form of the brand refuses
Only query_words exempt brand tokens. A title using another alias form ("Bath & Body Works" under an alias-typed brand) refuses form. Fix: also exempt title tokens in ident.brand_forms (IR identity, alias-expanded).

### F7 MINOR: E7, E16, E18 hold at base except for the missing symbol
"a brand refusal reads no W", "shopping_thumbnail 0 calls", "set_cached 0 calls" are true at base and fail only through getattr. Fix: positive halves base cannot meet: E7 a passing candidate reads W exactly once; E16 the no-KB contrast calls it once; E18 the thumb IS bound (outcome=shopping) and not stored.

### F8 MINOR: per-candidate stamps and log lines
Shopify stamps in the improving arm (several per catalog); Woo stamps every candidate before select_best (PS:8627): many IMG_SHOP page lines per store per product. Fix: stamp once on the returned dict (keep the winning product / variant, or an id(candidate) -> prod map for Woo) or state the count in 2.5 / E17.

### F9 MINOR: B adds a client-side image host
Section 3 says no new host, but B makes the phone load Google-hosted thumbnails (typically encrypted-tbn*.gstatic.com); app/legal/processors.json lists recipients the code reaches (google_fonts lists fonts.gstatic.com only). Fix: add a host-class count (gstatic=<n>, constant label, no value) to the keys line and name the manifest / privacy-text check in the B owner step.

### F10 MINOR: INC-P2 collision likely; make the fallback the default
INC-P2 (size pick, floor) is in RED in the other lane and the variant bind lives in _match_shopify_product (PS:15689-15696), 50 lines above the A hunk; the PS seed drags most of tests/ into the comm set. Fix: A WooCommerce-only now (drops the PS seed), Shopify as a follow-up after INC-P2 merges, unless OQ3 is answered before RED.

### F11 MINOR: kb_ingest provenance label
A shop image reaching kb_ingest (kb_ingest.py:456-462) is labelled "retailer_og" (no jsonld_facts). KB_INGEST is closed; add to limit 15 for the gate fix.

## Mutants to add
M23 bare gift refuses (E4 KEPT rows). M24 intense after a conc phrase treated as flanker (E4 bare Ultra Male). M25 thumb without words, W OFF (E12). M26 caller-side extraction before the A read (F3 P row).
