# GATE INC-I2e GUARD-SHORT-LINE (S96 orchestrator, 2026-11-16 about 20:40 AST)

RED wf_da54c2e2-e43 (one Opus 5.5 agent, model verified, 277,529 tokens, 33 min) is ACCEPTED.
- RED file tests/test_inc_i2e_guard_short_line.py, sha256 38090ba9bee4365db463cea2d8bc41858dcf0da77b2b69cc0894fe874e4a4f45, 21,287 bytes, pure ASCII: FROZEN. GREEN never edits it.
- At base: E1-E9 fail on assertions; P1 (x5), P2 (x2), P3 (x3), P4 pass. At the prototype 20 of 20.
- Comm set 206 files (set sha256 84667417...), base record stored under harness/base_records/b0ad2603.../ (22 known failing nodes); the prototype equal to the base record. Mutants M1-M9 killed. Restore proven (both HEAD blobs).
- The orchestrator reviewed proto.diff (image_relevance.py and CLAUDE.md) against spec section 2: it is the contract.

## Rulings
- GC-1 (Q1 / D1): CONFIRMED. Rule 1c is "sig2 and short2 empty, joins2 non-empty: pass iff joins2 & t2, else name"; rule 1d only when all three are empty.
- GC-2 (D2-D5, D7, D8, D9): accepted. Q2: keep the spec's whole-line drop set (STOP | CONCENTRATION | FRAGRANCE | UNIT; no "spray"); a line "M Spray" losing its M is a stated limit (L-5 below), not a change.
- GC-3 (Q3): `zip(toks, toks[1:])` may become `zip(toks, toks[1:], strict=False)` or an index loop; the CI ruff tier (E9,F63,F7,F82) and black 26.5.1 on image_relevance.py are the bar.
- GC-4 GREEN implements exactly proto.diff (scratchpad s96/i2e/red/proto.diff) in image_relevance.py, plus these CLAUDE.md amendments to the prototype's INC-I2e block (no other CLAUDE.md change):
  (a) THE INPUT PATHS, measured by the orchestrator at b0ad2603: the app's only compare caller is Home (SmartCompareApp/src/screens/HomeScreen.tsx streamComparison with {product_a, product_b}; compareTextPair has no screen caller), so every phone compare today is an explicit pair with brand "" (the empty-brand rule 2). The brand-known rule 1 is reached today only by q= API callers (the parser splits brand and line; no app screen sends q=) and, once ENABLE_PRODUCT_RESOLVER is ON, by every resolved typed pair (apply_resolution: brand = the house, name = the line). Camera products never reach `check`.
  (b) What changes on the phone with the switch alone (resolver OFF): typed `Chanel No 5` (base needs the token `no`, which a `CHANEL N(deg)5` title lacks; ON both fold to `no5`), typed `Dior Jadore` against `J'adore` titles and `Light Blue` against `Lightblue` titles; and it becomes stricter for numbered lines (typed `Chanel N(deg)5` refuses a `No 19` picture the base accepted).
  (c) The stated limits L-1..L-6 below, one line each.
- GC-5 add tests/test_inc_i2e_guard_short_line.py to .github/black-clean-paths.txt (sorted position as the file orders it; read its header first).
- GC-6 gates at GREEN (LC-7: GREEN is the last round before the PR when the adversary is SOUND): the RED file (20 of 20); the 206-file comm set in the RED round's chunks against the cached base record (reuse by LC-6; the set must be re-derived to confirm its hash is unchanged by the GREEN diff, else recompute); black --check and the CI ruff tier on the touched .py files; the fourteen client jest fences that read repo files (by path) AND the FULL jest suite once (CLAUDE.md changes), through the junction's install, never a package manager; the pre-commit hook on commit.
- GC-7 GREEN COMMITS on fix/inc-i2e-guard-short-line (this gate allows it): one commit "fix(images): INC-I2e GUARD-SHORT-LINE short lines and joined spellings pass the picture guard (dark ENABLE_IMAGE_GUARD_SHORT_LINE)" with a body of 3-6 lines and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; through the hook, never --no-verify, never push. Exactly four paths: app/services/image_relevance.py, CLAUDE.md, .github/black-clean-paths.txt, tests/test_inc_i2e_guard_short_line.py.

## Stated limits (for the PR body)
- L-1 a one-letter line (Y, M) accepts a flanker title carrying the letter (YSL Y Le Parfum), as every line accepts its flankers.
- L-2 a stray standalone letter in a title with the right brand can pass a one-letter line.
- L-3 L'Eau d'Issey accepts other L'Eau ... lines of the same house (and Eau d'Issey).
- L-4 the empty-brand path is stricter for numbered lines (N(deg)5 refuses No 19).
- L-5 the whole-line drop set omits "spray" (a line "M Spray" loses its M).
- L-6 a typed alias brand with the resolver OFF (typed `YSL Y`) still needs the token `ysl` in the title (the empty-brand path has no alias folding): fixed only by the resolver window.
- L-7 two adjacent title tokens may join into a line token by chance (`s` + `i` -> `si`).

## The adversary (one, LC-1)
Correctness lens with the second lens folded in: the contract of spec section 2 against the committed diff; flag OFF byte identity (re-run P1 and read that the OFF path is the base text); the flag-mix walk of spec section 4 (G x S x R) by reading the seams (relevance_kwargs, the scs call site, apply_resolution, the KB-served branch, the camera path, accept_pick with no related item); false-accept probes beyond the RED rows (realistic wrong-product titles for Y, M, N 5, J'adore, Light Blue, L'Eau d'Issey, and lines like Bleu de Chanel, Sauvage, 212, CK One, Si, 1 Million) measured with the venv at the commit, both flag states; the CLAUDE.md block's claims against the code; the comm-set completeness by the union rule. Verdict SOUND / NOT_READY with findings rated BLOCKING / MAJOR / MINOR (minors become stated limits by LC-4).
