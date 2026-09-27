## W4-8: category truth. Pharmacy "tablets" stop being electronics (flagged), and the weapons/drug blocklist gains a precision v2 (flagged)

This covers findings PO-CATEGORIES-I18N-01 (P1) and -03 (P2), plus the Arabic audit in -09. Base is 04acb757. Both halves ship dark.

### Flags

Both default OFF. Both are read PER CALL via `os.getenv(...).strip().lower() in ("true","1","yes","on")`, so a Railway flip needs no restart.

| flag | reader | effect ON | OFF |
|---|---|---|---|
| `ENABLE_CATEGORY_TOKEN_FIX` | `extraction_service.category_token_fix_enabled()` | a pharmacy/household veto runs on the ambiguous `tablet`/`tablets` hit in `classify_category_from_text` | the 04acb757 path, byte-identical |
| `ENABLE_BLOCKLIST_PRECISION_V2` | `content_safety_service.blocklist_precision_v2_enabled()` | L1 `check_query_intent`, L2 `is_text_safe` and `filter_shopping_items` use the v2 matcher | the v1 matcher, byte-identical |

### History: three carve-out rounds failed on the same class; grams no longer veto

**Rounds 1-2.**
- Half A reused `SUPPLEMENT_DOSE_RE`, which reads a bare integer + `g` as grams. Device tablets (`8G 128G`, `2.4G WiFi`, `1TB 12G`) became supplements.
- Half B dropped the bare tokens and enumerated intent phrases. Unlisted phrasings (`buy a silencer`, `glock 17 silencer`, a bare Arabic rifle) became allowed.

**Fable R10-R12 inverted both halves.**
- Half A got a dedicated dose pattern in which a bare integer + g never vetoes.
- Half B keeps v2 lists equal to v1 and gets its precision from a per-token exemption map.

**Rounds 3 and 4** kept a decimal-gram rung, first with a Wi-Fi band list and then with a `< 2.0 g` bound. The adversaries found `5.0G`, `2.45G`, `Tablet 0.5G` and `1.2 g-sensor` becoming supplements: the same class, a third time.

**Rulings R13/R14 ended it.**
- GRAMS NEVER VETO: the gram branch is deleted.
- R11's named context words are the qualifier FLOOR.
- The allowed set is OPEN over co-occurrence.

**Adversaries r5 and r6 returned SOUND** with minors. Rulings R15/R16 then tightened four things:
- the dose pattern's lookarounds (R15a, R16a);
- a stated limit for car-accessory strings (R16b, W4-8g);
- the whitespace pin (R16d);
- a per-field exemption on the L2 title + snippet surface (R16c).

### Half A: the rule as built (R2 veto-only + R10 + R13a/R14a + R15a/R16a)

With the flag ON, a hit on `tablet`/`tablets` runs `_tablet_veto(low)` in the order below. The veto runs ONLY for those two tokens; a pin catches a veto on every electronics synonym.

1. **Household token** (whole token): `descaling`, `dishwasher`, `washing machine`, `detergent`, `chlorine`, `denture`, `purification`. The tablet hit is skipped and the sweep continues, usually to `other`. Pinned: `Finish dishwasher tablets for food residue` goes to `grocery`.
2. **Dose** (a dedicated `_TABLET_DOSE_RE`, not `SUPPLEMENT_DOSE_RE`): ONLY an explicit pharmacy unit next to a number: `mg`, `mcg`, `ug`, the micro sign (U+00B5) or Greek mu (U+03BC) + `g`, `iu`, `ml`. **No gram form vetoes, integer or decimal.**
   - Pattern: `(?<![a-z0-9.,])\d+(?:[.,]\d+)?\s*(?:mg|mcg|ug|µg|μg|iu|ml)(?![a-z]|\s*\d)` (the micro and mu characters are ASCII escapes in the source).
   - **Before the number (R15a):** nothing alphanumeric and no `.`/`,`. So a number glued to a model code is not a dose, integer or decimal: `Tablet model X500mg`, `Tablet model X1.500mg` and `Tablet X2,500mg` are electronics. The decimal group is load-bearing: `tablet 1.5mg` and `tablet 0.25 mg` are supplements, and `tablet 500mg` is unchanged.
   - **After the unit (R16a):** a letter makes the unit part of a word (`tablet 2 ugreen stand`). A digit, with or without a space, makes it a model code: `Mercedes 2015 ML350 tablet holder`, `2012 ML 350 tablet mount`, `tablet 500mg2` and `2024 MG4 tablet screen protector` are electronics. `tablet 2 ml` is unchanged.
   - **Between number and unit (R16d):** any whitespace. Two spaces, a tab and U+00A0 each give supplements, pinned.
   - A unit anywhere in the text vetoes. The result is `supplements`.
