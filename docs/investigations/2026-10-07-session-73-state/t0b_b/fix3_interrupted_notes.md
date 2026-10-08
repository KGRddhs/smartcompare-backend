# T0b Phase B FIX round 3 notes (session 72)

Start 2026-10-06 00:03 AST (first tool call ~00:03). Budget 2 h -> stop measuring ~01:45, report by 02:03.
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b, HEAD 845ece15 (not updated).

## Start hashes (00:03) == fix2 final_hashes.json == adv-final END hashes (9/9):
- .githooks/pre-commit 864d30e5dd56a27de07cb5950417ea1fe79757ed2282f5b73d75f8dd7707a594
- .gitleaks.toml af71860f...
- .github/workflows/ci.yml 3b4b3ed2...
- tests/test_ci_gates.py 3b322a92...
- tests/test_gitleaks_config.py f305045b...
- tests/test_precommit_hook_phase_b.py 41eb1259...
- tests/test_precommit_hook_phase_b_round2.py cbcb795a...
- tests/test_precommit_hook_round2.py d2605991...
- tests/test_secret_scan_static.py 05e34918...

## Read 00:03-00:08: s72-common, spec, addendum, review, TB1-14, TBG1-8, TBF1-9, fix2 notes, adv-final notes.

## 00:10 box: node -e 0 0.92 s; hook runs measured 10-24 s each in the probe (slow-spawn).
## F1 probe (mk_variants.py -> variants/*.lf; f1_probe.py -> f1_probe.out), gitleaks stripped, scratch repos via
## the Phase A harness (hermetic env), variants: cur (fix2 hook), Y (backstop over porcelain staged.ext, LC_ALL=C),
## Yn (Y without LC_ALL=C), X2 (Y + NUL-mapped tr '\000' '\n' staged-diff file), Xd (adversary example tr -d).
- F1 CONFIRMED on cur, sh AND dash: dead_awk_png_akia rc0, dead_awk_png_jwt rc0, dead_awk_ttf_pk rc0,
  file_dead_awk_akia rc0, file_dead_awk_akia_env rc0 (the old stated limit is false).
- Y / X2 refuse all five (FOUR / NEWSHAPES), sh and dash; no 12-char piece in any output.
- utf16_akia (frozen 315_utf16_aws shape, working awk): cur/Y/X2 BINARY; Xd (tr -d) FOUR -> the adversary's
  tr -d example would change a frozen node's message (UTF-16 interleaved ASCII joined) -> not used.
- dead_awk_textconv_hide_akia: cur FOUR (fix2 fallback read the raw view), Y PASS (= base), X2 FOUR
  -> Y would narrow fix2's dead-awk coverage; X2 keeps it -> X2 chosen.
- pin_dead_awk_png_clean: cur/Y pass.
