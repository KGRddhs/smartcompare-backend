# INC-M1 MATCH-FOLD: spec (S96-FIX, 2026-11-17)

Base: main 7f672cfef1445233b58c323a08515baec7aae4bd. Merge main before the PR. If #419 has merged by then, take it in; it does not overlap these files.
Facts: <SP>/INC-M1/INC_M1_FACTS.md (measured at the base, read-only). R4: research-2026-11-16/R4_matching.md and work/R4/.
Arabic strings: write them in tests as Python escapes built at run time (see H7: the tool layer decodes backslash-u in tool text, so build each escape with chr(92) or write the code points as chr(0x062F) calls). Every file stays pure ASCII.

## 0. The split (ruling M1R-1)

The relay's INC-M1 has five parts. They become two units in sequence, each with its own PR.
- **INC-M1a RESOLVER FOLD:** Arabic typed names, the seed rows, and the Arabic concentration words. The files are `app/services/product_resolver.py` and `data/fragrance_lines.json`. It has no new flag: everything rides ENABLE_PRODUCT_RESOLVER (OFF on web), the hook being the only reader of the resolver's output.
- **INC-M1b MATCHER FOLD:** the brand alias fold in the identity subset, a houseless distinctive line, the single-concentration default, and padding words. The file is `app/services/price_service.py`, behind the new flag ENABLE_MATCH_FOLD, default OFF, read per call.

Both must merge BEFORE ENABLE_PRODUCT_RESOLVER opens. M1a goes first, because M1b reads the seed field M1a adds.
Why split: M1a is resolver-only and has no flag-OFF risk outside the hook. M1b changes the price gate itself and needs the full flag-mix walk. One unit would mean one long RED and two adversaries on mixed files.

## 1. INC-M1a RESOLVER FOLD

### 1.1 Facts this rests on (INC_M1_FACTS Q2, Q3, Q5, Q6)
- The resolver hook (scs:4622 sync, :5345 stream) runs BEFORE every search call on both paths. A search goes out as typed only because the hook is off or the side stayed unresolved.
- The lexicon arm leaves AR_A, AR_B and AR_B_YA unresolved: there are no Arabic line aliases, so `_find_house` finds the Arabic house and then the line search finds nothing.
- With Arabic house_aliases and line aliases added to data/fragrance_lines.json as JSON escapes, all three resolve high/lexicon. apply_resolution then writes the same dicts as for the Latin names, with no model call and no spend.
- After that rewrite:
  - the price filters read only the Latin fields (full_name, search_query, the cache key);
  - the picture guard builds its query and identity from the Latin brand and name fields;
  - the words guard's `typed` input changed no verdict on the corpus.
  So parity needs NO edit to image_relevance.py or image_service.py, and this unit touches neither.
- **The model arm is NOT needed for the RED rows.** The only switch that must be ON for Arabic typed names to reach search as Latin is ENABLE_PRODUCT_RESOLVER. This answers the relay's question.

### 1.2 What M1a builds
1. **Arabic aliases (the one home).**
   - In data/fragrance_lines.json:
     - Dior/Sauvage: `house_aliases` += the Arabic Dior (U+062F U+064A U+0648 U+0631); `aliases` += the Arabic Sauvage (U+0633 U+0648 U+0641 U+0627 U+062C).
     - Chanel/Bleu de Chanel: `house_aliases` += the Arabic Chanel (U+0634 U+0627 U+0646 U+064A U+0644); `aliases` += the WAW form (U+0628 U+0644 U+0648, space, U+062F U+0648, space, the Arabic Chanel) AND, explicitly, the YA form (the particle U+062F U+064A). Do not rely on the fuzzy OSA-1 match (M1R-3).
   - Write them as JSON escapes. The loader refuses any byte > 127 (product_resolver.py:496-497), and the file stays ASCII.
   - This file is the ONE home for Arabic brand and line spellings. A later reader (R4-9 Arabic titles, Arabic pictures) reads it through a product_resolver accessor, never through a second table (M1R-2).