3. **Pack count** `N tablets`/`N tabs` fires only when:
   - pack vocabulary (`pack`, `pack of`, `bottle`, `strip`, `blister`, `count`, `ct`, `pcs`, `x`) is adjacent to the count: before the number, between it and `tablets`, or right after (also `per strip`); OR
   - N >= 30.

   The ONE carve-out (R13b, accepted): a four-digit 1900..2099 before `tablets` is a listicle year, not a pack. It is pinned both ways: 1899 and 2100 veto; 1900, 2099 and `best 2026 tablets` do not. Pack context wins over the window (`bottle of 2000 tablets`). The result is `supplements`.
4. **Pharmacy token** (whole token): `effervescent`, `chewable`, `paracetamol`, `ibuprofen`, `panadol`, `adol`, `brufen`, `pharmacy`, `laxative`, `antacid`, `flu`, `vinegar`, `glucose`, `dose`, `dosage`. The result is `supplements`.
5. **No veto:** `electronics`.

The spec's rungs 2/3 (hard device spec, device vocabulary) are not built; under R2's veto-first order they are output-inert. `_CATEGORY_SYNONYMS` and `canonicalize_category` are untouched (pinned).

**Resolver and cost (R1):**
- A pharmacy pair returns `('supplements', False, None)` with or without a Supplements chip, and makes 0 A2b calls.
- A chipless HOUSEHOLD pair pays ONE A2b gpt-4o-mini call (`classify_category_llm`, 4 s cap).
- Device pairs and chipped pairs make no A2b call.

**Measured ON:**
- **Device recall.** The review's 27 out-of-vocabulary devices: **27/27** electronics.
- **Device-sense rows: 174/174** electronics. These are every device string of adversaries r1-r4 that is written without pack vocabulary or a pharmacy token, plus the boundary guards (`8G 128G`, `2.4G/5.0G`, `2.45G`, `10.1 G-sensor`, `1.6GHz`, `Tablet 0.5G`, `Android tablet 1.5G RAM 16G ROM`, `Tablet 7 inch 1.2G CPU`, `tablet bluetooth 1.2 g-sensor`, `Tablet 2.0G`, `Tablet 1G RAM 8G ROM`, and the R15a/R16a model codes above).
- **Supplements BY DESIGN (R15b).** Adversary r3's probe_a3.py holds a pack-context group that reads supplements under A through the count rung with adjacent pack vocabulary: `Samsung Galaxy Tab 2 tablets x 128GB`, `iPad Air 2 tablets pcs`, `Bundle 2 tablets count`, `Fire HD 10 Kids 2 tablets pack`, and `lenovo tablets 64 tabs open` (count >= 30). Two token rows also read supplements, through the `flu` and `pharmacy` tokens: `Galaxy Tab S9 tablet flu season` and `iPad tablet for pharmacy POS`. All are pinned so in PROBE_ROWS. This is a stated limit: a device listing that writes a quantity with pack vocabulary next to `tablets` is read as a pack.
- **Probe rows.** Every string of adversary r3's probe_a3.py / probe_lookahead.py and adversary r4's probe_r13.py is pinned verbatim with its verdict (79 rows).
- **Unit pins.**
  - The token-free rows `tablet 5 µg` and `tablet 5 μg` carry the micro-sign / Greek-mu unit pins; the unit alone decides.
  - The verbatim `Vitamin D 25µg tablets` and `Vitamin B12 500 μg tablets` rows are R14a's verbatim pins, not unit pins; `vitamin` already answers them with the flag OFF (R16d).
  - `Claritin 10mg tablets vs Zyrtec 10mg tablets` and `Paracetamol 500mg tablets` are supplements.
