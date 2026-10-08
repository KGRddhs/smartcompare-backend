# T0b Phase B round-3 CONTINUATION fix agent notes
start 2026-10-07 19:34:03 (budget 2h -> 21:34)

## start_hashes (python hashlib, 19:34)
.githooks/pre-commit 4e9a583c76575fe774312152cdf2b53759719c203473325599c9b9fbb3ed4e3b (round-3 edit, DIFF vs snapshot, expected)
.github/workflows/ci.yml 05c4ff90b00235f34f3a6fa7597077e7e56e3afb90d031865f3b238ac00ce8ae (round-3 edit, DIFF, expected)
.gitleaks.toml af71860f0f1e8c2f925ec3df8847af6367afcea82fd958c2ed8e2472ecccdb40 EQ snapshot
tests/test_ci_gates.py 3b322a925500190b9acf6b97129797f4cc89f784875696bac2fc5e4af66a824b EQ
tests/test_gitleaks_config.py f305045bcb187319b717cbf237f2dcfe152bf9bcee62a9cfa22d9c3359987b8e EQ
tests/test_precommit_hook_phase_b.py 41eb1259f56dbc1459e033d7d360ed57b2773667c0a120f7610b2194d3e29703 EQ
tests/test_precommit_hook_phase_b_round2.py ef2cfe21bbb01377222fecd2ca46dc199cac7e7fa5b1f1b78c42b582c5a63c24 (round-3 edit, DIFF, expected)
tests/test_precommit_hook_round2.py d26059912eb26e547bd79ac1af1fb102bb9d990d0b34b68b1326e2a5cb35d394 EQ
tests/test_secret_scan_static.py 05e34918a5c105436d80dba1cdd6cdbbfe5c067a7700a5ee6529819a6864b976 EQ
=> six named files equal SHA256SUMS.txt; no stop.
hook + ci.yml CRLF working copies (691/691, 586/586 CRLF); tests LF except test_ci_gates.py (CRLF).

## 19:37 round-4 nodes re-run on the start bytes
[pyt] tag=fix3c-r4-rerun start=2026-10-07 19:37:17 end=2026-10-07 19:37:32 elapsed=14s bound=600s status=OK rc=0 (16 passed)

## 19:38 locale probe (grep 3.0 MSYS, f.txt with 0xFF on an earlier line, key later)
- unset LC_*/LANG: grep acts as C (lines kept) although `locale` prints C.UTF-8
- LC_ALL=C.UTF-8 / en_US.UTF-8: grep drops ONLY the line holding 0xFF, keeps later lines, appends "Binary file X matches" at the END (stdout, grep 3.0)
- grep -q matches a key on a line holding 0xFF in both locales
=> m4 (LC_ALL=C dropped) is invisible to the ruled node (byte on an EARLIER line); visible only with the key on the SAME line as the byte.

