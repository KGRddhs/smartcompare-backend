## INC-I2e GUARD-SHORT-LINE (dark `ENABLE_IMAGE_GUARD_SHORT_LINE`)

**What.** The INC-I1 picture guard (`app/services/image_relevance.py::check`, on in production through `ENABLE_IMAGE_RELEVANCE_GUARD`) refuses EVERY candidate when the brand is known and its line has no significant token: `Y` (Yves Saint Laurent), `M` (Ted Baker), `L'Eau d'Issey`, `N°5` / `Nº5` / `No.5` (Chanel). It also fails joined spellings (`J'adore` against `Jadore`, `Light Blue` against `Lightblue`). INC-R1 (#410, dark `ENABLE_PRODUCT_RESOLVER`) sets brand = the house and name = the line on every resolved typed pair, so with the resolver on these perfumes would lose their picture at every tier. This unit must be switched on before the resolver window.

**How (ON).** Both sides fold the numero forms (`N 5` with the degree sign or the ordinal, `No.5`, `No 5`, `N5` -> `no5`). A candidate text adds its own adjacent-pair joins, never across two texts.
- **Brand known** (the brand test is unchanged):
  - a line with significant tokens passes on one of them or one of its joins;
  - a line with none passes on every one-character token or on a join. An elision letter counts only when it is the whole line (`Y`, `M`). `J'adore` joins to `jadore` and `L'Eau d'Issey` to `leau`; a join never includes a brand form;
  - a line with nothing to match falls to the fragrance word (fragrances, other), otherwise `name`.
- **Brand empty** (the typed path): every significant token must be covered by a token or a join, then the fragrance word.

**OFF.** `check` is the base code byte for byte. `relevance_kwargs`, `RelevanceCall`, the `[IMG_RELEVANCE]` line and its closed vocabulary are unchanged. The new flag is read per call inside `check` only, so it is never read while the guard is off.

**Files (4).** `app/services/image_relevance.py` (+159), `CLAUDE.md` (the Feature Flags sentence and the new INC-I2e block), `.github/black-clean-paths.txt` (+1), `tests/test_inc_i2e_guard_short_line.py` (new, 20 tests).

### Input paths (measured at b0ad2603)
- **The phone:** the app's only compare caller is Home (`HomeScreen.tsx:458`, `streamComparison` with `{product_a, product_b}`; `compareTextPair` has no screen caller). So every phone compare today is an explicit pair with brand `""` and uses the empty-brand rule.
- **The brand-known rule** is reached today only by `q=` API callers. Once `ENABLE_PRODUCT_RESOLVER` is ON, every resolved typed pair reaches it too.
- **Never reach `check`:** camera products (`relevance_kwargs` returns `{}`), the KB-served image branch, the piggyback `accept_scheme`, and links.

### Flag-mix walk (G = ENABLE_IMAGE_RELEVANCE_GUARD, S = this flag, R = ENABLE_PRODUCT_RESOLVER)
| G | S | R | behaviour |
|---|---|---|---|
| OFF | any | any | no guard; S never read (P3) |
| ON | OFF | OFF | production today, byte-identical (P1; the adversary's 426-row probe: head == base) |
| ON | OFF | ON | THE HAZARD: resolver lines Y / M / N(deg)5 / L'Eau d'Issey refused at every tier (pinned by P2). Do not open R before S |
| ON | ON | OFF | typed pairs use the empty-brand rule: numero fold and joins (typed `Chanel No 5` now matches `CHANEL N(deg)5` titles), stricter for numbered lines |
| ON | ON | ON | resolver lines pass. Every brand-known right title in the probe for Y, M, N(deg)5, J'adore, Light Blue and L'Eau d'Issey moves from refused to accepted |

### Gates
- **RED** (wf_da54c2e2-e43, one Opus 5.5 agent): rows E1-E9 fail at base on assertions; P1 (x5), P2 (x2), P3 (x3) and P4 pass. The prototype passes 20 of 20. Mutants M1-M9 are killed. The restore of the base files is proven.
- **GREEN** (wf_7216e401-137): commit c070d136. The RED file is unchanged (sha 38090ba9) and passes 20 of 20 with S unset and with S true.
- **Comm set:** 206 files by the union rule (set sha 84667417). The 22 failing nodes equal the cached base record at b0ad2603: no new failure.
- **Lint and hook:** black 26.5.1 and the CI ruff tier are clean, and the pre-commit hook ran (never `--no-verify`).
- **Jest:** the client fences (18 files) and the full suite (4,072 tests) fail only the 4 accepted nativeBundle.w37 drift nodes.
- **ONE ADVERSARY** (SAFE by LC-1): **SOUND**. Its findings F-1..F-5 are MINOR and become stated limits L-8..L-12 below.

### Stated limits
- L-1 a one-letter line (`Y`, `M`) accepts a flanker title that carries the letter (`YSL Y Le Parfum`), as every line accepts its flankers.
- L-2 a stray standalone letter in a title with the right brand can pass a one-letter line.
- L-3 `L'Eau d'Issey` accepts other `L'Eau ...` lines of the same house (and `Eau d'Issey`).
- L-4 the empty-brand path is stricter for numbered lines. Typed `Chanel N(deg)5` refuses `No 19`, and also `Number 5` or `#5` spellings, which the fold does not cover (F-2).
- L-5 the whole-line drop set omits `spray` (a line `M Spray` loses its M).
- L-6 a typed alias brand with the resolver OFF (typed `YSL Y`) still needs the token `ysl` in the title; only the resolver window fixes that.
- L-7 two adjacent title tokens may join into a line token by chance (`s` + `i` -> `si`).
- L-8 (F-1) brand known, with a line that has nothing to match (`Eau de Parfum`, or the brand alone): any picture of the house that carries a fragrance word passes. Today only `q=` callers reach this; the resolver always supplies a line.
- L-9 (F-3) a one-character line that is a digit or a lone elision letter (`5`, Chloe `L'Eau` -> `l`) passes on a stray standalone token.
- L-10 (F-4) on the typed path, a one-letter token is ignored whenever the typed name has a significant token. So typed `YSL Y` or `Ted Baker M` with the resolver OFF accepts any picture of that house (as the base does). The phone proof therefore needs R ON.
- L-11 (F-5) a joined spelling that includes an alias brand form (`CKOne` for Calvin Klein `CK One`) is not matched on the brand-known path; the base refuses it too.
- L-12 no new log key: the canary reads the existing `IMG_RELEVANCE` reason mix.

### Owner steps (names only)
1. Merge on the orchestrator's dated word at 7 of 7.
2. The orchestrator sets `ENABLE_IMAGE_GUARD_SHORT_LINE=true` on web in its own window, BEFORE the `ENABLE_PRODUCT_RESOLVER` window. It has an effect only while `ENABLE_IMAGE_RELEVANCE_GUARD` is ON.
3. Rollback: unset it.
4. Canary: the share of `IMG_RELEVANCE` lines with `outcome=rejected` and `reason=name`. With R ON, a `RESOLVE` line with `line_a=Y` (or `M`) followed by `IMG_RELEVANCE ... outcome=accepted` for that slot.

### Proof on the phone (merged, NOT yet proven until then)
- **With S alone (LIKELY, it depends on the titles the search returns):** typed `Chanel No 5` vs `Dior Sauvage` shows the Chanel bottle.
- **With G, S and R all ON:** `YSL Y` vs `Ted Baker M`, then `Chanel N(deg)5` vs `Dior J'adore`, show both bottles. Each picture must be the named line, not another perfume of the house.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
