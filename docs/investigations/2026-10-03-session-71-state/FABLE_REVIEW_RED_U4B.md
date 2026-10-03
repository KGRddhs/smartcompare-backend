# Fable review gate — U4b RED (synack-build-orchestrator Step 5.2), 2026-10-03

Reviewed: `sc-s70-u4b/SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` (sha256 `9225b396…`, +552/−29, CRLF kept) and `__tests__/helpers/pngDecode.ts` (`004cebe9…`), against `U4B_ICONS_DEPS_SPEC.md` §5 as corrected (14 corrections) and ruled (RQ1 ALIGN, RQ2 KEEP 1.0.0, RQ3 split CI, RQ6 scripts/, RQ8 versions).

**Verdict: PASS — GREEN may start (under Opus) once the Step 4 plan is approved.** No blocking issue; no GitHub issue filed.

Checked:
- Decoder (R9): signature check, chunk walk stopping at IEND, 13-byte IHDR, every IDAT concatenated before `inflateSync`, filters 0–4 with bpp = channels, straight alpha; refuses bit depth ≠ 8, colour type ∉ {2, 6}, interlace ≠ 0 with the spec's message shapes. Pixel layout = Pillow `tobytes()` for RGB/RGBA, so b7's `pixels_sha256` cross-check is valid.
- b12 proves the harness at base (two-IDAT split, five filters, 1×1 RGB, four refusals) — correction 13 honoured; Paeth mutant killed by the RED agent (log in `u4b/red/jest_b12_paeth_mutant.log`).
- b4–b10 assert the IHDR before decoding; thresholds match §4.4 prototype numbers with the spec's margins; b9 uses pixel-centre distance against 1024·33/108; b10's 0.28–0.33 window and the "narrower than adaptive" pin.
- b13/b14 pin the master sha and the renderer's path/needles (RQ6).
- d1 reddens on the orphan with `PENDING_REMOVAL = {}`; d5 pins package.json, lock root deps, lock package and node_modules; d3 todo and b3-todo deleted; EDGE_FIELDS/R11 docstrings past tense.
- k1/k2 target the RQ8 set; k3 exact `{ install: { exclude: ['react-native-svg'] } }`; k4 ALIGN variant (~10.0.x); k5 offline twin with the three range forms and "unsupported range" reported by name; k6 the Q3 = B split (names, run strings, continue-on-error only on the online step, order, no job-level continue-on-error, old name gone).
- e1 value unchanged with correction 4's executable rule in the comment (RQ2).
- RED proof: jest file alone `19 failed, 39 passed, 58 total`, 0 todo; tsc clean; eslint clean.

Minors for GREEN (not blocking): b1/b2 names still carry "(AHMED: supply art …)" — trim the suffix (prefix unchanged). k6's `run:` parser reads single-line `run:` values only, which the ruled steps are.

Residual risk accepted: thresholds are prototype-derived (Pillow 12.3.0 on this box); a different render lands outside them by design (the pin working).