2. **Arabic concentration phrases.**
   - The resolver's typed-concentration reader also accepts the Arabic concentration phrases that data/fragrance_lexicon.json already holds (3 forms: EDP, EDT, Parfum, written with the WAW particle). It also accepts each phrase with the YA particle.
   - It reads them from the lexicon and builds no new table: the lexicon is the one home for concentration words.
   - It maps them to the same Latin tokens CONCENTRATION_PHRASES returns, and it runs only inside the resolver (the hook).
   - price_service.extract_concentration is NOT changed: after apply_resolution, the variant is the Latin token.
3. **Seed rows (R4-5 data, no invented facts).**
   - Add the line Yves Saint Laurent / Y: concentrations [EDT, EDP], base EDT, flankers [Le Parfum, Elixir].
   - Add the line Rasasi / Hawas: concentrations [EDP], base EDP, flankers [Ice, for Her]. house_aliases [rasasi], plus the lexicon's Arabic Rasasi as an escape if the lexicon holds it (it does: facts Q3).
   - Add flankers to existing lines:
     - Libre: Intense, Le Parfum;
     - Khamrah: Qahwa, Dukhan;
     - Aventus: for Her, Absolu, Cologne.
   - Correct Libre's concentrations to [EDT, EDP], keeping base EDP (Libre Eau de Toilette exists; M1R-4).
   - Add the optional field `"single_concentration": true` ONLY to Aventus, Layton, Khamrah and Hawas. It defaults to false, and the validator (:454-476) accepts it. M1b reads this field; M1a only adds it and pins it.
   - Change no other line's data.
