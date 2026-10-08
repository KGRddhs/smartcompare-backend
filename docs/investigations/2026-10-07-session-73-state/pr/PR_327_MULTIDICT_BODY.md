## Dependency bump: multidict 6.7.1 -> 6.9.1 (CVE-2026-104874)

`pip-audit -r requirements.txt --strict` (the blocking `dependency-audit` job) started failing on 2026-10-07 on every PR, including the docs-only #326:

```
Found 1 known vulnerability in 1 package
multidict 6.7.1   CVE-2026-104874   6.9.1
```

This PR moves the one transitive pin to the advisory's fix version and nothing else:

- `requirements.txt`: `multidict==6.7.1` -> `multidict==6.9.1` (recompiled with `uv pip compile requirements.in -o requirements.txt --universal --python-version 3.12 --upgrade-package multidict==6.9.1`; uv 0.12.5)
- `requirements-dev.txt`: recompiled with `-c requirements.txt`; no line changed.

No `.in` file changed. The `Lock is current` CI step re-compiles both locks and diffs them; `backend-tests` installs the new pin on Linux (the local venv keeps the CI pins untouched while two gate workflows run on it, so the Linux run is the test of this bump).

Not verified locally: multidict 6.9.1 at runtime (CI's backend-tests job is the measurement).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