- **Pharmacy precision.** The review's 25 pharmacy/household strings: 14 supplements, 8 other, 3 brand-only electronics.
- **Corpus delta.** The 360-row corpus moves exactly one record (`C:supplements:05`, Ferrous sulfate 65mg tablets). The ON corpus hash is `5b5a4b70c85ffef47ce5788e6405eb3ed5f3973656b97055deba59d7eab49e8f`, unchanged this round.
- **Corpus + 35 tablet rows.** C:supplements:05 + TP:00..16 move; hash `ef29dbee204b015084fe6ee33c5fd0afb9c4b09f28b84763a6c58e42eef7b793`. R16a changed exactly one half: TP:04's `Nurofen 200mg 24 tablets` reads electronics. The pair still resolves supplements through `brufen` and `30 tablets`.

### Half B: v2 = v1 plus an exemption map (R11, R12, R13c/R14b, R16c)

`app/data/content_blocklist.json` was edited in place: raw UTF-8 Arabic, CRLF kept, `version` bumped to "2", `updated_at` 2026-09-27. The v1 `categories` are byte-unchanged (pinned).

`v2.categories` overrides weapons.en, weapons.ar and illegal_drugs.ar with lists EQUAL to v1; set equality and order are pinned. `v2.exempt.<cat>.<lang>.<token>` lists qualifiers.

Under the flag, a token with exemptions does not block a text that also contains one of ITS qualifiers:
- The qualifier match is whole-token, lowercased and `re.escape`d, with the matcher's own boundary.
- Every other token still blocks. v2 compiles every category, and both matchers are compiled at construction and selected per call.

**R16c: the exemption is decided per FIELD on the shopping surface.**
- `filter_shopping_items` still finds tokens over the joined title + snippet surface (the v1 decision), but a token in the title is exempted only by a qualifier in the title, and one in the snippet only by a qualifier in the snippet.
- A multi-word token that spans the two fields is in no single field, so no qualifier exempts it.
- Pinned, v1 / v2:
  - title `Silencer 9mm` + snippet `ships by car`: dropped / dropped (adversary r6's case; it was kept under round 5's v2);
  - `Solvent trap silencer kit .22` + `fits car cleaning`: dropped / dropped;
  - `Bosch exhaust silencer` + a benign snippet: dropped / kept;
  - `Silencer 9mm` + `Bosch exhaust silencer for cars`, and the reverse: dropped / dropped;
  - bare `Silencer`: dropped / dropped;
  - `Gerber tactical` + `knife for combat` (spanning): dropped / dropped;
  - the Arabic silencer + generator title: dropped / kept; the Arabic silencer title + exhaust snippet: dropped / dropped.
- The L1 query surface is one field; the L1 narrow/widen maps are unchanged.

**The exemption table: the R13c/R14b floor** (token -> qualifier -> justification):