4. **Flanker words before generic words.**
   - A typed flanker word that equals a seeded flanker of the resolved line ("Aventus Cologne", "Hawas for Her", "Hawas Ice", "Libre Intense", "Khamrah Qahwa") is matched BEFORE GENERIC_WORDS (cologne) and QUALIFIER_WORDS (for, her) drop it.
   - The side then resolves to the line WITH that flanker (the existing flanker representation: read how Stronger With You's flankers resolve today and use the same).
   - It never resolves to the base key at high confidence. "Dior Sauvage Tester" keeps today's behaviour (the owner has not ruled on testers; stated limit).

### 1.3 RED rows (minimum; RED may add)
- **AR-1:** resolve_pair(AR_A, AR_B) is `resolved`, giving [(Dior, Sauvage, EDP), (Chanel, Bleu de Chanel, EDP)]. apply_resolution produces exactly the dicts of resolve_pair(LAT_A, LAT_B) (brand, name, variant, search_query, category). Run it for AR_A+LAT_B, AR_B+LAT_A and AR_B_YA+LAT_A as well.
- **AR-2:** the same through the compare entry seam with ENABLE_PRODUCT_RESOLVER=true, the Step-2 fetch stubbed.
  - The stubbed search calls record their query.
  - The serper-shopping query, the unified-search query, the price cache key and the image query (full_name + " perfume") are byte-equal between the Arabic pair and the Latin pair.
  - Cover the sync path and the stream twin.
- **AR-3:** with the three RED strings and the Latin twins, the accepted-candidate sets of _selection_match and is_price_showable over the R4 corpus rows for both lines are equal. Use the facts Q4 LATIN column as the frozen golden.
- **AR-4:** the picture identity is equal: relevance_kwargs, then identity, then the verdict per corpus title under ENABLE_IMAGE_GUARD_SHORT_LINE ON, with ENABLE_IMAGE_GUARD_WORDS both off and on. Read image_relevance as is; edit nothing there.
- **AR-5:** an all-Arabic concentration phrase resolves to the Latin token: the Arabic Dior + the Arabic Sauvage + the lexicon's Arabic EDP phrase (WAW and YA) gives (Dior, Sauvage, EDP).
- **SEED-1:**
  - Typed "YSL Y EDP" and "Rasasi Hawas" resolve high/lexicon.
  - "Creed Aventus Cologne" resolves to the Aventus line with the Cologne flanker, NOT (Creed, Aventus, EDP) at high.
  - Run the same check for "Rasasi Hawas for Her", "Hawas Ice" and "Lattafa Khamrah Qahwa".
- **SEED-2:** the validator accepts `single_concentration`, rejects a non-boolean value, and the file stays pure ASCII.
- **PIN-0 (flag-OFF identity):** with ENABLE_PRODUCT_RESOLVER unset, the compare seam output for the Arabic pair and for the Latin pair is byte-identical to the base.
  - Also pin every non-hook reader of product_resolver / fragrance_lines.json found by `git grep` at the base: text_routes.py, error_handler.py, url_extraction_service.py (S97's file: read only), and scs outside the hook. Each must be either unaffected or pinned.
- **PIN-1:** the 12 existing lines resolve exactly as at the base for the R4 typed set (typed_resolver.txt), except the rows this spec changes on purpose: Libre's concentration set, and the flanker rows. Those changes are listed in the gate as deliberate.

### 1.4 Not in M1a (stated limits)
- The Arabic ml word.
  - Neither extract_sizes_ml nor the resolver reads it.
  - reconcile_pair_fairness reads sizes from the typed query, so "100 ml" typed in Arabic loses its size.
  - Out of scope; a later unit.
- Arabic names outside the two seeded lines go to the model arm. That needs ENABLE_PRODUCT_RESOLVER + ENABLE_ANTHROPIC_TEXT + a consent-3 request + the spend admit.
- Arabic-script listing titles (R4-9) and Arabic pictures (an image_relevance.py line-forms edit, S96's file): parity only. An Arabic-only title is still refused, exactly as under a Latin typed name.
- Display: the phone shows the resolved Latin name ("Dior Sauvage EDP") for an Arabic-typed name. This is the resolver's existing behaviour for every resolved side; the flip window shows it to the owner.
- Testers: unchanged (owner question 1 of R4).

### 1.5 Change list
data/fragrance_lines.json, app/services/product_resolver.py, CLAUDE.md (the INC-R1 block gains the M1a rows; the flag line is unchanged), tests/test_inc_m1a_resolver_fold.py (new).
Comm seed: facts Q8 plus the source-scanning pins (house rule).
No client file changes: ar.json must not change. The 14 client fences run once at GREEN.

### 1.6 Chain
SMALL-to-MEDIUM, resolver-only and dark behind an OFF flag: one correctness adversary (leaner chain), with the flag-mix lens folded in.
The flag mixes are ENABLE_PRODUCT_RESOLVER x ENABLE_ANTHROPIC_TEXT x consent (2 / 3) x ENABLE_IMAGE_GUARD_WORDS for AR-2 and AR-4.

## 2. INC-M1b MATCHER FOLD (spec only; starts after M1a's PR, on the meter)

Flag ENABLE_MATCH_FOLD, default OFF, read per call (house idiom). Flag OFF must be byte-identical.
1. **Alias fold in the identity subset** (R4-2).
   - In _descriptor_selection_verdict, fold every member of a brand alias group to one token on BOTH sides before the identity subset and variant add.
   - Use price_service._BRAND_ALIAS_GROUPS plus a NEW private table `_M1B_EXTRA_ALIAS_GROUPS` ({mfk, maison francis kurkdjian, francis kurkdjian}, {saint laurent} joined to the ysl group), read ONLY by this fold.
   - The shared _BRAND_ALIAS_GROUPS stays byte-identical: five other modules read it (price_service :5424 :6970 :6978 :7016 :11810, image_relevance :383, product_resolver :561, spec_spine_service, zyte_service).
2. **Houseless distinctive line.**
   - A title may omit the house when it carries every line token of a seeded line that is distinctive (two or more line tokens, or one token of six or more letters; so Sauvage, Aventus, Khamrah, Layton, Baccarat Rouge 540 and Bleu de Chanel qualify, and Y, Libre and Eros do not).
   - The line is read through a product_resolver accessor (the one home), never a copied list.
3. **Single-concentration default** (R4-3). In _vd_candidate_missing_query_axis (fragrances), a candidate that omits the concentration counts as stating the query's concentration ONLY when:
   - the query's line is a seeded line with `single_concentration: true`;
   - the query concentration is that line's one concentration;
   - the title names no flanker word of that line.
4. **Padding.** RED measures which of pour, homme, femme, vaporisateur, vapo and natural are not yet stripped (_FRAGRANCE_PADDING_TOKENS, _GENDER_IDENTITY_STRIP) and adds only those, under the flag.
- **RED rows:**
  - The R4 lost_why brand-spelling rows (7), the missing-axis rows (3) and the variant-add row ("Christian Dior Sauvage EDP 60ml") turn into accepts.
  - The brandform.txt rows ("YSL Libre EDP 90ml" under "Yves Saint Laurent Libre EDP"; "Baccarat Rouge 540 Eau de Parfum 70ml" under "Maison Francis Kurkdjian Baccarat Rouge 540 EDP"; "Creed Aventus 100ml" and "Lattafa Khamrah 100ml" under their resolved EDP queries) turn into accepts.
- **GUARD rows (must stay rejected):**
  - Sauvage EDT under an EDP query, and "Dior Sauvage 100ml" (no concentration) under "Dior Sauvage EDP": a multi-concentration line still fails closed.
  - Hawas for Her, Aventus for Her and Aventus Cologne under the base query.
  - The dupe, mini, travel, gift-set, refill and body rows of the corpus.
  - Every Arabic title, unchanged.
- **Flag mixes to walk:** ENABLE_MATCH_FOLD x ENABLE_PRICE_NOT_LOST x ENABLE_VARIANT_DESCRIPTOR_AXES x ENABLE_LISTING_MATCH_GUARD x ENABLE_DATA_GUARDS_V2 x ENABLE_PRODUCT_RESOLVER, on the full R4 confusion matrix. Report the AW (accepted wrong) count per mix: it must not rise in any mix.
- **Chain:** it changes the price gate, so two adversaries (correctness; flag-mix and wrong-price), then one re-verifier per fix round.

## 3. Gate line for the relay
- M1 needs NO edit to image_relevance.py or image_service.py.
- The one home for Arabic brand and line spellings is data/fragrance_lines.json (via product_resolver).
- The fold alone carries the RED rows; the model arm is not needed. The switch that must be ON for the effect is ENABLE_PRODUCT_RESOLVER.
- M1a has no new flag. M1b adds ENABLE_MATCH_FOLD.
- Arabic typed names reach search as Latin only once ENABLE_PRODUCT_RESOLVER is ON. I did not build a second pre-hook path while the resolver is dark (M1R-5); the relay may overrule this.

### 1.7 M1a mutants (RED proves each is killed; RED may add)
- MA1: drop the Arabic line alias of Sauvage (house alias kept).
- MA2: drop the YA alias of Bleu de Chanel (WAW kept). If the OSA-1 fuzzy match still resolves it, the mutant survives: then a row must pin the explicit YA alias by reading the data file (M1R-3).
- MA3: the Arabic concentration phrases read with the WAW particle only.
- MA4: Arabic concentration phrases mapped to EDT for every phrase.
- MA5: flanker matched AFTER the generic-word drop (today's order).
- MA6: `single_concentration` accepted as any truthy value (the validator).
- MA7: the Arabic aliases written as raw UTF-8 bytes (the loader must refuse; a row pins that the file is ASCII and still loads).
- MA8: apply_resolution keeps the typed Arabic as search_query (the AR-2 seam must catch it).
- MA9: Libre's concentrations left as [EDP].
