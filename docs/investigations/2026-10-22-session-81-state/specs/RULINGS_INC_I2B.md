# RULINGS INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER (S96 orchestrator, 2026-11-17 about 01:45 AST)

The draft spec is s96/i2b/spec/INC_I2B_UNIT_SPEC.md (wf_c6650711-fa0, Opus 5.5). Its spec review, INC_I2B_SPEC_REVIEW.md, says AMEND. These rulings bind; where they differ from the draft, they win.

## Class
- I-1 (OQ1) FOCUS, so TWO adversaries after GREEN. The unit adds a refusal at a shared chokepoint while its parent flags G and S are ON in production. It adds three flags and touches an adapter.
  - Adversary 1: the WORDS. Run the false-refuse / false-accept corpus and probes beyond the RED rows, cover Arabic and French spellings, run the concentration rule under R OFF and R ON, and walk the guard version and the cache axis.
  - Adversary 2: the SHOP TIER AND PRODUCTION. Cover the A stamp in the Woo adapter, the B thumb tier, the inline override and the late chooser, log lines, the OFF byte identity of every edited region, and the flag-mix walk against production: G ON, S ON, R OFF and ON, L OFF and ON.
  - There is no further spec review.

## Open questions
- I-2 (OQ2) WIDEN the E22 GUARD_SET:
  - It covers the new functions (_check_base, _words_reason, _conc_labels and any helper they call).
  - It covers a DETERMINISTIC text of every module-level word table that check() reads, the old ones included (NAME_EXCLUDE, CONCENTRATION_WORDS, STOP_WORDS, FRAGRANCE_WORDS, BRAND_NOISE, PLACEHOLDER_BRANDS, UNIT_WORDS, ELISION, the SIZE_TOKEN pattern, and the new FORM_WORDS, INTENSE_WORDS and CONC_PHRASES).
  - Deterministic means: sets and frozensets as `repr(sorted(...))`, regexes as `.pattern`, dicts as `repr(sorted(items))`. Never a plain repr of a set, because string hash order changes per process.
  - This closes most of INC-I2a A2-1. price_service alias groups and deny rules stay outside; they are a stated limit.
  - PICK_GUARD_RULES gets its new value; E22 of tests/test_inc_i2a_picture_not_cut.py is a moved pin with that value.
- I-3 (OQ3, F10) A = WooCommerce ONLY in this unit.
  - No edit to price_service.py, so the PS seed leaves the comm set.
  - The Shopify stamp is a follow-up after INC-P2 merges; name it in the PR body as a follow-up.
- I-4 (OQ4) THREE flags: W = ENABLE_IMAGE_GUARD_WORDS, A = ENABLE_SHOP_PAGE_IMAGE, B = ENABLE_SHOPPING_THUMB_IMAGE.
- I-5 (OQ5) The public Store API shape of WooCommerce `images` is accepted for the RED fakes. The IMG_SHOP page line logs key names only, so the flip window settles the shape; stated limit.
- I-6 (OQ6) No size floor for pictures in this unit (words only); stated.
- I-7 (B owner policy) B stays OFF until the owner rules. The flip note names two checks for that window: the owner ruling on Google-hosted thumbnails, and the processor manifest / privacy text (F9).

## The concentration source (the draft's row-4 risk, ruled)
- I-8 Rule 2(b) ("a different concentration") uses ONLY a concentration the USER TYPED. A resolver default (INC-R1 fills the line's base concentration, e.g. Sauvage = EDT, when none was typed) must NEVER refuse a picture.
- The amendment agent measures how product_resolver records the variant: typed vs defaulted. It then picks the smallest seam that carries "typed concentration" into identity, by order of preference:
  1. a field the resolver already sets;
  2. the typed text already reachable from the guard call;
  3. a new defaulted keyword in relevance_kwargs.
- A bare typed "Dior Sauvage" with R ON keeps both EDT and EDP pictures. RED row: R ON, bare name, Serper fake [EDP item first] -> the EDP URL is accepted with W ON.

## The review findings
- I-9 (F1) ACCEPTED. "Intense" directly after a concentration phrase is part of the label (EDT Intense, EDP Intense). Rule 2(a) fires only for a free-standing "intense" (not after a concentration phrase, not before "fragrance" or "perfume"). 2(b) treats "EDP Intense" != "EDP" only when the user typed a concentration. The review's probe titles join E4 as KEPT for a bare query, and the typed-EDT residual is stated.
- I-10 (F2) ACCEPTED.
  - The bare tokens "gift", "gifts" and the Arabic gift words never refuse alone.
  - These count: "giftset" and the adjacent joins gift+set, gift+box, gift+pack; coffret, set(s), kit, bundle, duo, trio.
  - "travel" counts only when joined with size, spray, set or kit.
  - The four review titles join E4 as KEPT. New mutant: a bare "gift" refuses.
- I-11 (F3) ACCEPTED. The A reader lives in the IR leaf. The adapter call is guarded with `if _relevance.shop_page_image_enabled():`, so with A OFF the adapter runs its base path: no image expression, no image_service import. The raw objects are passed and extracted inside the try. P row: A unset, images='x' -> the base dict and no raise.
- I-12 (F4) ACCEPTED. The thumb tier applies the word rule after rel.accept whatever W reads. E12 runs with W unset. New mutant: a thumb without the words test.
- I-13 (F5) ACCEPTED. Extrait and Parfum fold into one class for 2(b). A typed "Parfum" refusing EDP is a stated limit. 2(b) runs only on a typed concentration (I-8).
- I-14 (F6) ACCEPTED: title tokens inside ident.brand_forms are exempt from rule 1.
- I-15 (F7) ACCEPTED: positive halves for E7, E16 and E18, as the review states.
- I-16 (F8) ACCEPTED: stamp once on the select_best winner (an id(candidate) -> prod map). One IMG_SHOP page line per store per product.
- I-17 (F9) ACCEPTED: the IMG_SHOP keys line gains a constant host-class count (gstatic=<n>; constant labels, no values).
- I-18 (F11) ACCEPTED: stated limit 15 says a shop-API image reaching kb_ingest would be labelled retailer_og. ENABLE_KB_INGEST stays closed until its gate fix.

## The cache axis and the version
- I-19 The pick_cache_name axis carries W (w0/w1) beside s0/s1, so a pick stored under the looser rule is never read with W ON. A and B never write the pick cache (B is never stored; the A stamp is a price field). PICK_GUARD_RULES moves (I-2): one paid miss per product once L is ON, as stated.