| token | qualifier | justification |
|---|---|---|
| EN `silencer` | `exhaust` | measured: `Bosch exhaust silencer vs Walker silencer` (C:other:06), `car exhaust silencer` |
| | `generator` | measured: `Honda generator silencer box` |
| | `bosch` | R13c context word; measured in C:other:06 |
| | `walker` | R13c context word; measured in C:other:06 |
| | `hilux` | measured: `Toyota Hilux silencer vs Land Cruiser silencer` |
| | `car` | R13c context word |
| | `muffler` | R13c context word |
| EN `tactical knife` | `gerber` | measured: `Tactical knife Gerber vs Victorinox Swiss knife` (C:other:37), `Gerber tactical knife vs Leatherman Wave` |
| | `victorinox` | measured EDC brand (C:other:37) |
| | `leatherman` | measured EDC brand (`... vs Leatherman Wave`) |
| AR bunduqiya (rifle) | maa (water) | measured: bunduqiya maa lil-atfal (water gun) |
| | nerf | measured: bunduqiya nerf (`Nerf vs water gun`) |
| | hawaa (air) | measured: bunduqiya hawaa daght (air rifle) |
| AR katim sawt (silencer) | aadim (exhaust) | measured: katim sawt aadim al-sayyara Bosch vs Walker |
| | muwallid (generator) | measured: katim sawt muwallid Honda |
| AR sikkin qitali (combat knife) | jarbar (Gerber) | measured: sikkin qitali Gerber vs Victorinox |
| AR afyun, hamza spelling as in v1 (opium) | atr (perfume) | R13c context word |
| | utur (perfumes) | R13c context word |
| | san loran (Saint Laurent) | measured: afyun if san loran (YSL Opium, Arabic) |
| | blak (black) | measured: blak afyun (Black Opium) |
| | `ysl` | R13c context word |
| | `yves saint laurent` | R13c context word; subsumed by `saint laurent` (a drop is caught only by the exact-table pin) |
| | `saint laurent` | R13c context word |

- No other token has exemptions. A brand outside the floor exempts nothing (pinned blocked in both states): `Honda silencer`, `Yamaha silencer`, `Spyderco tactical knife`, and the Arabic Bosch beside katim sawt.
- R14b pins: `Walker silencer`, `car silencer`, `silencer muffler`, `Bosch silencer`, and the hamza-spelled atr+afyun, utur+afyun and afyun+san loran are BLOCKED under v1 and ALLOWED under v2. Bare hamza afyun and bare `silencer` are BLOCKED in both states.

**Stated limit: the allowed set is OPEN over co-occurrence (R13d).** Under v2, ANY query that pairs an exempted token with one of its qualifiers is allowed, intent wording included. Measured examples, pinned blocked OFF and allowed ON:
- `glock 17 exhaust silencer`
- `buy silencer hilux`
- `exhaust silencer for sale`
- `tactical knife gerber for combat`
- `car silencer for pistol`
- `buy walker silencer`
- AR buy-air-rifle, AR air-sniper-rifle, AR buy-opium-"black"
- AR silencer+rifle+air+exhaust (both tokens exempted)

A different v1 token still blocks: `exhaust silencer for glock 19` on `glock 19`, `exhaust silencer ammunition` on `ammunition`, `Gerber tactical knife vs switchblade` on `switchblade`. These are follow-up W4-8d material.

The same openness holds on `is_text_safe`. That function receives ONE caller-composed string: title + retailer / domain / product name at its 22 call sites, which this unit does not edit. It has no field boundary, so R16c cannot apply there. Measured and pinned: `is_text_safe("Silencer 9mm ships by car")` is False under v1 and True under v2.

**Measured collision EXAMPLES (the L1 narrow list):**
- Over the 413 committed strings: 17 keys (the silencer/tactical-knife/katim/sikkin/bunduqiya collisions, C:other:06, C:other:37, the 3 bare-hamza Arabic YSL Opium queries and the Arabic Black Opium string).
- Over all 562 probe strings: 63 keys (unchanged this round).
- Newly BLOCKED: 0 over the 562 (widen []).

**R14c: the alef spelling is a pre-existing gap, identical in both states.** v1's drug list carries only the hamza afyun, so the bare-alef spelling (and bare-alef + san loran) is ALLOWED under v1 AND v2 (pinned as the measured fact). v1 stays byte-unchanged. Follow-up W4-8f.

**Measured ON:**
- L1 hashes OFF (= HEAD): whole map `8c8de712de00844c081901b4e1afc628ef5200bfd1ca7b89629bf5d2ea144627`, C: subset `3885d2701484167362f2241faa3b50b965b04c1771d149946764ae26d0238a07`.
- L1 hashes ON: `5d07f87dae48b98bd5c847b42d61c8d82bfdbd9ac7a9b4cd71841d9df04292bc` / `763af6f7...`.
- Corpus L1 delta: C:other:06 and C:other:37.
- Every adversary r1/r2 intent phrasing is BLOCKED in both states with an identical verdict and match. So is every bare exempted token alone.
- L2: 521 `_proof` titles, 0 unsafe OFF and ON (is_text_safe and filter_shopping_items).

