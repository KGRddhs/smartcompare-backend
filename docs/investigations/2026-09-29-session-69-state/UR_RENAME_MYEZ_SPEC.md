# U-R — rename the app from Qaren to MYEZ (ميّز) in the client, the health message and the landing — unit spec

**Ahmed, 2026-09-30 (mid-session, binding): "we renamed it to MYEZ."** The pitch-prep memory of 2026-09-27 already records MYEZ (Mayez / ميّز) as the company brand; the app now carries it too. Owner: Claude. JavaScript + static HTML: rides the production build (the display name and purpose strings are native and live in U4a).

## 1. Measured footprint (main `d6e613a3`)

| Where | `Qaren` | `قارن` |
|---|---|---|
| `SmartCompareApp/src/i18n/en.json` | 26 | 0 |
| `SmartCompareApp/src/i18n/ar.json` | 2 | 108 |
| hard-coded literals in `SmartCompareApp/src/**/*.ts(x)` (outside i18n, outside `qaren://` / `qaren.app` / `com.qaren` / `qaren-rr` / `Qaren<Component>` identifiers) | 9 | — |
| `SmartCompareApp/app.json` (`name` + the two permission strings) | 3 (owned by **U4a**, see its RENAME NOTICE) | 0 |
| `app/main.py` (`/health` message "Qaren API is running") | 2 | 0 |
| `landing/{index,privacy,terms,support}.html` + `landing/ar/{index,privacy,terms}.html` | 30 | 51 |
| `app/legal/*.md` | 12 | 0 (rewritten wholesale by **U8**, not here) |

## 2. Target

R1 **Catalogs.** Every user-visible `Qaren` in `en.json` → `MYEZ`; every `قارن` in `ar.json` → `ميّز` (and the 2 Latin `Qaren` there → `MYEZ`), EXCEPT strings that are addresses or identifiers: `qaren://…`, `qaren.app`, `support@qaren.app`, `privacy@qaren.app`, `legal@qaren.app` (decision D14; default = keep), and any key whose value is a URL. Arabic grammar: ميّز is a proper noun; re-read every sentence it lands in (e.g. «قارن يساعدك» → «ميّز يساعدك») and fix agreement where the old name was used as a verb pun («قارن» also means "compare!"; the copy may have leaned on that — where a sentence only works as the verb, keep the verb and add the brand elsewhere).
R2 **Hard-coded literals** (the 9): move to i18n keys or rename in place; component identifiers (`QarenLogo`, `Qaren*`) stay (code names, not copy).
R3 **Health message**: `app/main.py` → "MYEZ API is running" (a jest/pytest that pins the old string, if any, is updated; `scripts/bundle_d_prod_smoke.py` checks only the status code — verify).
R4 **Landing**: the seven HTML pages: brand text → MYEZ / ميّز; the `<title>`s; the wordmark text; keep the AASA file, the Team ID, the `/support` mailto (D14). Do not touch `landing/README.md` history.
R5 **Nothing else**: not app.json (U4a), not legal (U8), not the bundle id / slug / scheme / EAS project / Sentry org, not `data/trending_curated.json` unless it carries the brand.
R6 **Wordmark**: `assets/logo-wordmark.png` does NOT exist on main (the follow-up doc names it; verify) — nothing to change; the icon is D4.

## 3. Tests (RED at base)

T1 `__tests__/i18n/brand.myez.s69.test.ts`: a fence over both catalogs: no value contains `Qaren` or `قارن` unless the value is an address/URL/scheme (allowlist regex `qaren://|qaren\.app|@qaren\.app`); every value containing `MYEZ`/`ميّز` in one catalog has a counterpart key in the other (parity via the existing W3-11 fence); the copy-policy banned words are absent.
T2 `__tests__/brand.hardcoded.s69.test.ts`: a source fence over `src/**/*.tsx?` for string literals containing `Qaren` outside the identifier/URL allowlist → 0.
T3 backend `tests/test_health_brand_s69.py`: `GET /health` message contains `MYEZ` and not `Qaren` (through the bounded runner).
T4 landing: a small node/py script test that the seven pages contain no `Qaren`/`قارن` outside `qaren.app`/mailto (can live under `tests/` as a static file check).

## 4. Gates
Client: jest by path `'\.s69\.test|i18nFence|copyPolicy|Home|Onboarding|Profile'`, FULL suite (orchestrator), tsc, eslint by path. Backend: the new test + `tests/test_security_regression.py` health cases through `pyt.py`; ruff count unchanged. Landing: `grep -rn "Qaren\|قارن" landing --include=*.html | grep -v "qaren.app"` → 0.

## 5. Rulings
- R-A: `MYEZ` in capitals, `ميّز` with the shadda, until Ahmed answers D12/D13 otherwise; a later restyling is a catalog-only change.
- R-B: addresses stay on qaren.app (D14 default B); the landing pages say MYEZ with the old address.
- R-C: never `git checkout --`; junction rules; bounded runner for every pytest; the Arabic is written by the green agent and marked for the on-device walkthrough.
