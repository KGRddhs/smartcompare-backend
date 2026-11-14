## S95-DEP: dnspython 2.9.2 and soupsieve 4.1 (pip-audit --strict clean again)

`dependency-audit` is a required check. It turned red on main's own lock when the audit feed began reporting five advisories, after #404's CI run had passed. Every PR fails it until the lock moves:

| package | locked | advisory | fixed in |
|---|---|---|---|
| dnspython | 2.9.0 | CVE-2026-128089 | 2.9.2 |
| soupsieve (via beautifulsoup4) | 2.9.2 | CVE-2026-126190 / -126191 / -126192 / -126193 | 4.0.0 / 3.0.2 / 2.10.0 |

### The change
- `requirements.in`: the floors `dnspython>=2.9.2` and `soupsieve>=4.0` (floors only, the certifi / #367 pattern).
- `requirements.txt`: recompiled with CI's own command, `uv pip compile requirements.in -o requirements.txt --universal --python-version 3.12`, seeded from the committed lock. Exactly two pins move: dnspython 2.9.0 -> 2.9.2 and soupsieve 2.9.2 -> 4.1. `requirements-dev.txt` is unchanged by its recompile.

### Measured (one adversary, SAFE by the leaner chain: SOUND)
- Lock currency: CI's `Lock is current` commands give an empty diff for both locks. `pip-audit -r requirements.txt --strict`: no known vulnerabilities (the base lock reproduces exactly the five).
- Two venvs, base (the CI pins) and head (the new locks), run 259 test files in 11 chunks. These are every test naming price_service, url_extraction_service, bs4, email_validator / EmailStr or the auth register / login paths. Results are identical, and no node fails only at head.
- The backend's only CSS selectors (8 compound selectors in `app/services/price_service.py`, no combinators, no pseudo-classes) give identical results under both venvs on synthetic pages and on all 11 `tests/fixtures/iherb_*.html` fixtures.
- dnspython is reached only through email-validator behind pydantic `EmailStr`, called with `check_deliverability=False`, so no `dns.*` module is used at runtime. 12 synthetic `EmailStr` cases give identical results.

### Stated limits
- Release age: soupsieve 4.1 (2026-11-10) and dnspython 2.9.2 (2026-11-03) are younger than the house's 14 days, and no CVE-fixing release of either package is older. The rule covers new dependencies, and neither package is new to the lock. Taking 4.1 also brings a fix for a selector-compile race between threads.
- soupsieve jumps two majors. On edge-case markup, 4.x no longer matches content inside `<template>` (a 4.0 change), and `[attr=value]` no longer ignores a trailing newline (a 4.1 fix). Results are identical on normal pages and on every fixture. If such markup appears live, card capture falls through to the existing fallback chain.
- When the advisories were published was not verified, only that #404's audit passed and this one fails.
- The local measurement ran on Windows with uv 0.12.5. CI on Linux, with the newest pip-audit against the live feed, is the arbiter.

### After the merge
Railway redeploys `web` with the new lock (soupsieve 4.1 in production HTML parsing). No flag and no client change. Every open PR then needs main merged in so that its `dependency-audit` reruns.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