### Stated limits

- **Grams never veto (R13a/R14a):** a gram-denominated tablet dose with no other pharmacy signal stays electronics under A: `tablet 1.5g`, `tablet 0.5 g`, `Metformin 1g tablets`, `Metformin 0.5g tablets` (`metformin` is not a pharmacy token, measured), `Aspirin 2.4g tablets`, `Dextrose 4g tablets`, `4g tablets`. `Glucose 4g tablets` is caught by the `glucose` token. Follow-up W4-8e.
- **Car-brand model years (R16b, W4-8g, NO carve-out):** a model year before the MG brand reads as a milligram dose. `2023 MG ZS tablet holder` and `tablet mount for 2021 MG HS` are electronics OFF and supplements ON, pinned in both states. `2024 MG4 ...` and the ML350 / `ML 350` forms are electronics, because R16a treats a unit followed by a digit as a model code.
- **A dose followed by a number (a measured consequence of R16a):** `200mg 24 tablets` does not veto on the dose rung. With no pharmacy token and a count under 30 the string stays electronics, which is the flag-OFF verdict: `Nurofen 200mg 24 tablets`, `Ferrous sulfate 65mg 28 tablets`, `Thyroxine 50mcg 28 tablets`, pinned. Pharmacy-token, >= 30 and pack-word forms still veto.
- **A leading-dot dose:** `Tablet .5mg` reads electronics (R15a).
- **R10 rules as ruled:** pack-count or N >= 30 vetoes even in device-ish text; so does an `ml`/`iu` unit or a pharmacy token anywhere (`Fire HD 10 Kids 2 tablets pack`, `32 tablets`, `lenovo tablets 64 tabs open`, `Tablet 4 ml`, `tablet dose tracker app`, `iPad tablet for pharmacy POS`). All are pinned verbatim.
- **R5:** brand-only pharmacy strings (`Dulcolax tablets`, `Imodium tablets vs Motilium tablets`, `Beechams Max Strength tablets`) stay electronics. Pinned.
- **R3 EN parity gap:** EN `buy opium` and `hunting rifle` stay ALLOWED in both states, as at HEAD. Their AR twins stay blocked. Follow-up W4-8d.
- **Half B:** co-occurrence (above, including `is_text_safe`) and the alef gap (W4-8f).
- The specs cache is not keyed on category (see Canary).
- The corpus is the review lane's authored set, not traffic.
- `scripts/verify_flag_byte_identity.py` is blind to this unit, so identity is proven by the corpus-records gate.
- The camera path (`image_routes.py:390`) sends no chip.

### Client

No request or response key changes. With A ON, values change: `metadata.category_used` (electronics -> supplements/other) and `category_switched` (True -> False for a pharmacy pair with a Supplements chip). The value-only renders on phones are the Home smart-pick pill (`home_routes.py:497`) and `HistoryScreen` `item.category`. With B ON, phones get `CONTENT_UNAVAILABLE` on fewer queries.

### Gates (all through the bounded runner, qaren_netguard plugin)

- **Unit files** (575 + 557 + 29 = 1161 nodes): 1161 passed in each of unset / A / B / both; netguard 0.
- **Mutation matrix** on the final bytes, from byte snapshots with sha-verified restores: 262 rows.
  - Sources: the fix-r5 table, adversary r5's and r6's rows, and the new R15/R16 rows.
  - Totals: 237 apply, 231 killed, 6 equivalent. The equivalents are the count-before-dose order; v2 extends/ignores/AR-only overrides when v2 == v1; `.lower()` on qualifiers under IGNORECASE; and the R16c no-qualifier fast path, which is an optimisation.
  - 25 are N/A because R14a deleted their targets.
  - Kills: lookbehind without `.,` 2 (the X1.500mg / X2,500mg rows); decimal group removed 3 (tablet 1.5mg); digit exclusion removed 8 (ML350, ML 350, MG4); digit exclusion without the space form 5; single-space only 1; ASCII-space only 2.
  - Kills, R16c: the per-field check collapsed to the joined surface 7 (the `Silencer 9mm` + `ships by car` row); no spanning check 3.
