# INC-I2b adversary A1 (THE WORDS): NOT_READY

Head aec760b5a6657765fed22f591a40d76fdd891435 (parent 5cd93c6a; `git -C W log --oneline -3` shows aec760b5, 5cd93c6a, 16662850). Diff read in full for the four app files, the I2a test and CLAUDE.md. W was not written: probes ran from a detached scratch worktree at the head (since removed) with `-B`, and the flags were patched as module attributes inside the probe process. No ENABLE_* or credential name was set in any shell.

## Runs
- [pyt] tag=s96b-adva1-redax, 04:22:21 to 04:22:27, status=OK rc=0. RED file + addenda: 38 passed. netguard 0, hermeticity sentinel 38.
- Digest probe (probes/digest.py), three fresh interpreters with PYTHONHASHSEED=0, random and 777: all three give a9bdcc90 (full prefix a9bdcc901c1bd5dc), the same as PICK_GUARD_RULES.
- Words probe (probes/mkcases.py -> cases.json, probes/words.py -> words_out.txt): 179 fresh real-shaped rows. Modes:
  - roff: the production explicit dict, brand "", line = typed = full_name;
  - ron: resolver-rewritten, typed = carrier, or "" with no carrier;
  - q: the parser path, typed = full_name.
- Extra probes: tok.py (tokens and _conc_scan), ar2.py (Arabic under R OFF), resolver.py (resolve_lexicon on names that carry a form word).

## Findings

### F-A1-1 MAJOR: a marketing "Intense" refuses the right bottle (rule 2(a))
INTENSE_GENERIC_NEXT holds only fragrance and perfume. Any other word after a stand-alone "intense" sets free_intense, and the title is refused with `concentration` for every query: bare or typed, R OFF or ON. Measured as base None, then concentration with W ON:
- "Dior Sauvage Eau De Parfum 100ml - Long Lasting, Intense Scent" (typed Dior Sauvage EDP)
- "Dior Sauvage EDP 100ml, Intense Long Lasting Fragrance for Men"
- "Dior Sauvage Eau de Parfum 100ml Intense and Long Lasting"
- "Lattafa Khamrah Eau De Parfum 100ml - Sweet, Intense & Long Lasting" (bare Lattafa Khamrah; "&" drops out, so the tokens read intense, long)
- "Dior Sauvage EDT 100ml, Intense Woody Scent" (bare Dior Sauvage)

None of L1 to L16 states this. E4b keeps only the exact "Long Lasting Intense Fragrance" shape.

Fix: refuse a free intense only when it sits next to a concentration phrase, or at the end of the title or the line, or before a size token. Otherwise, at the least, add scent(s), long, lasting, and, smell, aroma to INTENSE_GENERIC_NEXT. Add a RED row for each of the five titles.

### F-A1-2 MAJOR: an Intense flanker typed with a concentration loses the title written in the other order (rule 2(b))
_conc_scan folds "intense" into the label only AFTER a phrase. "Intense EDP" therefore reads {EDP} (plus a free intense), and "Eau de Parfum Intense" reads {EDP Intense}. When the user typed both the intense and a concentration, the two orders are disjoint and the right bottle is refused:
- typed "Valentino Born in Roma Intense EDP" vs "Valentino Donna Born In Roma Eau de Parfum Intense 100ml"
- typed "Coco Mademoiselle Eau de Parfum Intense" vs "Chanel Coco Mademoiselle Intense EDP 100ml"
- typed "Coco Mademoiselle Intense EDP" vs "Chanel Coco Mademoiselle Eau de Parfum Intense Spray 100ml"
- typed "Dior Homme Intense EDP" vs "Dior Homme Eau de Parfum Intense 100ml"
- typed "Boss Bottled Intense EDP" vs "Hugo Boss Boss Bottled Eau de Parfum Intense 100ml"
- typed "Le Male Le Parfum EDP Intense" vs "Jean Paul Gaultier Le Male Le Parfum Intense Eau de Parfum" ({Parfum, EDP Intense} vs {Parfum Intense, EDP})

L2 covers only a typed EDT WITHOUT intense. On the q= path the parser variant counts as typed (L4), so "name ... Intense" plus a variant of EDP hits this too.

Fix: in 2(b), when INTENSE_WORDS & query_words is not empty, remove the " Intense" suffix from both label sets before the disjoint test. Keep free_intense for an intense before a phrase so that rule 2(a) is unchanged. Add a row for each of the six.

### F-A1-3 MINOR: the I-14 brand-form exemption is inert on today's explicit path
On the explicit path (production, R OFF) the dict brand is always "" (SCS:2048 and 4575, never reassigned in _fetch_product_data at SCS:6195). So brand_forms is empty, and a line typed without its brand loses the brand's form words:
- "Japanese Cherry Blossom" vs "Bath and Body Works Japanese Cherry Blossom Eau de Parfum 75ml": form
- "White Musk" vs "The Body Shop White Musk Eau de Toilette 60ml": form

The E4d row passes only because it builds the relevance with brand "Bath & Body Works", a shape the R OFF path never produces. With the brand typed, query_words exempt it, and both pass.

Stated limit: "I-14 needs a known brand (R ON or the q= parser); under R OFF a typed line without its brand loses Bath & Body Works / The Body Shop pictures."

