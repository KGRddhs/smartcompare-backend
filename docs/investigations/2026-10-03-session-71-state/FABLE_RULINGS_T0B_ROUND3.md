
## Orchestrator rulings after round 2 (BINDING, 2026-10-03 20:15)

Round 2: fix-2 applied TF1 (hook a575e8ed...) and wrote the round-2 pins (22 nodes); the second shell-security adversary was SOUND (argv shims under sh and dash, -x traces, 0.25-8 MB inputs, the tag protocol, six revert mutants; 7 minors); fix-3 applied MINOR-1 (a Z trailer written only after a successful git diff, awk exits 2 without it, so a dying .env parse or a failed git diff refuses the commit), MINOR-2 (allexport switched off for the section) and MINOR-3 ((unnamed) entries) and added four r3_ pins (hook ba98ddc4..., round-2 file 30544f75..., 30 nodes).

- **TF6 (MINOR-4, stated limit).** A single .env line of about 1 MB or more makes the built-in parse take minutes (and crashed dash before round 2; it is refused now). No real .env has such a line; TF1 binds the parse to built-ins; a length cap would add a new semantic. Recorded in the PR text; no change.
- **TF7 (recorded).** A failed git diff still lets the byte-equal four-branch line and the 4a branch pass silently (their pipeline status is the last grep's); only 4b refuses. Phase B, which adds gitleaks in front of them, may give 4a the same Z-trailer pattern.
- **TF8 (orchestrator gates before commit).** The hook file dash column on the final hook (fix-3 ran its env nodes only) and the round-2 + skill files, through the bounded runner; then git rm --cached .claude/settings.local.json (TR7), test_skill_frontmatter fully green, the four-file pin set, commit, PR.