- **Flag-OFF equality:** base 04acb757 == head unset == 'false' == B-on == base2, record by record. All equal the committed fixture (`b76fcef9...`, all-strings `cac3460c...`).
- **CI-order set,** 32 files, one process per state: 2096 passed x4.
- **Comm set,** 104 files at HEAD, in chunks of at most 25: only the 3 guard-caused SSRF nodes fail; `comm -13` against the committed base-failed file is empty.
- ruff E9/F63/F7/F82 clean; py_compile and json.load OK.
- `git diff --stat -- app/` touches only the three files below; CRLF kept.

### Follow-ups

- **W4-8b:** the resolved category in the specs cache key.
- **W4-8c:** Arabic category tokens (`ENABLE_ARABIC_CATEGORY_TOKENS`).
- **W4-8d (DECISIONS_AHMED):** EN intent phrases v3; whether the co-occurrence exemption needs an intent-word guard; and whether the `is_text_safe` call sites should pass fields so R16c can reach them.
- **W4-8e:** gram-denominated tablet doses (integer or decimal) followed or preceded by a pharmacy signal; also a dose followed by a pack number (`200mg 24 tablets`).
- **W4-8f:** alef/hamza normalisation in the blocklist matcher, with the AR drug list audited for other spelling variants.
- **W4-8g:** car-accessory listings that name the MG or ML brands beside a number.
- **PO-CATEGORIES-I18N-09b:** bare AR handgun blocks massage/glue/caulk/heat/water guns.

### Canary

- Use `nocache=true` or never-seen pairs. A rollback leaves supplements-schema specs cached for up to 7 d (L1) / 30 d (L2).
- **A:** watch the `metadata.category_used` distribution for queries containing `tablet`, the price `source_method` mix (bolo/nasser/iHerb) and the A2b call count. For the first window, add the MG / ML car-brand strings (`MG ZS`, `MG HS`, `MG5`, `ML350`, a model year + `MG`) to the canary list (W4-8g).
- **B:** watch the `CONTENT_UNAVAILABLE` rate. Audit every newly-allowed query that contains an exempted token plus intent wording (buy/sell/for sale/a weapon brand), and the L2 `dropped N/M` INFO lines. Those go to W4-8d.

### Activation

Flip A alone first, then B alone in its own window. No migration, no OTA, and no Railway variable beyond the two flags.

### Files

- `app/services/extraction_service.py`: reader, veto, dose/count patterns.
- `app/services/content_safety_service.py`: reader, per-call select, exemption matcher, per-field L2 exemption.
- `app/data/content_blocklist.json`: `v2` + `exempt`, version 2.
- `tests/test_category_token_fix.py` (new).
- `tests/test_content_blocklist_arabic_parity.py` (new).
- `tests/fixtures/category_corpus_gcc_360.json` + `category_corpus_gcc_360_head_records.json` (new).
- `tests/test_blocklist_collision_audit.py` is unchanged from base (R13e).

