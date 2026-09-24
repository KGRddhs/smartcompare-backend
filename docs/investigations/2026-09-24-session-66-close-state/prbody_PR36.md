## Gents/Ladies wrong-gender price leak (extends PR #32), plus a strict-gender-wins fix

**Rescue of PR #36** (`feature/gents-ladies-gender-leak`, opened 2026-07-08, CI red on the old baseline). This branch carries the original commit rebased onto current main plus the fix its adversarial review demanded. Supersedes #36; close that one when this merges.

### Defect
The price-identity gate matched a fragrance "<X> Gents" against "<X> Ladies" as the same product. `_selection_match('Ajmal Aristocrat Gents', 'Ajmal Aristocrat Ladies', 'fragrances')` returned True on main with both gates on, so a men's query could be priced from the women's PDP. `gents` and `ladies` are in `_FRAGRANCE_PADDING_TOKENS`, which the subset check ignores. They were missing from the strict `_GENDER_*_TOKENS` sets and from `_pronoun_gender_of`, so the gender contradiction axis never fired for them. PR #32 fixed exactly this for him/her.

### Fix
1. `_pronoun_gender_of` now maps `gents -> men` and `ladies -> women`, beside him/her. It is the separate, flag-gated pronoun axis that feeds only the contradiction check (`_vd_gender_mismatch`, via `VariantDescriptor.gender_pronoun`). `_gender_of` stays strict, so the femme asymmetry and the empty-core/identity logic are unchanged. Tokens are word-level after `_fold_identity`: Gent's, Ladies', full-width Ｇｅｎｔｓ and upper case fold to the token, and Gentleman, Gentlemen, Gentsx and Sladies do not trigger it. A title carrying both genders ("Ladies & Gents", "for Him and Her") resolves to None, so it is ambiguous and never a contradiction.
2. **Strict gender wins** (found in adversarial review, one line in `_vd_gender_mismatch`). The pronoun gender is consulted only when the strict gender is None: `g = d.gender or d.gender_pronoun`, on both sides. The PR #32 helper treated "strict gender + opposite catalogue word" as ambiguous. With gents/ladies added, that opened a new leak: 'Versace Eros Pour Homme' vs 'Versace Eros Pour Femme - Gents' and 'Dior Sauvage For Men' vs 'Dior Sauvage For Women Gents' passed selection and the backstop, and 'Eros Pour Femme' vs 'Eros Pour Homme Ladies' passed `backstop_identity_verdict`. All three are rejected again at both call sites (backstop -> `(False, 'not_exact:gender')`) and are pinned.

### Scope (wider than fragrances)
The contradiction axis runs for fragrances, makeup, skincare, haircare and fashion. Gents/Ladies therefore also reject in beauty and fashion: Casio Edifice Gents vs Ladies Watch, and Carolina Herrera 212 Men vs 212 Ladies in makeup. Both are pinned at both call sites, as is a same-gender fashion pair ("Gents" vs "Gent's", "Ladies" vs "Ladies'") that must still match. Every observed flip is an opposite-gender reject. The electronics title still extracts the pronoun, but the axis never reports gender there (pinned).

### Evidence
- `tests/test_gender_gents_ladies_leak.py` (44 nodes, autouse zero-network guard) and `tests/test_gender_contradiction_fix.py` (17, byte-unchanged): 61 passed, 0 failed.
- Neighbour set (12 descriptor/gender/variant files): 314 passed, 0 failed.
- ruff `E9,F63,F7,F82` and py_compile are clean. Pinned venv (fastapi 0.141.1, pydantic 2.13.4, pytest 9.1.1).
- Mutation matrix, 19 byte mutations of `price_service.py` by the fixer plus 7 by the round-2 adversary (26 total), each restored from a sha-verified snapshot. Every non-equivalent mutation reddens at least one node:
  - revert to the PR#32 helper: 6
  - pronoun wins over strict: 7
  - drop the both-stated requirement: 8
  - any both-stated pair counts as a mismatch: 3
  - both-words-returns-men: 4
  - skip `_fold_identity`: 3
  - substring instead of word tokens: 5
  - prefix matching: 2
  - widen the scope to every category: 1
  - drop the mismatch check at selection: 17
  - drop the gender check at the backstop: 7
  - drop gents: 13
  - drop ladies: 12
  - move the words into the strict sets: 15
  - remove the flag gate: 5
- One pin has no mutation power, and its name and comment say so: `test_no_regression_femme_query_vs_homme_ladies_rejected_at_selection`. The femme asymmetry already rejects that pair at selection on main. Its backstop twin carries the power.
- Flag-off byte-identity: head vs base modules loaded side by side, 640 rows x 6 functions per config. 0 differences in all four flag-off configs (flags unset / gate only / AXES on with gate off / AXES=false), against both the PR base 1c6f6796 and main 6ab9d7ea.
- Round-2 adversary: SOUND. Its one minor is a coverage gap, not a defect: only the CANDIDATE half of strict-gender-wins is pinned (a mutation that puts the QUERY side back on the old `_combined` helper survives all 60 nodes, while its candidate-side mirror reddens 6). The code is symmetric and correct on both sides; a query-side pin is a follow-up.

### Flag / environment state
- Gated by `variant_descriptor_axes_enabled()`: inert unless `ENABLE_EXACT_PRICE_GATE` and `ENABLE_VARIANT_DESCRIPTOR_AXES` are both true. Both are read per call.
- `ENABLE_EXACT_PRICE_GATE` **defaults ON in code** (`os.getenv(..., 'true')`; CLAUDE.md records it as on in prod). `ENABLE_VARIANT_DESCRIPTOR_AXES` defaults OFF. So **ENABLE_VARIANT_DESCRIPTOR_AXES is the only real switch**, and setting it alone activates the fix. Measured with the gate unset and AXES=1: the axes predicate is True and Gents vs Ladies is rejected.
- **Prod state is UNVERIFIED.** No Railway read was made and no env value was read. The earlier PR body said "ON in prod"; that rested on a 2026-08-17 note and is not confirmed. If AXES is unset in prod, both this fix and the leak it closes are dormant there.

### Honest limits
- A unisex product that two retailers label differently ("Oud Wood Gents" vs "Oud Wood Ladies") is now rejected. This is by design: stated genders are opposite.
- Arabic gender words (رجالي / نسائي) are still ignored. The tokenizer keeps [a-z0-9] only.
- A "For Women" query vs a "Ladies" candidate is still rejected by the strict femme asymmetry. This is unchanged and pinned.
- A title carrying both Her and Gents resolves to None and still matches.
- The 175-file comm gate was measured by the rebaser on the pre-fix branch; after the strict-wins fix only the two gender files and the 12-file neighbour set were re-run (the change is confined to `_vd_gender_mismatch`, reached only when `gender_pronoun` is non-None, and the flag-off probe proves identity).

### Post-rebase verification (main `7368f862`, 2026-09-24)
Rebased clean onto `7368f862` (W4-1 #173 edits `price_service.py` in other functions; no textual conflict) as `32141817` on top of the rebased original `a8e8c765`. On the pinned venv: the two gender files + the 12-file neighbour set + `test_shopping_currency_truth.py` gave 479 passed, 0 failed; ruff + py_compile clean.

### Follow-ups
- Read the real `ENABLE_VARIANT_DESCRIPTOR_AXES` state from Railway (names only) before relying on this fix in prod.
- Pin the QUERY half of strict-gender-wins (a contradictory pair with the stray opposite word on the query side).
- Arabic gender tokens for the pronoun axis (own unit, own pins).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