### F-A1-4 MINOR: a brand spelled with the bare word Parfum reads as the Parfum concentration
Typed "Parfums de Marly Layton EDP" (or "Layton EDP") vs "Parfum de Marly Layton for Men 125ml" gives {Parfum} vs {EDP}, so the title is refused with concentration. That title is a common marketplace misspelling with no other concentration phrase. The plural "Parfums" does not trigger it, and nor does the bare query. Brand forms are exempt from rule 1 only, not from the concentration scan.

Stated limit, or exempt a "parfum" token followed by "de marly" / "d empire".

### F-A1-5 MINOR: residual false refuses and false accepts (stated-limit text)
- Refused:
  - a note word: "... Notes of Bergamot, Lavender and Vanilla Oil" (form);
  - "Dior Sauvage EDP 100ml in Gift Box" (form; as I-10 rules, but this is the right bottle in its retail box).
- Accepted, wrong:
  - "Twist and Spray 3 x 20 ml" (a refill or travel set);
  - "EDP 10ml Roll-On" (FORM_WORDS has rollerball, not roll / on);
  - "Eau Forte", "Kenzo Flower Poppy Bouquet", "Rasasi Hawas Ice", "La Vie Est Belle L'Elixir" (bare): flankers, L1.
- Arabic "او دو بارفيوم" / "برفيوم" (the common Golden Scent spellings) read no label, so they are lenient, not refused.

### F-A1-6 MINOR: the Arabic parity claim is wider than the code
GB-8 says "the unit changes nothing for an Arabic-script typed name", and ARABIC_PROBE says W "adds no new refusal or acceptance". Under today's R OFF path (brand "") an Arabic title that passes base (it carries the Arabic perfume word) now gets the Arabic FORM_WORDS and CONC_PHRASES. For typed "ديور سوفاج EDP", the titles عطر + ديور سوفاج + one of these words are refused with W ON (None at base):
- طقم هدية (gift set): form
- او دو تواليت (EDT): concentration
- عينة (sample): form
- للشعر (for hair): form

All four are correct refusals. The Arabic gift word alone stays None (AX-3 holds). AX-1 passes because its eight probe titles carry none of these words.

Fix the wording, not the code: "W adds only the listed Arabic form and concentration words; no right Arabic title was found refused."

### F-A1-7 MINOR: the guard version still misses identity's helpers and two tables (a pre-existing gap, L10 wording)
Walking the code objects of GUARD_SET transitively, these are reached but not hashed:
- functions: _line_keys, _line_tokens, _before_unit, alias_groups, _category, _denied, _https, _raster_path, _related, _str, dict_items;
- verdict-bearing constants: FRAGRANCE_WORD_CATEGORIES, FRAGRANCE_CATEGORY, OTHER_CATEGORY, TIER3_ORGANIC_MAX, _HTTPS.

Every word table check() reads IS in the text, and the text is deterministic. A later edit to _line_keys or FRAGRANCE_WORD_CATEGORIES changes verdicts without moving PICK_GUARD_RULES.

Add them, or name them in L10. Separately, CLAUDE.md:728 still lists the old GUARD_SET and "INC-I2b is next" (stale; doc only).

## Probed and cleared
- **Determinism:** the digest is the same across hash seeds; sets are sorted, CONC_PHRASES is a sorted tuple (a stable sort by length), and the regexes are hashed by `.pattern`.
- **The concentration rule, R OFF and R ON** (ron and q rows):
  - bare + R ON keeps the EDP and the EDT pictures;
  - carrier "Dior Sauvage EDP" refuses EDT and Elixir;
  - a rewritten dict without the carrier ("") keeps both pictures;
  - q= with full "Dior Sauvage EDT" refuses EDP (GB-3 / L4 as ruled; the parser prompt says "variant/size if mentioned", extraction_service.py:115).
- **Cache axis:** pick_cache_name adds "w1:" + the sorted typed labels (constants), and is unchanged with W OFF. I also checked whether the typed-word exemption (query_words) could poison the R ON name. resolve_lexicon does not resolve any form-word name: "Dior Sauvage Gift Set / Deodorant / Travel Spray / Mini / Refill / Body Mist / Shower Gel / After Shave", "Lattafa Khamrah Hair Mist / Oil". The model arm's guard (d) (_line_within_typed, QUALIFIER_WORDS) also refuses a residual form word. So under R ON a typed form word never shares a name with the bare line. Under R OFF the line is the typed text.
- **French:** Vaporisateur, Homme, Recharge (refused), Coffret (refused), "Eau Fraîche" (folds to Eau Fraiche), "L'Elixir" (Elixir), "Eau Extreme" (no label).
- **Elixir / Extrait / Parfum:** Elixir with "Parfum" after it, Extrait folding into Parfum, typed Parfum vs EDP refused (L3), typed Elixir vs EDP refused.
- **Brand or line with a form word, when typed:** Montale Powder Flowers and Montale Intense Cafe kept; Refillable and Rechargeable kept.
- **First text:** every guarded call passes the title as the first text (image_service.py:277, 287, 294, 311, 870; IR _organic_reason). accept_pick's `check(ident, (), ())` reads no words.

## Verdict
NOT_READY, on two MAJOR findings: F-A1-1 and F-A1-2 refuse a right picture outside the stated limits. Both are small changes to _conc_scan / _words_reason plus new RED rows. F-A1-3 to F-A1-7 become stated limits or wording changes.
