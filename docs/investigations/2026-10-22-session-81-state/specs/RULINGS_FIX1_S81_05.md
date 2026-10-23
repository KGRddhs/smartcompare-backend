# RULINGS_FIX1_S81_05 (orchestrator Fable 5.1, 2026-10-23 ~15:50 AST): REQUEST-CONTEXT (ENABLE_REQUEST_CONTEXT_HEADERS) fix round 1 after two SOUND adversaries on GREEN e9fd7148 (correctness 0 blocking / 0 major / 5 minor; engineering 0 / 0 / 7 minor; reports <scratchpad>/S81-05_adv/{correctness,engineering}_REPORT.md, copied to specs/S81_05_ADV1_*.md)

Precedence: GATE_S81_05 > RULINGS_S81_05 > the review > the spec; these rulings amend them for this round. Measurement base stays 84c861f6 (the branch base). The rebase onto dfc6502f is the NEXT step, not this round: the fix agent makes no git write beyond ONE commit on feature/s81-s05-request-context (never add/checkout/rebase/stash). GREEN never edits a RED assertion; the fix round may ADD rows.

## Code rulings
- F1-1 (correctness m2): `device_key()` fails CLOSED on a pepper that cannot be UTF-8 encoded: catch `UnicodeError` around the encode, return None and emit the SAME rate-limited WARNING naming DEVICE_KEY_PEPPER (never the value, never the exception text). One new row (red on the GREEN bytes: a lone-surrogate pepper raises UnicodeEncodeError today) + one mutant (the except removed) killed.
- F1-2 (correctness m5, GREEN D6): drop the dead defensive code in `header_state`: no bytes-name case folding (ASGI servers deliver lower-case header names; the spec's exact-bytes compare stands) and no non-constant-state filter (only the three constants are ever bound). No pin for removed code; the STATELEAK / case-fold mutants fall away. Flag OFF stays byte-identical (the P4 literals re-run both ways).

## Wording rulings (CLAUDE.md row, PR body, main.py comment, leaf docstring)
- F1-3 (correctness m1 + engineering m3): stated limit (4) and the main.py S81-05 comment read "never the default-limit (SlowAPIASGIMiddleware) key_func, which runs outside the ContextVar scope; a per-route @limiter.limit key_func runs inside it and may read these values (measured)".
- F1-4 (engineering m1): the canary sentence: the WARNING can fire only once a consumer calls device_key (S81-09); until then confirm DEVICE_KEY_PEPPER by NAME on web before that consumer flips.
- F1-5 (correctness m3): "pinned by r26" -> "r26 pins the default-executor case; the qaren-worker pool is a plain ThreadPoolExecutor with the same contract (read)".
- F1-6 (correctness m4 + engineering m2; row + PR body): "Flag OFF and ON are byte-identical on every response by construction (the same scope / receive / send objects, r22 / r23); measured on the 401 / 404 envelopes in four states (P4) and on 12 request shapes by the correctness adversary".
- F1-7 (engineering m4): "read once per ASGI call of any scope type (the flag read is the first statement)", not "once per HTTP request".
- F1-10 (GREEN Q3): p19 / p20 are GREEN-time contract rows (red at base because the leaf is absent); the PR body's pin table says so.

## Orchestrator-side (not the fix agent's)
- F1-8 (engineering m5): the comm-set rule in s81-common.txt gains: Path.glob walkers, `"app"` path-segment joins, bare ast.parse(read_text), listdir / scandir, .github readers, helper-module importers and conftest fixtures (measured here: no missing file).
- F1-11 (GREEN Q1): the rebase step (wf_unit_rebase.js) onto the main of that moment carries the CLAUDE.md anchor union (session order B1, B3, B4, D03, S81-03, ST1 once PR #370 is merged, S81-05) and the FY25 UNIT_ENV union with S81-03's line; it launches after this round's re-verifier is SOUND.

## Measurement rulings
- F1-9 (engineering m6 / m7): with node -e 0 above 3 s the CI-order set runs in chunks of at most 8 files; the hook `-k black` nodes are NOT MEASURED locally this round unless the box is idle (CI covers them); both stated in the report.
- Gates for the fix commit: unit file ON and OFF; the new row red on the pre-fix bytes (state the AssertionError / exception seen on a scratch copy of e9fd7148, never a checkout in the worktree); the mutation rows for device_key and header_state re-run on the fix bytes + the new mutant; the 28-file pin set and the CI-order set; the comm set at HEAD vs the GREEN record (branch-only-new empty); ruff E9,F63,F7,F82 + py_compile + black on the touched files; pre-commit hook on the commit (no --no-verify). Re-verifier: both lenses in ONE agent on the exact commit bytes.