### Orchestrator addendum (Fable, ship time 2026-09-27)
- **Pipeline (seven fix rounds, seven adversaries):** the killed session-68 green resumed under the bounded harness (a mutant left on disk by the killed run was found by sha and restored first) -> adversary r1 DEFECTIVE -> fix r2 -> adversary r2 DEFECTIVE on the SAME two classes (device tablets to supplements through the dose rung; a blocklist v2 that dropped tokens) -> Fable design rulings R10-R12 (a rebuilt dose rung; v2 lists = v1 verbatim + a per-token exemption map) -> fix r3 -> adversary r3 DEFECTIVE a third time on decimal Wi-Fi bands -> Fable R13 (**grams never veto**) -> fix r4 (started before R13; a `< 2.0 g` bound) -> adversary r4 DEFECTIVE on R13 -> Fable R14 (R13 restated with every probe string, the micro-sign units, the qualifier floor in the hamza spelling, the bare-alef pins withdrawn) -> fix r5 -> adversary r5 SOUND (2 minors) -> adversary r6 SOUND (4 minors) -> Fable R15/R16 (the dose lookbehind excludes separators; a unit followed by a digit is a model code; the MG-brand-plus-year stated limit; the L2 exemption decided per field) -> fix r7 -> adversary r7 SOUND (5 pin gaps). Every adversary left the worktree byte-identical to the fixer's reported shas. Rulings: `.qa-s68/RULINGS_W4_8*.md` (archived in the session state folder).
- **Adversary r7's pin gaps closed by the orchestrator (test rows only, no app change):** `tests/test_content_blocklist_arabic_parity.py::R16C_L2_ROWS` gained `("Gerber tactical knife", "in stock")` and `("Gerber Tactical Knife", "")` (an exempted multi-word token that ENDS the title does not span into the snippet - mutants A7_junction_off_by_one / A7_spanning_end_ge now redden, 2 failed each) and `("Accessories", "Bosch exhaust silencer")` / `("Spare part", "Honda generator silencer box")` (the token and its qualifier both in the snippet exempt it there - A7_fastpath_title_only reddens, 2 failed); `tests/test_category_token_fix.py::DEVICE_GUARDS` gained `"2012 ML  350 tablet mount"` and the tab form (any whitespace between a unit and the model digits - A7_lookahead_digit_single_space reddens, 1 failed). Every restore sha-verified; the three unit files: 1173 passed in each of the four states, `[netguard] blocked 0`.
- **Ruling conflict resolved (R17, ratified here):** R16a (a unit followed by a digit is a model code) and R16b (the MG-brand-plus-year stated limit) disagreed on `2024 MG4 tablet screen protector`; the fixer resolved it toward R16a (MG4 -> electronics under A, pinned as a device guard) and that is ratified - the R16b stated limit is exactly the two strings `2023 MG ZS tablet holder` and `tablet mount for 2021 MG HS` (follow-up W4-8g).
- **Stated limit added (adversary r7):** `is_text_safe` receives ONE caller-composed string at its 22 call sites (title + retailer / domain / the USER's product name), so under `ENABLE_BLOCKLIST_PRECISION_V2` a qualifier carried by the user's own query (`car silencer`, `Bosch exhaust silencer`) exempts every listing title on those adapters that carries the same token - the R16c per-field class on that surface, with the user query as the other field. Recorded as follow-up W4-8h (compose the check per field at those call sites); the L2 `filter_shopping_items` surface is per-field since R16c.
- **Post-rebase ship checks** (onto main `8a1e0d55`, which carries W4-11 in `extraction_service.py` in different functions): the three unit files and the 32-file CI-order set in ONE process per state (unset / A / B / both), the netguard ratchet, ruff E9,F63,F7,F82, py_compile and `json.load` - results in the PR's first comment if they differ from the fixer's numbers above.
- **Flags on main after this merge (default OFF, read per call):** `ENABLE_CATEGORY_TOKEN_FIX`, `ENABLE_BLOCKLIST_PRECISION_V2`. Nothing is flipped; Railway and Supabase untouched. Ahmed's product call before the v2 flip: the EN weapon-intent phrasings that carry a qualifier are ALLOWED by design (W4-8d/e).

- **Post-rebase ship checks, measured (main `8a1e0d55`):** the three unit files 1173 passed in each of the four states; the 32-file CI-order set green in ONE process per state (status OK, all four); ruff / py_compile / `json.load` clean; `git diff --stat -- app/` = the three files (274+/6-). The subset netguard ratchet flagged ONE node as a new egress attempt, `tests/test_flush_live_price_key.py::test_flag_on_matches_the_live_writer_on_a_present_but_empty_search_query` (`curl_cffi` to footlocker.com.bh `configs.json`, blocked by the guard) - re-measured ALONE at BASE `8a1e0d55` in a detached scratch worktree: the same attempt, so it is pre-existing and order-dependent (the full CI order does not show it - #223's CI ratchet was OK with this file present), not this unit's; noted on #211 (the egress-node campaign).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
