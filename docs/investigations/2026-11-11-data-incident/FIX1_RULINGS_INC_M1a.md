# FIX ROUND 1 RULINGS, INC-M1a (S96-FIX, 2026-11-17 14:22 AST)

Head under review: 06deda559bc1bdebf249edf3b23c072e5b37956b on fix/inc-m1a-resolver-fold (base main 9bc13109).
Adversary: <SP>/INC-M1a_adv/correctness_REPORT.md, verdict NOT_READY: B1 blocking, M1 major, m1-m7 minor. Probes: probe_guard.txt, probe_accept.txt, probe_x1.txt.

## FX1 (B1): scope the one-character exact rule to the lexicon arm only
- Keep GREEN's D1 rule (a one-character alias token matches only exactly) ONLY in the lexicon arm's D5 line search, reached from _lexicon_side. Pass a keyword through _best_window / _token_distance from that one caller, or use an equivalent explicit seam.
- _line_within_typed, the model-arm guard, and every other caller of _best_window / _token_distance must behave exactly as at base 9bc13109.
- These model-arm accepts are true at base and must be true again: typed "Chanel No 5" with model line "N" + chr(0xB0) + "5"; "Chanel No 5 Eau de Parfum"; "Hermes Terre de Hermes" with model line "Terre d'Hermes"; "Dior Bois de Argent" with model line "Bois d'Argent"; "Prada Le Homme" / "L'Homme"; "Issey Miyake L Eau De Issey". Take the exact inputs from probe_guard.txt and probe_accept.txt.
- Build every non-ASCII character with chr() at run time.

## FX2 (M1): a new pin file, RED-first
- The frozen RED file stays byte-identical (63fc6a67). Add tests/test_inc_m1a_gate_rows.py, pure ASCII, hermetic, flags set explicitly.
- **SR rows (short tokens):**
  - These must NOT resolve high to (Yves Saint Laurent, Y): "YSL L'Homme", "Yves Saint Laurent L'Homme", "YSL B", "YSL by", "YSL X", "YSL 1", "YSL Ya", "YSL Yo", and "YSL" plus a one-letter Arabic token.
  - These MUST resolve to (Yves Saint Laurent, Y): "Y", "Y EDP", "YSL Y", "Saint Laurent Y", "YSL Y EDP", "YSL Y Elixir". Use probe_short_after.txt as the golden.
- **MG rows (model guard):**
  - The FX1 accepts above go through _line_within_typed / accept_model_side, using the same seam as test_inc_r1_resolver.py's r21 rows.
  - Add at least one refusal the guard already makes at base (a model line not within the typed text). This pins the guard both ways.
- **Proof, in this order:**
  1. At HEAD 06deda55 the MG rows FAIL (AssertionError only), and the SR rows PASS.
  2. With mutant X1 (D1 reverted) applied on a scratch copy, the SR rows FAIL.
  3. After the FX1 fix, all rows pass.
  4. Mutant "exact rule applied in _line_within_typed too" (today's HEAD) fails the MG rows.

## FX3 minors
- **m1:** reword the CLAUDE.md M1a bullet and the PR body to: "with ENABLE_PRODUCT_RESOLVER OFF nothing changes, except the INC-U1 link key (product.link_key, brand and variant in the /url response) when ENABLE_URL_LINK_RESULT is ON (M1R-9; both OFF on web)". Remove "the resolver is not called" and "reads no lines file".
- **m2:** moot after FX1. The CLAUDE.md bullet says the one-character rule is the lexicon arm's only.
- **m3:** the PR body: put the [pyt] line under "Existing resolver suites ... 699 passed".
- **m4 (bare "Y" resolves high with no house):** a stated limit, as the base exact single-token rule. It is an owner question for the resolver window. No code.
- **m5 (two flanker words, first wins):** a stated limit. No code.
- **m6, m7:** stated limits.
- **The client fences:** the orchestrator has made the node_modules junction in the worktree. Run the fourteen fences ONCE by path from INC-P2_fix1/fence_list.txt (jest, the same command INC-P2 used). The accepted drift is the 4 config/nativeBundle.w37 nodes.

## Gates for the fix round
- Unit file + the new pin file + test_inc_r1_resolver.py, with ENABLE_PRODUCT_RESOLVER on and off.
- The 7 resolver suites.
- The comm set at the new HEAD vs the base list (branch-only-NEW EMPTY).
- The whole-tree one-process run is NOT re-run unless module-level state changes again.
- One new commit on the branch: no amend, no force push. Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.

## Re-verifier
- One correctness re-verifier on the new HEAD.
- It checks:
  - B1 is closed, both ways (lexicon short-token exactness kept; model guard back to base);
  - M1 is pinned (X1 killed);
  - the MG rows are killable;
  - the minors' words match the bytes;
  - the fence result.
