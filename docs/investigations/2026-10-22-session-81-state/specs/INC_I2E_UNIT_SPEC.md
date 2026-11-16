# INC-I2e GUARD-SHORT-LINE: unit spec (S96 main lane, 2026-11-16)

Orchestrator: S96 (Claude Opus 5.5, claude-opus-5-5). Base: origin/main b0ad260363e0cf0074e4ee596b140d073466e92a (holds INC-I1 #407, INC-R1 #410). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s96-i2e, branch fix/inc-i2e-guard-short-line. Class: SAFE by LC-1 (no FOCUS surface: a dark data-pipeline guard change, backend only) -> LC-8 (this spec is the orchestrator's own review), ONE adversary after GREEN. Seed: FINDINGS_AND_FIX_PLAN_2026-11-15.md section 4 INC-I2 part (e) and T2_pictures.md T2-06 / V2 (T2-06 CONFIRMED).

## 1. The defect (measured at b0ad2603 by git plumbing; re-measure the line numbers)

`app/services/image_relevance.py`:
- `_line_tokens` (about :331-345) drops every token shorter than 2 characters, every stop / concentration / fragrance / unit word, a size token, a number before a unit and the brand's own forms.
- `check` (about :378-398), brand known: `if not (ident.name_tokens & t): return "name"`. When `name_tokens` is EMPTY this refuses EVERY candidate.
- Lines with no significant token once the brand is known: `Y` (Yves Saint Laurent), `M` (Ted Baker), `L'Eau d'Issey` (Issey Miyake: l, eau, d, issey -> all dropped), `N°5` / `Nº5` / `No.5` (Chanel: `N°5` normalizes to `n`, `5`, both dropped; `No 5` keeps only `no`, which never matches a `N°5` title).
- Joined spellings fail both ways: line `J'adore` (tokens j, adore) never matches a title `Jadore`; line `Light Blue` never matches `Lightblue`, and the reverse.
- Who passes a split brand + line today: the q= parser path (brand and name split by the parser) -> ALREADY live in production with ENABLE_IMAGE_RELEVANCE_GUARD ON. The INC-R1 resolver (`product_resolver.apply_resolution`: brand = the house, name = the line) will put every typed explicit pair on this path once ENABLE_PRODUCT_RESOLVER is ON: then `YSL Y`, `Ted Baker M`, `L'Eau d'Issey`, `Chanel N°5` lose every picture. This unit must merge and be switched on before the resolver window.
- `structured_comparison_service.py` passes `relevance_kwargs(brand, name, category, partial_slot, is_vision)` (find it by text: `_image_relevance.relevance_kwargs(`), so `line` = the product name.

## 2. The contract (flag ENABLE_IMAGE_GUARD_SHORT_LINE, default OFF, the house idiom, read PER CALL inside `check`)

New module constant `SHORT_LINE_FLAG_ENV = "ENABLE_IMAGE_GUARD_SHORT_LINE"` and `short_line_enabled() -> bool` (same truthy set `_TRUTHY`, `os.getenv(..., "false").strip().lower()`). It has an effect only where `check` runs, i.e. only with ENABLE_IMAGE_RELEVANCE_GUARD ON (`relevance_kwargs` returns {} when that is OFF; unchanged). Camera products, the KB-served image branch and the piggyback `accept_scheme` never reach `check`: unchanged.

OFF: `check` returns exactly what it returns at base for every input (byte-identical behaviour); `relevance_kwargs`, `RelevanceCall`, the `[IMG_RELEVANCE]` line, `image_query`, `REASONS`, `TIERS`, `OUTCOMES` unchanged. The new flag is not read when the guard is OFF.

ON, definitions (all pure, total, built with `_cg.normalize`; image_relevance.py stays a LEAF: no new module-level import, no logger, no I/O):

- NUMERO FOLD `fold_numero(tokens)`: walking the folded token list, a token in {"n", "no", "nr"} directly followed by an all-digit token becomes the ONE token "no"+digits (the digit token is consumed); a single token matching `n(?:o|r)?[0-9]+` becomes "no"+digits; every other token is kept. So `N°5`, `Nº5`, `No.5`, `No 5`, `No5`, `N5` all give `no5`; `No 19` gives `no19`. Applied to the line and to every candidate text when ON.
- LINE KEYS of the identity (the line = `relevance["line"]`, else the product name, as today), computed from the folded line tokens AFTER the numero fold:
  - `sig2`: the significant tokens by today's `_line_tokens` rules applied to the folded list (length >= 2, not in NAME_EXCLUDE, not a brand form, not a size token, not a number directly before a unit word).
  - `short2`: the single-character tokens of the folded list that are a letter or a digit, are not a number directly before a unit word, and are not an elision letter (ELISION = {"l", "d", "j", "s", "c", "n", "m"} EXCEPT that a one-letter token which is the WHOLE line after removing brand forms, stop / concentration / fragrance / unit words is always kept: so `M` for Ted Baker and `Y` for YSL are kept, the `l` and `d` of `L'Eau d'Issey` are not).
  - `joins2`: the concatenation of each ADJACENT pair of folded line tokens where neither member is a brand form, neither is a size token or a number before a unit, and NOT both members are in NAME_EXCLUDE. So `J'adore` -> {"jadore"}; `L'Eau d'Issey` (brand Issey Miyake) -> {"leau"} ("eaud": both... `d` is not in NAME_EXCLUDE, so "eaud" IS a join: allowed, harmless; "dissey" is NOT: issey is a brand form); `Light Blue` -> {"lightblue"}; `Eau de Parfum` -> none.
- CANDIDATE KEYS of one `check` call: `t2` = for EACH text separately, its folded tokens after the numero fold PLUS the concatenation of each adjacent pair of those tokens (never joined across two texts); the union over the texts. Host tokens and `fragrance_texts` are read exactly as today.

ON, the test (the FIRST failing reason is returned, as today):
1. Brand known (`not ident.brand_empty`): the brand test is today's, unchanged (`brand`). Then:
   a. `sig2` non-empty: pass iff `(sig2 | joins2) & t2` is non-empty, else `name`.
   b. `sig2` empty, `short2` non-empty: pass iff `short2 <= t2` (each as a standalone token) or `joins2 & t2`, else `name`.
   c. `sig2` and `short2` empty, `joins2 & t2` non-empty: pass.
   d. otherwise (nothing of the line to match: `Eau de Parfum`, a line equal to the brand, a blank line): when `ident.needs_fragrance_word` (fragrances / other / empty category) pass iff `FRAGRANCE_WORDS & (t2 | _text_tokens(fragrance_texts))`, else `fragrance_word`; any other category -> `name` (as today).
2. Brand empty: every member of `sig2` must be COVERED (it is in `t2`, or it is a member of a pair whose join is in `joins2 & t2`); `sig2` empty and `short2` non-empty: `short2 <= t2`; both empty: `name`. A failure -> `name`. Then today's fragrance-word rule (on `t2`).

Implementation latitude: the line keys may live as NEW fields at the END of the frozen `Identity` with defaults (frozenset()), filled always by `identity()` and READ only when the flag is ON, PROVIDED the RED agent measures that no test compares an `Identity` by equality or constructs one positionally in a way the new fields break; otherwise a separate frozen dataclass built once per `RelevanceCall` and an optional keyword on `check`. GREEN may not change any public signature's existing parameters.

Stated limits (accepted by this spec): a one-letter line (`Y`, `M`) accepts a flanker title that carries the letter (`YSL Y Le Parfum`), as every line already accepts its flankers; a stray standalone letter in a title with the right brand can pass; `L'Eau d'Issey` accepts other `L'Eau ...` lines of the same house; the empty-brand path becomes STRICTER for numbered lines (typed `Chanel N°5` now needs `no5`, so a `Chanel No 19` picture is refused where the base accepted it). No new log key: the `[IMG_RELEVANCE]` line keeps its closed vocabulary.

## 3. Prototype change list (RED proves it in place; GREEN implements)
1. `app/services/image_relevance.py`: the flag constant and reader; `fold_numero`; the line-key builder; the candidate-key builder; `check` branches on the flag (OFF path textually the base code, untouched); module docstring paragraph for the flag.
2. `CLAUDE.md`: (a) after the `ENABLE_PRODUCT_RESOLVER` sentence of the **Feature Flags** paragraph add one sentence naming `ENABLE_IMAGE_GUARD_SHORT_LINE` (INC-I2e GUARD-SHORT-LINE, default OFF, read per call) and pointing at its block; (b) a new block `### INCIDENT LANE unit (INC-I2e GUARD-SHORT-LINE, S96 main lane, 2026-11-16)` placed directly after the INC-R1 block: the flag row (effect ON, OFF byte-identical, the mixes of section 4), the stated limits, owner steps (the orchestrator flips it on web in its own window BEFORE the ENABLE_PRODUCT_RESOLVER window; rollback = unset). Respect every CLAUDE.md reader pin (find them by the import graph and by grep for "CLAUDE.md" under tests/).
3. `.github/black-clean-paths.txt`: add the new RED test file only if it is black-clean (measure with the venv's black; never reformat other files).
No other file. No change to `structured_comparison_service.py`, `image_service.py`, `product_resolver.py`.

## 4. The flag-mix walk (each row is a test or a reasoned read; ON/OFF of G = ENABLE_IMAGE_RELEVANCE_GUARD, S = ENABLE_IMAGE_GUARD_SHORT_LINE, R = ENABLE_PRODUCT_RESOLVER)
| G | S | R | behaviour |
|---|---|---|---|
| OFF | any | any | no guard; `relevance_kwargs` -> {}; S never read (test: a getenv recorder sees no S read on the guard-OFF path of `relevance_kwargs` and `get_product_image_url`'s base call) |
| ON | OFF | OFF | base INC-I1 (production today): typed pairs reach the empty-brand path; the q= path already refuses short lines |
| ON | OFF | ON | the hazard: resolver lines Y / M / N°5 / L'Eau d'Issey refused at every tier (a PIN row documents it at base) |
| ON | ON | OFF | typed path: empty-brand rule 2 (numero fold, joins; stricter for numbered lines); q= path: rule 1 |
| ON | ON | ON | resolver lines pass by rule 1 |
Also: the KB-served image branch and camera products never call `check` (unchanged, cite the line); the llm_pick tier with no related organic item calls `check(ident, (), ())` -> `brand` (unchanged under S ON: rule 1 starts with the brand test).

## 5. Rows of the RED file tests/test_inc_i2e_guard_short_line.py (pure ASCII; build `°` `º` with chr(); synthetic but realistic titles; flags via monkeypatch.setenv / delenv per test; missing symbols through getattr helpers so every RED row fails on an AssertionError)
- E1 YSL Y (brand "Yves Saint Laurent", line "Y", fragrances): S ON -> "Yves Saint Laurent Y Eau de Parfum 100ml" accepted; "YSL Y EDP" accepted; "Yves Saint Laurent Libre Eau de Parfum" -> "name".
- E2 Ted Baker M: "Ted Baker M Eau de Toilette 100 ml" accepted; "Ted Baker Woman Eau de Toilette" -> "name".
- E3 L'Eau d'Issey (brand "Issey Miyake"): "Issey Miyake L'Eau d'Issey Eau de Toilette" accepted; "Issey Miyake Nuit d'Issey Eau de Parfum" -> "name".
- E4 Chanel N°5 (lines "N°5", "No 5", "Nº5" each): titles "CHANEL N°5 Eau de Parfum", "Chanel No.5 EDP", "Chanel N5 Parfum" accepted; "Chanel No 19 Eau de Parfum" -> "name".
- E5 joined: brand "Dior" line "J'adore" vs "Dior Jadore Eau de Parfum" accepted; brand "Dolce & Gabbana" line "Light Blue" vs "Dolce Gabbana Lightblue EDT" accepted; line "Lightblue" vs "Dolce & Gabbana Light Blue Eau de Toilette" accepted.
- E6 nothing to match (brand "Chanel", line "Eau de Parfum", fragrances): "Chanel Eau de Parfum 100ml" accepted; "Chanel Coco handbag" -> "fragrance_word"; category "electronics" -> "name".
- E7 empty brand (the typed path, brand ""): line "Chanel N°5" vs "CHANEL N°5 Eau de Parfum" accepted and vs "Chanel No 19 Eau de Parfum" -> "name" (the stricter change); line "Dior Jadore" vs "Dior J'adore Eau de Parfum" accepted.
- E8 end to end through `RelevanceCall` + `image_service.get_product_image_url` with a fake Serper Images payload (the INC-I1 test file's own fakes are the model; no network): relevance {brand "Ted Baker", line "M", fragrances, slot 0} with S ON returns the matching image URL and the summary reads accepted / serper_images; S OFF returns None with reason name.
- E9 the per-call read: one test flips S between two `check` calls on the same identity and sees both answers.
- P1 OFF golden: every E1-E7 case with S unset AND with S "false" returns the BASE reason, recorded at base as literals in the file (so OFF = base).
- P2 the hazard documented: G ON, S OFF, the E1-E4 resolver-shaped identities refuse every listed title (`name`).
- P3 guard OFF: `relevance_kwargs(...)` == {} and S is never read (a getenv recorder) for G unset / false with S true.
- P4 leaf: image_relevance.py module-level imports unchanged (AST read).

## 6. Mutants (on the prototype, the RED file alone each time)
M1 drop the numero fold of candidate texts; M2 drop the numero fold of the line; M3 `short2` keeps elision letters (L'Eau d'Issey then needs `l`/`d`); M4 rule 1b uses `&` instead of `<=`; M5 candidate pair joins across two texts; M6 `joins2` keeps brand-form members ("dissey" -> E3's Nuit row must catch it); M7 rule 1d ignores the category (electronics passes); M8 the flag read once at import; M9 the OFF path reads the new keys (P1 must catch it).

## 7. Stay-green and gates
Stay-green (run at base AND at the prototype, whole files): tests/test_inc_i1_picture_must_match.py, tests/test_inc_i1_noon_and_wiring.py, every tests/test_inc_r1_*.py, every test file naming image_service / get_product_image_url / image_relevance / relevance_kwargs, and the CLAUDE.md readers. The comm set by the union rule of s81-common.txt (module + symbol reference grep for image_relevance, check, identity, Identity, RelevanceCall, relevance_kwargs, get_product_image_url; UNION the source-scanning pins; UNION the CLAUDE.md readers by the import graph); base record cached per LC-6. The fourteen client jest fences that read repo files run at GREEN because CLAUDE.md changes (SmartCompareApp/node_modules is a junction: run jest by path with the existing install; never a package manager). black on image_relevance.py (listed in .github/black-clean-paths.txt) and ruff as CI runs them.

## 8. Proof (for the PR body and the flip note)
Merged, not proven. Phone: with G ON, R ON and S ON, typed `YSL Y` vs `Ted Baker M` and `Chanel N°5` vs `Dior J'adore` show both bottles. Log: `RESOLVE` line with line_a=Y; `IMG_RELEVANCE product=0 ... outcome=accepted` for both slots; the count of `outcome=rejected` with `reason=name` falls after the S window.
