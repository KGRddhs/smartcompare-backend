# S81-08b spec writer report (Opus 5.5, 2026-10-24)

Spec: C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b/.qa-s80/S81-08b_UNIT_SPEC.md (52,933 B, ASCII, LF,
sha256 920fb599f82d61b455ddc20e6d692da3d7c6d962c0ce7d2ff120952f8bc5da14). Base ea3aef15. Worktree git
status --short empty (the spec is under the gitignored .qa-*/). Scratch worktree created and removed.

Runs:
- [pyt] tag=s08b-base-A ... elapsed=49s bound=1200s status=OK rc=0 (599 passed; netguard 14 attempts / 8 nodes)
- [pyt] tag=s08b-base-B ... elapsed=27s bound=1200s status=OK rc=0 (661 passed, 1 skipped; netguard 34 / 6)
- [pyt] tag=s08b-probe ... elapsed=5s bound=600s status=OK rc=0 (7 passed; netguard 0)

Key measured findings: only two request-time stored-row matches exist (register + W3-3 social, both via
_inherit_device_counter); share stores the body and matches nothing; invite/quiz read no fingerprint;
SAME_DEVICE is dead at base (_load_invitee selects no hash; 0 referrer-hash reads); the device cap is
stored-vs-stored; Sentry already filters the legacy header; S81-05 pins forbid any new leaf import in
auth_routes; S81-14 (main 86d5a24d) pins the FY25 file sha.

Counts: RED 11, PIN 14, mutants 16, comm set 222 files (base NOT MEASURED).