## 19:39-19:42 test edits (round-2 file only, Edit tool, LF)
- docstring Round 4 -> F1 to F4 + TBF11 shim note
- imports GIF, OTF, WEBP from the Phase B file
- CI_GL_SHIM amended (TBF11): +13/-1 lines; colour unless argv has --no-color; ERR -> ESC[31mERR ESC[0m via sed
- nodes: f1_dead_awk_utf8_locale_invalid_byte_then_akia_refused (LC_ALL=C.UTF-8, 0xFF built in Python),
  f4_{jpeg,ttf,gif,webp,otf}_upper_case_extension_passes, ci_unreachable_pr_base_fails_without_scanning
- py_compile ok; ruff E9,F63,F7,F82 clean; black: only pre-existing lines differ (file not on the allowlist)
[pyt] tag=fix3c-new-nodes start=2026-10-07 19:41:44 end=2026-10-07 19:42:26 elapsed=41s bound=600s status=OK rc=0 (46 passed: Round4 + TestSecretScanStep)

## 19:43-19:53 mutants (mut.py; byte copy -> count-checked edit -> killing nodes sh+dash -> restore -> sha256; mutants.jsonl)
- tbf11_ci_no_color_dropped: KILLED 6/6 (ci_gitleaks_err_line_fails rc=0 behavioural x2, ci_gitleaks_call_runs_without_colour argv x2, ci_real_gitleaks_err_line_fails rc=0 x2) [pyt] m_tbf11 19:43:57-19:44:05 9s FAIL rc=1
- C_pr_ends_head_only: KILLED by ci_unreachable_pr_base_fails_without_scanning sh+dash (rc=0); the push node stays green [pyt] 19:44:06-19:44:11 5s FAIL rc=1
- m1_ext_reader_dropped: SURVIVED 48/48 (Round4, b3_, a1_) [pyt] 19:44:25-19:45:19 54s OK
- m2_tr_reader_dropped: SURVIVED 48/48 [pyt] 19:45:19-19:46:19 60s OK
- m3_tr_d: KILLED by frozen i315_utf16_aws_key sh+dash (+ a4_typechange, b7_gif/webp dump, pin_a3 dump) [pyt] 19:46:19-19:46:39 19s FAIL
- m4_lc_all_dropped: SURVIVED 36/36 incl. the new f1_dead_awk_utf8 node [pyt] 19:46:39-19:47:42 63s OK
- H_{jpeg,ttf,gif,webp,otf}_case_row_dropped: each KILLED by its f4_ node sh+dash (binary refusal of the sample path)
- tbf1_no_color_dropped: KILLED (tbf1 shim argv x2, tbf1 real rc x2)
- every restore sha == 4e9a583c (hook) / 05c4ff90 (ci.yml)

## 19:54 m4 probe (m4_probe.py -> m4_probe.out; dead awk, gitleaks stripped; base = 845ece15 blob de0a4bd8)
ruled (0xFF earlier line, key later file) LC_ALL=C.UTF-8: base/cur/m4 all rc=1 FOUR (sh, dash) -> m4 invisible
same line (key + 0xFF on one line) LC_ALL=C.UTF-8: base rc=0, cur rc=1 FOUR, m4 rc=0 (sh, dash) -> a same-line node kills m4 (new-only refusal; base never refused it)
same line, default env (grep acts as C here): all rc=1

## Gates (TBF18)
G1 gitleaks STRIPPED (PATH without the WinGet Gitleaks dir; shutil.which(gitleaks)=None, sh/dash/git resolve):
[pyt] tag=fix3c-nogl-phA start=2026-10-07 19:54:30 end=2026-10-07 19:57:43 elapsed=192s bound=1200s status=OK rc=0 (62 passed)
[pyt] tag=fix3c-nogl-r2frozen start=2026-10-07 19:57:52 end=2026-10-07 19:59:35 elapsed=103s bound=1200s status=OK rc=0 (30 passed)
[pyt] tag=fix3c-nogl-phb start=2026-10-07 19:59:35 end=2026-10-07 20:06:11 elapsed=395s bound=1200s status=OK rc=0 (97 passed, 17 skipped)
[pyt] tag=fix3c-nogl-r2new start=2026-10-07 20:06:21 end=2026-10-07 20:12:28 elapsed=368s bound=1200s status=OK rc=0 (95 passed, 8 skipped = gitleaks not on PATH: tbf1_real x2, widening x4, ci_real x2)
G2 gitleaks PRESENT:
[pyt] tag=fix3c-gl-phA start=2026-10-07 20:12:40 end=2026-10-07 20:18:32 elapsed=352s bound=1200s status=OK rc=0 (62 passed)
[pyt] tag=fix3c-gl-r2frozen start=2026-10-07 20:18:33 end=2026-10-07 20:21:37 elapsed=184s bound=1200s status=OK rc=0 (30 passed)
[pyt] tag=fix3c-gl-phb-sh start=2026-10-07 20:21:55 end=2026-10-07 20:28:25 elapsed=390s bound=1200s status=OK rc=0 (57 passed; -k "not dash")
(the Bash tool moved the two-call loop to background at its 600 s cap; the same single process kept running, no second pytest started)
G4: sh -n 0, dash -n 0 (LF copy hook.lf); yaml.safe_load ci.yml 7 jobs incl. secret-scan; hook 691/691 CRLF, ci.yml 586/586 CRLF
G7: git diff --stat == git diff --ignore-cr-at-eol --stat (cmp equal): 4 tracked files, 466 insertions, 70 deletions (hook 414, ci.yml 93, test_ci_gates 16, test_precommit_hook_round2 13)
G6: gitleaks dir over byte copies (sha-checked) of the 9 unit files, default-only config, --redact --no-color --ignore-gitleaks-allow, id+path template: rc=0, report empty (0 findings); positive control (runtime GitHub-token shape) rc=1 github-pat
[pyt] tag=fix3c-gl-phb-dash start=2026-10-07 20:28:26 end=2026-10-07 20:34:59 elapsed=393s bound=1200s status=OK rc=0 (54 passed, 3 skipped sh-only real-commit nodes)
[pyt] tag=fix3c-gl-r2new-sh start=2026-10-07 20:35:11 end=2026-10-07 20:40:39 elapsed=328s bound=1200s status=OK rc=0 (55 passed)
[pyt] tag=fix3c-gl-r2new-dash start=2026-10-07 20:40:48 end=2026-10-07 20:46:36 elapsed=348s bound=1200s status=OK rc=0 (48 passed)
G3: [pyt] tag=fix3c-pins start=2026-10-07 20:46:50 end=2026-10-07 20:48:52 elapsed=122s bound=1200s status=OK rc=0 (261 passed; ci_gates, channel_freshness, gitleaks_config, hermeticity_pins, secret_scan_static, skill_frontmatter, sqlfluff_config)

## F5 (TBF17) 20:49:00-20:51:17, real gitleaks 8.30.1, git 2.52.0.windows.1, real `git commit` through the hook (core.hooksPath)
control plain commit: rc=1 not committed, "gitleaks refused the staged changes (rule id and place above)"
git -c color.ui=always commit: rc=1 not committed (same refusal)
git -c color.diff=always commit: rc=0 COMMITTED -> BYPASS CONFIRMED
diagnosis (f5_precedence.out, f5_direct.out): a git child of the hook sees GIT_CONFIG_PARAMETERS over GIT_CONFIG_COUNT (color.ui: override=always);
 direct gitleaks: PARAMETERS color.ui=always alone rc=0; + the hook's COUNT override rc=1 (color.diff=never is more specific than color.ui)

## Survivor follow-ups 20:51-21:02
frozen round-2 d1_/r3_ under m1/m2/m4: 18/18 pass each (SURVIVED)
m1 probe (m1_probe.out): dead awk + LC_ALL=C.UTF-8 + diff.external decoding a key with 0xFF on the same line: base rc=0, cur FOUR, m1 rc=0 (sh, dash) -> killing node design measured
m2: fix3_prev notes measured dead_awk_textconv_hide_akia (Y = porcelain-only = m2) PASS vs X2 FOUR -> killing node design
## Final 21:03: hook 4e9a583c, ci.yml 05c4ff90 unchanged from start; round-2 file a9383736 (+272/-1 vs fix-2 snapshot; LF, ASCII); 6 others = snapshot
