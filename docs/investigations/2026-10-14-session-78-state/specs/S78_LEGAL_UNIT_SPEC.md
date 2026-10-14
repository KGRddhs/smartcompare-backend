# S78-LEGAL unit spec (measured)

- Unit: S78-LEGAL. Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s78-legal`, branch `feature/s78-legal-privacy`, base main `4772d492` (clean tree, `git status --short` empty at the start).
- Binding rulings: `sc-docs-70/docs/investigations/2026-10-14-session-78-state/specs/RULINGS_S78_LEGAL.md` (LR1-LR11). They win over this spec where they conflict; this spec only makes them executable.
- Evidence: `runs/legal_exposure_audit_wf_5cc660fb.json` (lenses personal / secrets / law / tos / privacy + synthesis), `LEGAL_AUDIT_PLAN_S78.md`, `NOTES_DRAFT.txt` (same state folder).
- Personal-data rule: this file never carries the home address, a house / block / road number, a phone number or a personal email. They are written `<HOME_ADDRESS>`, `<HOME_TOWN>` (the town component of the current postal value, a two-word name ending in "Town" followed by a four-digit code), `<PHONE>`, `<PERSONAL_EMAIL>`. The controller name "Husain Aseeri" is the public App Store seller name (LR2) and is written out.
- Every measurement below was taken read-only on the base tree; nothing in the worktree was written (sha256 of `app/legal/*` and every `landing/*.html` / `landing/ar/*.html` before and after the dry runs: identical; `git status --short` empty).

## 0. What the unit does (one paragraph)

Through the U8 machinery only (LR9): replace the controller postal value with the LR1 interim line (EN + a new AR key), correct the controller name to the Apple spelling and add the field of activity and the trade name (LR2), describe every infrastructure recipient by category with an on-request sentence and list transfer countries without vendors (LR3), trim the security internals (LR6), rewrite the Terms of Service as v2 with the LR5 sections (Apple section, carve-outs, narrow indemnity, general clauses), move the twelve date anchors to 2026-10-14 (LR4; the two route anchors become derived from `consent_service.TERMS_VERSION`), and replace the personal email in the two crawler User-Agent strings (LR7). Then update the pins that assert the old text (LR9) and add a pattern-based RED file (LR8).

## 1. Base state (measured at 4772d492)

### 1.1 Fill-in data file `tests/fixtures/legal_fill_in_u8.json` (61 lines, CRLF)

| line | key | base value | ruling |
|---|---|---|---|
| 12 | `trade_name` | `""` | LR2 -> `"MYEZ"` |
| 29 | `placeholders.CONTROLLER_NAME` | `"Hussain Aseeri"` | LR2 -> `"Husain Aseeri"` |
| 30 | `placeholders.CR_NUMBER` | `null` | stays (d5 = A) |
| 41 | `placeholders.IP_OWNER` | `"the publisher"` | -> `"the developer named in section 1"` (TOS-11: "the publisher" is undefined) |
| 42 | `placeholders.IP_OWNER_AR` | AR "the publisher" | -> AR twin (section 3) |
| 46 | `placeholders.POSTAL_ADDRESS` | `<HOME_ADDRESS>` (shape: three "Word NNNN" street components, "<HOME_TOWN> NNNN", "Bahrain") | LR1 -> interim EN |
| (none) | `placeholders.POSTAL_ADDRESS_AR` | does not exist: the AR documents carry the same Latin `<PLACEHOLDER:POSTAL_ADDRESS>` token | NEW key (section 2, step B) |
| 47 / 52 | `PRIVACY_EMAIL` / `SUPPORT_EMAIL` | `privacy@getmyez.com` / `support@getmyez.com` | unchanged |
| 37 / 38 | `HOSTING_REGIONS` / `_AR` | "India and Singapore" / AR twin | unchanged (country list stays true) |
| 4-6 | `_placeholders_comment`, `_placeholder_answers_comment`, `_values_comment` | measured clean: no address value, no street-number shape, no name | extend with the S78 sentences (section 2) |

The Arabic documents show the controller name in Latin script (the same `CONTROLLER_NAME` token, `privacy_policy_ar.md:9`): there is no Arabic-script spelling to keep, so LR2's "Arabic rendering" question is moot; an Arabic spelling (if ever wanted) would need a new `CONTROLLER_NAME_AR` key, and the Arabic form of the name does not distinguish Husain / Hussain. Flagged, nothing to do.

### 1.2 Pre-fill snapshot templates `tests/fixtures/legal_prefill_u8/*.md` (all CRLF)

`fill_in_legal.py` fills these (the committed `app/legal/*.md` are the filled copies; `test_polish_prefill_snapshot_tracks_the_documents` requires that filling the snapshot with the committed data reproduces the live sources).

| file:line | token(s) / text the unit touches |
|---|---|
| `privacy_policy.md:5` | `*Effective date: October 11, 2026*` (date line) |
| `privacy_policy.md:9` | s1 identity: fork `d5_identity` inline A = `<PLACEHOLDER:CONTROLLER_NAME><PLACEHOLDER:TRADE_NAME_CLAUSE>, <PLACEHOLDER:POSTAL_ADDRESS>` |
| `privacy_policy.md:75-85` | s5 list: Supabase, Railway, Upstash, Sentry ("stored in the EU (Germany)"), OpenAI, Expo, Apple, Google (+ "Google also receives the email ... (see Cloudflare below)"), search providers (Serper, Bright Data, Firecrawl, Scrape.do + `<PLACEHOLDER:YOUTUBE_CLAUSE>`), Cloudflare + "Google (Gmail)", retailer websites |
| `privacy_policy.md:87` | s5 carve-out sentence (kept) + own-terms sentence "Retailer websites (section 6), the sign-in providers Apple and Google, and Google as our mailbox provider act under their own terms." + "We may also disclose data where the law requires it." |
| `privacy_policy.md:91` | s5 website paragraph naming Google Fonts |
| `privacy_policy.md:99` | s7 "United States (OpenAI and Google) and Germany (Sentry)<PLACEHOLDER:HOSTING_REGIONS_CLAUSE>. <PLACEHOLDER:TRANSFER_BASIS>" |
| `privacy_policy.md:131` | s11 "We do not send advertising. <PLACEHOLDER:INAPP_NOTIF_CLAUSE>" |
| `privacy_policy.md:135` | s12 `<PLACEHOLDER:MINORS_CLAUSE>` |
| `privacy_policy.md:139` | s13 "(certificate pinning)", "(Keychain)", "Administrative functions require a secret key." |
| `privacy_policy.md:141` | s13 "From our servers, Sentry receives exception types, ..." |
| `privacy_policy.md:151` | s15 changes sentence |
| `privacy_policy.md:157` | s16 `- **Postal address:** <PLACEHOLDER:POSTAL_ADDRESS>` |
| `privacy_policy_ar.md` | the same lines (5, 9, 75-85, 87, 91, 99, 131, 135, 139, 141, 151, 157); s1 uses the Latin `CONTROLLER_NAME` and `POSTAL_ADDRESS` tokens |
| `terms_of_service.md:5` | date line |
| `terms_of_service.md:9` | s1 party clause with the `d5_identity` fork |
| `terms_of_service.md:1-104` | sections 1-17 (17 `##` headings); s16 Apple is one sentence (:98); s12 liability has no carve-outs (:73-80); s17 contact (:100-103) with `<PLACEHOLDER:POSTAL_ADDRESS>` at :103 |
| `terms_of_service_ar.md` | the same structure, 17 sections; :9 and :103 carry the Latin postal token |
| `support_contact.md:1` | `MYEZ is provided by <fork>.` |
| `support_contact_ar.md:1` | AR `<fork>.` |

### 1.3 Variants `scripts/legal_variants_u8.json` (190 lines, CRLF)

| line | entry | base | change |
|---|---|---|---|
| 5-16 | fork `d5_identity` (docs privacy, terms, support; inline A) | A = `<CN><TNC>, <POSTAL_ADDRESS>`; B = `<CN><TNC> (commercial registration number <CR_NUMBER>), <POSTAL_ADDRESS>`; AR twins with the Latin `POSTAL_ADDRESS` | postal token leaves the fork; A gains the field of activity (section 3.1) |
| 88-95 | clause `TRADE_NAME_CLAUSE` | `, trading as {value}` / AR | unchanged (answer `trade_name` becomes "MYEZ") |
| 97-106 | clause `MINORS_CLAUSE` privacy/terms true | "If you are under the age of majority where you live, ..." | LR5.3 under-18 text |
| 108-115 | clause `YOUTUBE_CLAUSE` on | "; YouTube (Google) receives product names ..." | category text (flag is off; keeps LR3 true if it is ever on) |
| 132-139 | clause `HOSTING_REGIONS_CLAUSE` nonempty | `, and in {value} (our database and hosting providers)` / AR | drop the role parenthesis (LR3: countries only) |
| 151-164 | clause `TRANSFER_BASIS` false | "... and to Google as our mailbox provider, which handles email under its own terms (section 5)." / AR | "our mailbox provider" (no vendor; basis no stronger) |
| 166-188 | clause `DELETION_SECTION` terms 043 (:174, AR :184) | "... Deleting your account erases your account data from our servers; ..." | point to privacy s9 + OpenAI (TOS-12); privacy 043 / old and terms old unchanged |
| 1-3 | `_comment` | mentions the Cloudflare line as plain text | reword to "the email-providers line" (no fork or clause may carry it) |

The forks `d3_training`, `openai_retention`, `territories_complaints`, `legal_basis`, `referral_push_name` and the clauses `INAPP_NOTIF_CLAUSE`, `DPO_CONTACT` are unchanged.

### 1.4 Generated markdown `app/legal/*.md` (filled at 2026-10-11, all CRLF)

Lines measured by content (address masked):

| file | date | `<HOME_ADDRESS>` | controller name | vendor names (whole word) |
|---|---|---|---|---|
| `privacy_policy.md` (157 lines) | :5 | :9, :157 | :9 | Supabase :75, Railway :76, Upstash :77, Sentry :78 :99 :141, Expo :80, Cloudflare :82 :84, Serper / Bright Data / Firecrawl / Scrape.do :83, Gmail :84, Google Fonts :91 |
| `privacy_policy_ar.md` | :5 | :9, :157 | :9 | the same lines (AR attaches the proclitic waw to some names) |
| `terms_of_service.md` (103) | :5 | :9, :103 | :9 | none (OpenAI and Apple only) |
| `terms_of_service_ar.md` | :5 | :9, :103 | :9 | none |
| `support_contact.md` (3) | - | :1 | :1 | none |
| `support_contact_ar.md` | - | :1 | :1 | none |

Street-component + digit pattern hits (the RED pattern of section 5 R1): 6 per privacy / terms document (2 occurrences x 3 components), 3 per support document, 0 anywhere else. No `@gmail.com`, no `+973` shape, no other email than the two role addresses in any legal markdown or landing page. The `<HOME_TOWN>` token occurs only inside `<HOME_ADDRESS>` in served surfaces.

### 1.5 Landing pages (six legal regions, all CRLF; regions generated by `scripts/render_legal_landing.py`)

| page | region begin / end | date line | `<HOME_ADDRESS>` | vendor lines in the region | site-address count (`qaren\.app|getmyez\.com`) |
|---|---|---|---|---|---|
| `landing/privacy.html` | :182 / :325 | :185 | :188, :323 | :253-262, :267, :273, :310 | 11 |
| `landing/terms.html` | :171 / :259 | :174 | :177, :257 | none | 6 |
| `landing/support.html` | :209 / :212 | - | :210 | none | 10 |
| `landing/ar/privacy.html` | :176 / :319 | :179 | :182, :317 | :247-256, :261, :267, :304 | 11 |
| `landing/ar/terms.html` | :162 / :250 | :165 | :168, :248 | none | 6 |
| `landing/ar/support.html` | :208 / :211 | - | :209 | none | 10 |

Outside the regions every page loads `fonts.googleapis.com` in the head (privacy/terms :15 and :17, support :16 and :18): chrome, not touched (self-hosting the fonts is plan item LR-3, not in this unit), so the privacy policy must keep disclosing a web-font service (as a category). `landing/index.html` and `landing/open.html` carry no address. `landing/bot/index.html:20` already says `email <a href="mailto:support@getmyez.com">support@getmyez.com</a>` (the LR7 check: the page and the new UA agree).

### 1.6 The twelve date anchors, found by content (CLAUDE.md's `legal_routes.py:30/:47` are stale)

| # | file:line | base text |
|---|---|---|
| 1 | `app/api/legal_routes.py:55` | `"last_updated": "2026-10-11",` (privacy) |
| 2 | `app/api/legal_routes.py:74` | `"last_updated": "2026-10-11",` (terms) |
| 3 | `app/legal/privacy_policy.md:5` | `*Effective date: October 11, 2026*` |
| 4 | `app/legal/terms_of_service.md:5` | same |
| 5 | `app/legal/privacy_policy_ar.md:5` | `*تاريخ السريان: 11 أكتوبر 2026*` |
| 6 | `app/legal/terms_of_service_ar.md:5` | same |
| 7 | `landing/privacy.html:185` | `<p class="subtitle"><em>Effective date: October 11, 2026</em></p>` (inside the region) |
| 8 | `landing/terms.html:174` | same |
| 9 | `landing/ar/privacy.html:179` | AR, inside the region |
| 10 | `landing/ar/terms.html:165` | AR, inside the region |
| 11 | `app/services/consent_service.py:31` | `TERMS_VERSION = "2026-10-11"` |
| 12 | `SmartCompareApp/src/services/consent.ts:12` | `export const TERMS_VERSION = '2026-10-11';` |

Not anchors but must move with them: the four snapshot date lines `tests/fixtures/legal_prefill_u8/{privacy_policy,terms_of_service}{,_ar}.md:5` (the snapshot pin), and three test literals: `tests/test_consent_capture_w3_16.py:39` (`TERMS_VERSION = "2026-10-11"`), `tests/test_legal_docs_u8_polish.py:81` (`AR["DATE_LINE"]`) and `:472` (`"*Effective date: October 11, 2026*"`), `tests/test_legal_disclosure_s77.py:538-539` (`last_updated != "2026-10-11"`, RL1). Anchors 7-10 move by the render, anchors 3-6 by the fill of the snapshot. The jest suites import `TERMS_VERSION` (no literal pin; `landing.brand.s69.test.ts` mentions the date in comments only). The T6 parser (`tests/test_legal_docs_u8.py:647-648`) reads the FIRST `<Month> <D>, <YYYY>` / `<D> <Gulf month> <YYYY>` in each file, so the date line must stay first.

### 1.7 Crawler User-Agent (LR7)

| file:line | definition | use |
|---|---|---|
| `app/services/sitemap_discovery_service.py:387-389` | `_ROBOTS_UA = "%s/1.0 (+https://getmyez.com/bot; contact: <PERSONAL_EMAIL>)" % (robots_eval.NAMED_AGENT)` | `:411` `headers={"User-Agent": _ROBOTS_UA, ...}` |
| `scripts/resolve_search_descriptors.py:80-82` | `USER_AGENT = "%s/1.0 (+https://getmyez.com/bot; contact: <PERSONAL_EMAIL>)" % (robots_eval.NAMED_AGENT)` | `:178` |

These are the only `@gmail.com` literals in `app/`, `scripts/`, `landing/` and `SmartCompareApp/src` (`app/legal/processors.json:163` has the id `"gmail"`, not an address). Pins: `tests/test_domain_s76.py:99-110` (t4: the two literals are equal and contain `(+https://getmyez.com/bot;`; the literal is read by `name\s*=\s*"([^"]*)"\s*%`, so the `"..." % (NAMED_AGENT)` form must stay), `tests/test_robots_unreadable_ruling.py:312` (starts with `NAMED_AGENT`), `tests/test_legal_disclosure_s77.py:675-721` (D9: the files that mention QarenBot / NAMED_AGENT are exactly four; unchanged by this edit). `pyproject.toml:6` and `backend/pyproject.toml:6` carry the personal email in `authors` (not served, not outbound: outside LR7, open question Q9). `tests/test_abuse_detection.py:122` carries a personal-looking `@gmail.com` test value (not served; for the repo masking owner action, Q9).

### 1.8 Is `processors.json` or a vendor list served publicly?

No. `app/api/legal_routes.py:40-75` serves only the four markdown files; `app/main.py` mounts only the admin static dir (`:541-543`); `landing/Dockerfile` copies only `index/privacy/terms/support/open.html`, `bot/`, `.well-known/`, `ar/`; nothing in `SmartCompareApp/src` or `App.tsx` mentions `processors` (grep: 0 hits). The audit's live GETs of `/api/v1/legal/processors` and `getmyez.com/processors.json` were 404. The manifest is public only through the public GitHub repo (owner action OA-3). No route change is proposed.

### 1.9 Machinery behaviour (measured on temp copies under the scratchpad, never the worktree)

- `scripts/fill_in_legal.py --dry-run` on the worktree: rc 0, no `would write` line (idempotent; it writes nothing in dry-run: `run()` returns before any `write_bytes`).
- `scripts/render_legal_landing.py --check`: rc 0 (no stale region).
- Refusal probe (temp copy of the six filled sources, six pages and the renderer, `--variants` pointing at the worktree file): the committed data -> rc 0; `CONTROLLER_NAME` changed -> rc 3 `fork d5_identity (ar, privacy): expected exactly one variant in the text, found none (a value it uses changed after a fill-in? already filled? restore the pre-fill markdown from git and run again)`; `POSTAL_ADDRESS` changed -> the same rc 3 line; after a byte copy of `tests/fixtures/legal_prefill_u8/*.md` over the six sources -> rc 0 and six `would write` lines. So the remedy is exactly "restore from the pre-fill snapshot, then fill"; "from git" in the hint is misleading (git holds the FILLED copies) and must be read as "from the snapshot".

### 1.10 Base pass state (bounded runner, one process at a time)

```
tests/test_legal_docs_u8.py            47 passed  [pyt] tag=base-u8 start=2026-10-14 03:01:32 end=2026-10-14 03:01:47 elapsed=15s bound=600s status=OK rc=0
tests/test_legal_docs_u8_d3c.py        22 passed  [pyt] tag=base-test_legal_docs_u8_d3c start=2026-10-14 03:01:55 end=2026-10-14 03:01:58 elapsed=3s bound=600s status=OK rc=0
tests/test_legal_docs_u8_polish.py     69 passed  [pyt] tag=base-test_legal_docs_u8_polish start=2026-10-14 03:01:58 end=2026-10-14 03:02:09 elapsed=10s bound=600s status=OK rc=0
tests/test_legal_disclosure_s77.py     31 passed  [pyt] tag=base-test_legal_disclosure_s77 start=2026-10-14 03:02:09 end=2026-10-14 03:02:14 elapsed=5s bound=600s status=OK rc=0
tests/test_legal_routes.py             11 passed  [pyt] tag=base-test_legal_routes start=2026-10-14 03:02:14 end=2026-10-14 03:02:18 elapsed=4s bound=600s status=OK rc=0
tests/test_consent_capture_w3_16.py    17 passed  [pyt] tag=base-test_consent_capture_w3_16 start=2026-10-14 03:02:18 end=2026-10-14 03:02:22 elapsed=4s bound=600s status=OK rc=0
tests/test_domain_s76.py                7 passed  [pyt] tag=base-test_domain_s76 start=2026-10-14 03:02:22 end=2026-10-14 03:02:25 elapsed=3s bound=600s status=OK rc=0
tests/test_robots_unreadable_ruling.py 24 passed  [pyt] tag=base-test_robots_unreadable_ruling start=2026-10-14 03:02:25 end=2026-10-14 03:02:28 elapsed=3s bound=600s status=OK rc=0
tests/test_search_descriptor_d3.py     30 passed  [pyt] tag=base-test_search_descriptor_d3 start=2026-10-14 03:02:28 end=2026-10-14 03:02:32 elapsed=4s bound=600s status=OK rc=0
tests/test_u3c_referral_push_name.py   19 passed  [pyt] tag=base-test_u3c_referral_push_name start=2026-10-14 03:02:32 end=2026-10-14 03:02:36 elapsed=3s bound=600s status=OK rc=0
tests/test_landing_fallback_pages_s69.py 11 passed [pyt] tag=base-test_landing_fallback_pages_s69 start=2026-10-14 03:02:36 end=2026-10-14 03:02:38 elapsed=2s bound=600s status=OK rc=0
rest of the comm set (17 files, section 6) 824 passed [pyt] tag=base-comm-rest start=2026-10-14 03:14:11 end=2026-10-14 03:15:45 elapsed=94s bound=1200s status=OK rc=0
```

Every run: `[netguard] blocked 0 attempt(s)`, the hermeticity sentinel clean. Logs: `<scratchpad>/s78legal/base_*.log`.

### 1.11 Line endings

Every file the unit edits is CRLF in the working copy and LF in the index (`core.autocrlf=true`; `git ls-files --eol` shows `i/lf w/crlf`). `fill_in_legal.py` writes the newline style of the source it reads and the renderer keeps the page's own, so a CRLF snapshot gives CRLF output. Whole-file rewrites (the two ToS templates) must be written with CRLF bytes (Python `newline="\r\n"` or bytes), never with an LF writer; check `git diff --stat` shows content lines only.

## 2. Change list, in the order GREEN applies it

Before step A: byte-copy (Python `shutil.copyfile`) every file listed below into `<scratchpad>/s78green_before/` and record its sha256; restore only from those copies, never `git checkout`. NEVER hand-edit `app/legal/*.md` or a landing region: they are outputs of steps C-D.

### A. Templates (the pre-fill snapshot, six files)

1. `tests/fixtures/legal_prefill_u8/privacy_policy.md` and `privacy_policy_ar.md`: date line :5 -> 14 October 2026 (EN `*Effective date: October 14, 2026*`, AR `*تاريخ السريان: 14 أكتوبر 2026*`); s1 :9 (identity line + postal sentence; the AR uses the NEW `<PLACEHOLDER:POSTAL_ADDRESS_AR>`); s5 :75-91 (category list, own-terms sentence, on-request sentence, website paragraph); s7 :99 (countries without vendors); s11 :131 (direct-marketing sentence); s13 :139 and :141 (internals); s15 :151 (material-change notice); s16 :157 (AR postal token becomes `_AR`). Exact texts: section 3.2. Every other line stays byte-identical (T8, T11, d3c (a)-(l), S77 D1-D4, D15, D18 depend on them).
2. `tests/fixtures/legal_prefill_u8/terms_of_service.md` and `terms_of_service_ar.md`: replaced by the ToS v2 templates of section 3.3 (19 sections, same section numbers 1-16 as today; 17 indemnity, 18 general, 19 contact). Sections 2, 4, 8, 9, 10 and the s11 bullets keep their pinned sentences byte-identical (list in section 4.2).
3. `tests/fixtures/legal_prefill_u8/support_contact.md` and `support_contact_ar.md`: line 1 per section 3.1.
4. The forks stay locatable: the inline variant A text of `d5_identity` (new form, step B) must occur exactly once in privacy, terms and support of each language; variant B must not be a substring of A or vice versa.

### B. Fill-in data, variants, manifest

5. `tests/fixtures/legal_fill_in_u8.json`:
   - `trade_name` "" -> `"MYEZ"` (TRADE_NAME_CLAUSE then reads ", trading as MYEZ" / AR "، تحت الاسم التجاري MYEZ").
   - `placeholders.CONTROLLER_NAME` -> `"Husain Aseeri"`.
   - `placeholders.POSTAL_ADDRESS` -> `"Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com)"` (LR1 verbatim).
   - NEW `placeholders.POSTAL_ADDRESS_AR` (insert right after `POSTAL_ADDRESS`, keys stay sorted) -> `"مملكة البحرين (عنواننا البريدي متاح عند الطلب عبر privacy@getmyez.com)"` [AR-NEW].
   - `placeholders.IP_OWNER` -> `"the developer named in section 1"`; `IP_OWNER_AR` -> `"المطوّر المذكور في القسم 1"` [AR-NEW].
   - `_placeholders_comment`: add "POSTAL_ADDRESS / POSTAL_ADDRESS_AR: the controller's postal line in the EN / AR documents (interim since S78, LR1: 'Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com)' and its AR twin; never a residence, a block, road, street, building, flat or house number, a town or area name or coordinates; the later P.O. Box is a two-value re-fill: restore the snapshot, record both values, run the fill-in; no code change)". `_values_comment`: one S78 sentence (name spelling per the App Store Connect account name 2026-10-14; trade name MYEZ; IP_OWNER defined). No personal value in any comment.
   - Leave every other key and the seven flags unchanged.
6. `scripts/legal_variants_u8.json` (texts in section 3):
   - `forks.d5_identity.en.A` = `<PLACEHOLDER:CONTROLLER_NAME>, an individual app developer in the Kingdom of Bahrain<PLACEHOLDER:TRADE_NAME_CLAUSE>`; `en.B` = `<PLACEHOLDER:CONTROLLER_NAME><PLACEHOLDER:TRADE_NAME_CLAUSE> (commercial registration number <PLACEHOLDER:CR_NUMBER>)`; `ar.A` = `<PLACEHOLDER:CONTROLLER_NAME>، مطوّر تطبيقات يعمل بصفة فردية في مملكة البحرين<PLACEHOLDER:TRADE_NAME_CLAUSE>` [AR-NEW]; `ar.B` = `<PLACEHOLDER:CONTROLLER_NAME><PLACEHOLDER:TRADE_NAME_CLAUSE> (السجل التجاري رقم <PLACEHOLDER:CR_NUMBER>)`. The postal token leaves the fork (it becomes plain template text after the fork, so the P.O. Box swap never touches a fork).
   - `clauses.MINORS_CLAUSE.{en,ar}.{privacy,terms}.true`: section 3.2 / 3.3.
   - `clauses.YOUTUBE_CLAUSE.{en,ar}.privacy.on`: category text (section 3.2).
   - `clauses.HOSTING_REGIONS_CLAUSE.en.privacy.nonempty` = `, and in {value}`; `ar.privacy.nonempty` = `، وفي {value}`; `empty` stays `""`.
   - `clauses.TRANSFER_BASIS.{en,ar}.privacy.false`: section 3.2.
   - `clauses.DELETION_SECTION.{en,ar}.terms.043`: section 3.3 (the `old` variants and both privacy variants unchanged).
   - `_comment`: replace the Cloudflare sentence by "The email-providers line of privacy section 5 is plain text in the committed markdown, never a fork or clause (fix P1, amended S78)"; keep the rest.
7. `app/legal/processors.json` (internal manifest, LR3): add to every row three keys after `gate_flag`: `"category_en"`, `"category_ar"`, `"public_name"` (values below), and rewrite `_comment`: "category_en / category_ar must appear in privacy_policy.md / privacy_policy_ar.md (T7a); name_en / name_ar must appear there only when public_name is true (OpenAI, Apple, Google sign-in, retailer websites: LR3) and must not appear otherwise; ..." keeping the ProductImage / retailer-row sentence (polish Q5 pins it) and the NOT_PERSONAL sentence. Row ids, modules, hosts and gate flags are unchanged (T7b / T7c keep their meaning).

| id | category_en | category_ar | public_name |
|---|---|---|---|
| supabase | `database and sign-in provider` | `مزوّد قاعدة البيانات وتسجيل الدخول` | false |
| railway | `hosting provider` | `مزوّد الاستضافة` | false |
| upstash | `temporary-storage provider` | `مزوّد التخزين المؤقت` | false |
| sentry | `error-reporting provider` | `مزوّد تقارير الأخطاء` | false |
| openai | `OpenAI` | `OpenAI` | true |
| expo_push | `notification and update provider` | `مزوّد الإشعارات والتحديثات` | false |
| eas_update | `notification and update provider` | `مزوّد الإشعارات والتحديثات` | false |
| apple | `Apple` | `Apple` | true |
| google_sign_in | `Google` | `Google` | true |
| google_fonts | `web-font service` | `خدمة خطوط على الويب` | false |
| serper, bright_data, firecrawl, scrapedo | `search and page-retrieval providers` | `مزوّدو البحث على الويب واسترجاع الصفحات` | false |
| cloudflare | `email-routing service` | `خدمة لتوجيه البريد الإلكتروني` | false |
| gmail | `mailbox provider` | `مزوّد صندوق بريدنا` | false |
| youtube (gated, off) | `video search service` | `خدمة للبحث عن مقاطع الفيديو` | false |
| retailers | `retailer websites` | `مواقع المتاجر` | true |

Each category string is a whole-word substring of the section 3.2 text it names (verify with the T7a `_name_in` helper before running the fill).

### C. Restore, then fill (the refusal handling)

8. Because the six live sources are already filled and step B changes values inside the `d5_identity` fork, a direct `fill_in_legal.py` run refuses with rc 3 `fork d5_identity ... found none (a value it uses changed after a fill-in? ...)` and writes nothing (measured, section 1.9). The remedy, and the only allowed path:
   1. byte-copy each EDITED snapshot file `tests/fixtures/legal_prefill_u8/<name>.md` over `app/legal/<name>.md` (Python `shutil.copyfile`; the snapshot is CRLF, so the output stays CRLF); sha256-compare source and destination;
   2. run `PYTHONIOENCODING=utf-8 <venv python> scripts/fill_in_legal.py --dry-run` -> rc 0 and six `would write` lines;
   3. run `PYTHONIOENCODING=utf-8 <venv python> scripts/fill_in_legal.py` -> rc 0, `wrote:` six sources and `rendered:` six pages (the script renders the six landing regions itself, step D);
   4. run the dry-run again -> rc 0 with no `would write` line (idempotent; `test_fix_b1_fill_in_rerun_with_the_same_data_changes_nothing`).
   If any step exits 2 (a null) or 3 (inconsistent), stop, fix the template / variant / data, restore from the snapshot again and repeat; never edit the filled output.

### D. Render

9. Step C.3 already rewrote the six regions. Run `<venv python> scripts/render_legal_landing.py --check` -> rc 0 and no `stale:` line. Never run the renderer without `--check` after a manual edit; there is none.

### E. Code

10. `app/api/legal_routes.py`: add `from app.services.consent_service import TERMS_VERSION` and use `"last_updated": TERMS_VERSION` at :55 and :74 (anchors 1-2 become derived: LR4's single source; `consent_service` imports only stdlib and fastapi, so there is no cycle; T9's no-`Query()` AST pin and `get_terms_of_service()` without arguments keep working).
11. `app/services/consent_service.py:31` `TERMS_VERSION = "2026-10-14"`.
12. `SmartCompareApp/src/services/consent.ts:12` `export const TERMS_VERSION = '2026-10-14';` (reaches phones only with the first post-approval OTA; no OTA before approval, LR4).
13. `app/services/sitemap_discovery_service.py:387` and `scripts/resolve_search_descriptors.py:80`: the literal becomes `"%s/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)"` (keep the `% (robots_eval.NAMED_AGENT)` form and the CRLF bytes; the formatted value is `QarenBot/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)`, LR7). No other code change.

### F. Pins and new tests

14. Apply the pin edits of section 4.1 (each one listed with its reason), add `POSTAL_ADDRESS_AR` to the synthetic data sets (polish `COMPLETE_VALUES`, `tests/fixtures/legal_d3c_u8.json` `ar_values`), update `tests/fixtures/legal_d3c_u8.json` (`fix3_ar.s5_own_terms`, `fix2_ar.hosting_roles` semantics) and `tests/fixtures/legal_disclosure_s77.json` (`privacy_s5_google_ar`, `privacy_s5_cloudflare_ar`, `privacy_s5_own_terms_ar`, `privacy_s7_transfer_ar`, add the retired AR sentences to `retired_ar`).
15. `SmartCompareApp/__tests__/landing.brand.s69.test.ts:60-74` `ADDRESS_COUNTS`: re-measure the six legal pages after step C with the same regex the test uses (`/qaren\.app|getmyez\.com/g` on the whole page) and write the measured numbers (expected, to be confirmed by the measurement: privacy 14, ar/privacy 14 = 11 + the two postal lines carrying privacy@ + the on-request sentence; terms 13, ar/terms 13 = the 5 chrome mentions + 8 in the region (s1 postal and contact, s7, s13, s15, s19 x3); support 11, ar/support 11); the pytest mirror `tests/test_legal_disclosure_s77.py:956` `PRIVACY_PAGE_ADDRESSES` takes the measured privacy value.
16. The RED file(s) of section 5 already exist (written by the RED agent); GREEN only makes them pass (it may fill the AR fixture strings the RED left for the native-review list, never weaken an assertion).

### G. Re-date recipe if the merge slips past 2026-10-14 (one mechanical commit by the orchestrator)

Replace the date in exactly these places and nothing else: the four snapshot date lines (step A), restore + fill (step C), `consent_service.py:31`, `consent.ts:12`, `tests/test_consent_capture_w3_16.py:39`, then `render_legal_landing.py --check`. Every other test derives the date from `consent_service.TERMS_VERSION` (section 4.1 makes the polish and S77 date pins derive it). The AR date uses Western digits and the Gulf month table of `tests/test_legal_docs_u8.py:633-646`.

## 3. Full proposed text (template form: tokens as they stand in the pre-fill snapshot)

Conventions: `<CN>` = `<PLACEHOLDER:CONTROLLER_NAME>`, `<TNC>` = `<PLACEHOLDER:TRADE_NAME_CLAUSE>`, `<PA>` / `<PA_AR>` = `<PLACEHOLDER:POSTAL_ADDRESS>` / `<PLACEHOLDER:POSTAL_ADDRESS_AR>`, `<SE>` = `<PLACEHOLDER:SUPPORT_EMAIL>`, `<PE>` = `<PLACEHOLDER:PRIVACY_EMAIL>`; write the full tokens in the files. `[AR-NEW]` marks every Arabic sentence that is new or changed (the native-review list, D11); unmarked Arabic is byte-identical to the base. Markdown subset: one line per list item, a blank line between a list and the next paragraph (the renderer refuses a non-item line right after an item). Pre-checked against the rules every new sentence must pass: T1 (no "draft", "template" except "message templates", no AR "draft" / "template" / "legal counsel" words), T3 (no old brand, no standalone AR old-brand word), the UL12 copy policy (no AR banned or scary word: the scary list matches substrings, so no word containing its four entries), the d3c (k) personal-data claim scan (EN and AR), the S77 D4 not-sold rule, and `tests/test_legal_routes.py` (the ToS keeps "3 successful invites per device" and "7 days", never "expire 30 days").

### 3.1 Controller identity and the interim postal line (privacy s1, ToS s1, support)

Filled readings (after step C):

- EN privacy s1: `MYEZ (the "App") is provided by Husain Aseeri, an individual app developer in the Kingdom of Bahrain, trading as MYEZ ("we", "us"). Postal address: Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com). We decide how and why your personal data is processed in the App. Contact: privacy@getmyez.com.`
- AR privacy s1: `ميّز («التطبيق») تطبيق يقدّمه Husain Aseeri، مطوّر تطبيقات يعمل بصفة فردية في مملكة البحرين، تحت الاسم التجاري MYEZ («نحن»). العنوان البريدي: مملكة البحرين (عنواننا البريدي متاح عند الطلب عبر privacy@getmyez.com). ونحن من يقرّر كيف تُعالَج بياناتك الشخصية في التطبيق ولماذا. للتواصل: privacy@getmyez.com.` [AR-NEW: the field of activity, the trade-name reading, the postal sentence]

Templates:

| doc | EN template | AR template |
|---|---|---|
| privacy s1 (:9) | `MYEZ (the "App") is provided by <d5 fork> ("we", "us"). Postal address: <PA>. We decide how and why your personal data is processed in the App. Contact: <PE><PLACEHOLDER:DPO_CONTACT>.` | `ميّز («التطبيق») تطبيق يقدّمه <d5 fork> («نحن»). العنوان البريدي: <PA_AR>. ونحن من يقرّر كيف تُعالَج بياناتك الشخصية في التطبيق ولماذا. للتواصل: <PE><PLACEHOLDER:DPO_CONTACT>.` [AR-NEW: "العنوان البريدي: ..." sentence] |
| privacy s16 (:157) | `- **Postal address:** <PA>` (unchanged) | `- **العنوان البريدي:** <PA_AR>` |
| support (:1) | `MYEZ is provided by <d5 fork>. Postal address: <PA>.` | `مقدّم تطبيق ميّز: <d5 fork>. العنوان البريدي: <PA_AR>.` [AR-NEW] |
| ToS s1 / s19 | section 3.3 | section 3.3 |

`<d5 fork>` = the inline variant A of step 6: EN `<CN>, an individual app developer in the Kingdom of Bahrain<TNC>`, AR `<CN>، مطوّر تطبيقات يعمل بصفة فردية في مملكة البحرين<TNC>` [AR-NEW]. Postal values (step 5): EN `Kingdom of Bahrain (our postal address is available on request at privacy@getmyez.com)`, AR `مملكة البحرين (عنواننا البريدي متاح عند الطلب عبر privacy@getmyez.com)` [AR-NEW]. The name appears only in privacy s1, ToS s1 and the support line (LR2); privacy s16 and ToS s19 carry the postal line and the role addresses only.

### 3.2 Privacy policy: every changed or new clause

**s5 Who receives your data (replaces :75-85; the carve-out sentence and the invite paragraph :89 are unchanged).** Order: the named recipients first, then the categories.

| EN | AR |
|---|---|
| `- **OpenAI:** identifies products and writes comparisons (section 4).` (unchanged) | `- **OpenAI:** تحدد المنتجات وتكتب المقارنات (القسم 4).` (unchanged) |
| `- **Apple:** only if you use Sign in with Apple. Apple shares your email address, or a private relay address, with us. Apple also delivers notifications to iPhones.` (unchanged) | `- **Apple:** فقط إذا استخدمت تسجيل الدخول عبر Apple. تشارك Apple معنا عنوان بريدك الإلكتروني أو عنوان ترحيل خاصًا. كما توصل Apple الإشعارات إلى أجهزة iPhone.` (unchanged) |
| `- **Google:** if you use Google Sign-In, Google shares your name, email address and profile picture with us through its sign-in token.` (the mailbox sentence is removed) | `- **Google:** إذا استخدمت تسجيل الدخول عبر Google، تشارك Google معنا اسمك وعنوان بريدك الإلكتروني وصورة ملفك الشخصي عبر رمز تسجيل الدخول الخاص بها.` (the mailbox sentence is removed) |
| `- **Our database and sign-in provider:** stores your account and the records described in section 3, and sends sign-in emails such as password resets.` | `- **مزوّد قاعدة البيانات وتسجيل الدخول لدينا:** يخزّن حسابك والسجلات الموضحة في القسم 3، ويرسل رسائل تسجيل الدخول مثل رسائل إعادة تعيين كلمة المرور.` [AR-NEW] |
| `- **Our hosting provider:** runs our servers. Its logs can record each request to our servers, including the IP address it came from and the web address requested, which for a comparison can include the product names.` | `- **مزوّد الاستضافة لدينا:** يشغّل خوادمنا. وقد تسجّل سجلاته كل طلب يصل إلى خوادمنا، بما في ذلك عنوان IP الذي صدر منه وعنوان الويب (URL) المطلوب، والذي قد يتضمن أسماء المنتجات في حالة المقارنة.` [AR-NEW] |
| `- **Our temporary-storage provider:** holds usage counters, sign-in security checks and short-lived copies of data that make the App faster.` | `- **مزوّد التخزين المؤقت لدينا:** يحفظ عدادات الاستخدام وعمليات التحقق الأمني عند تسجيل الدخول ونسخًا قصيرة العمر من البيانات تجعل التطبيق أسرع.` [AR-NEW] |
| `- **Our error-reporting provider:** receives error and performance reports from our servers and from the App (section 13).` | `- **مزوّد تقارير الأخطاء لدينا:** يتلقى تقارير الأخطاء والأداء من خوادمنا ومن التطبيق (القسم 13).` [AR-NEW] |
| `- **Our notification and update provider:** delivers notifications (through Apple's notification service) and App updates. It receives your notification token and the text of each notification, and your device's requests for updates.` | `- **مزوّد الإشعارات والتحديثات لدينا:** يوصل الإشعارات (عبر خدمة الإشعارات من Apple) وتحديثات التطبيق. ويتلقى رمز الإشعارات الخاص بك ونص كل إشعار، وطلبات جهازك للحصول على التحديثات.` [AR-NEW] |
| `- **Web search and page-retrieval providers:** receive product search terms and retailer page addresses, never your identity<PLACEHOLDER:YOUTUBE_CLAUSE>.` | `- **مزوّدو البحث على الويب واسترجاع الصفحات:** يتلقون عبارات البحث عن المنتجات وعناوين صفحات المتاجر، ولا يتلقون هويتك أبدًا<PLACEHOLDER:YOUTUBE_CLAUSE>.` [AR-NEW] |
| `- **Our email providers:** an email-routing service receives the email you send to our addresses and forwards it to our mailbox provider, which stores it under its own terms.` | `- **مزوّدو البريد الإلكتروني لدينا:** تتلقى خدمة لتوجيه البريد الإلكتروني الرسائل التي ترسلها إلى عناويننا وتعيد توجيهها إلى مزوّد صندوق بريدنا، الذي يخزّنها وفق شروطه الخاصة.` [AR-NEW] |
| `- **The retailer websites and store search services we query:** see section 6.` | `- **مواقع المتاجر وخدمات البحث في المتاجر التي نستعلم منها:** انظر القسم 6.` [AR-NEW] |

Paragraph after the list (:87). The first sentence is byte-identical (d3c (n) pins it); the second changes; the third is new; the fourth is unchanged:

- EN: `Except as section 4 describes for OpenAI, each of our service providers processes data only to provide its service to us, and we require each of them to protect it at least as well as this policy does. Retailer websites (section 6), the sign-in providers Apple and Google, and our mailbox provider act under their own terms. We will tell you the names of our service providers on request at <PE>. We may also disclose data where the law requires it.`
- AR: `باستثناء ما يوضّحه القسم 4 بشأن OpenAI، يعالج كل مزوّد من مزوّدي الخدمات لدينا البيانات فقط لتقديم خدمته لنا، ونُلزم كلًّا منهم بحمايتها بمستوى لا يقل عن المستوى الذي تنص عليه هذه السياسة. أما مواقع المتاجر (القسم 6) ومزوّدا تسجيل الدخول Apple وGoogle، ومزوّد صندوق بريدنا، فتعمل وفق شروطها الخاصة. وسنخبرك بأسماء مزوّدي الخدمات لدينا عند الطلب عبر <PE>. وقد نفصح أيضًا عن البيانات عندما يقتضي القانون ذلك.` [AR-NEW: the second and third sentences]

The filled EN third sentence is exactly LR3's "We will tell you the names of our service providers on request at privacy@getmyez.com."

Website paragraph (:91):

- EN: `When you visit our website, our hosting provider can log your request, including your IP address, and the pages load fonts from a web-font service, which receives your IP address.`
- AR: `عند زيارتك لموقعنا الإلكتروني، يمكن لمزوّد الاستضافة لدينا تسجيل طلبك، بما في ذلك عنوان IP الخاص بك، كما تحمّل الصفحات خطوطًا من خدمة خطوط على الويب، تتلقى عنوان IP الخاص بك.` [AR-NEW]

`YOUTUBE_CLAUSE` on (flag off today; the text keeps LR3 true if it is ever turned on):

- EN: `; a video search service receives product names when we look for review videos`
- AR: `؛ وتتلقى خدمة للبحث عن مقاطع الفيديو أسماء المنتجات عندما نبحث عن مقاطع فيديو للمراجعات` [AR-NEW]

**s7 Transfers outside Bahrain (:99).** The countries are the ones the base text names (OpenAI and Google: United States; Sentry: Germany; `HOSTING_REGIONS`: India and Singapore), without the vendor mapping (LR3). The basis sentence is no stronger than today's (no adequacy claim, no Art 12/13 claim).

- EN template: `Our providers process data outside Bahrain, including in the United States and Germany (European Union)<PLACEHOLDER:HOSTING_REGIONS_CLAUSE>. <PLACEHOLDER:TRANSFER_BASIS>`
- AR template: `يعالج مزوّدونا البيانات خارج البحرين، بما في ذلك في الولايات المتحدة وألمانيا (الاتحاد الأوروبي)<PLACEHOLDER:HOSTING_REGIONS_CLAUSE>. <PLACEHOLDER:TRANSFER_BASIS>` [AR-NEW]
- `HOSTING_REGIONS_CLAUSE` nonempty: EN `, and in {value}`, AR `، وفي {value}`.
- `TRANSFER_BASIS` false: EN `We transfer data to our service providers, which are required by contract to protect it, and to our mailbox provider, which handles email under its own terms (section 5).`; AR `ننقل البيانات إلى مزوّدي الخدمات لدينا، وهم ملزَمون تعاقديًا بحمايتها، وإلى مزوّد صندوق بريدنا، الذي يتعامل مع رسائل البريد الإلكتروني وفق شروطه الخاصة (القسم 5).` [AR-NEW]
- Filled EN: `Our providers process data outside Bahrain, including in the United States and Germany (European Union), and in India and Singapore. We transfer data to our service providers, which are required by contract to protect it, and to our mailbox provider, which handles email under its own terms (section 5).`

**s11 Notifications (:131): one new sentence (PDPL Art 17(1)(c)(4)).**

- EN: `... We do not send advertising. We do not use your personal data for direct marketing. <PLACEHOLDER:INAPP_NOTIF_CLAUSE>`
- AR: `... لا نرسل إعلانات. ولا نستخدم بياناتك الشخصية للتسويق المباشر. <PLACEHOLDER:INAPP_NOTIF_CLAUSE>` [AR-NEW]

**s12 Children (`MINORS_CLAUSE` privacy true, LR5.3 consistency):**

- EN: ` If you are under 18, or under the age of majority where you live if that is higher, a parent or guardian must agree to this policy and to our Terms of Service for you.`
- AR: ` وإذا كان عمرك أقل من 18 عامًا، أو كنت دون سن الرشد في مكان إقامتك إن كان أعلى من ذلك، فيجب أن يوافق أحد والديك أو وليّ أمرك على هذه السياسة وعلى شروط الاستخدام نيابةً عنك.` [AR-NEW]

**s13 Security (:139, :141; LR6).** Paragraph 1 replaced; paragraph 2 changes only its server subject; paragraph 3 unchanged.

- EN p1: `Data is encrypted in transit (HTTPS/TLS), and the App checks our server's identity before sending data. Your sign-in tokens are kept in your device's secure storage.`
- AR p1: `تُشفَّر البيانات أثناء نقلها (HTTPS/TLS)، ويتحقق التطبيق من هوية خادمنا قبل إرسال البيانات. وتُحفظ رموز تسجيل الدخول الخاصة بك في وحدة التخزين الآمنة على جهازك.` [AR-NEW]
- EN p2: replace `From our servers, Sentry receives exception types,` by `From our servers, our error-reporting provider receives exception types,`; every other word of p2 stays (the UF7 sentences, "Reports from the App can include", "Performance traces from the App record the same request addresses.", "Performance traces from our servers").
- AR p2: replace `يتلقى Sentry من خوادمنا أنواع الاستثناءات` by `يتلقى مزوّد تقارير الأخطاء لدينا من خوادمنا أنواع الاستثناءات` [AR-NEW]; every other word stays (polish A13 pins "ولا متون الطلبات").
- s14 (on-device data, "(Keychain)") is unchanged: it names Apple's own secure store, which is a user-facing fact (items survive app deletion), not our infrastructure.

**s15 Changes (:151):**

- EN: `If we change this policy, we will update the effective date above and publish the new version in the App and on our website. If a change is material, we will also announce it in the App or on our website before it takes effect.`
- AR: `إذا غيّرنا هذه السياسة، فسنحدّث تاريخ السريان أعلاه وننشر النسخة الجديدة في التطبيق وعلى موقعنا الإلكتروني. وإذا كان التغيير جوهريًا، فسنعلن عنه أيضًا في التطبيق أو على موقعنا الإلكتروني قبل سريانه.` [AR-NEW: the second sentence]

Untouched privacy sections (byte-identical): s2 (including the aggregated-statistics sentence, D9), s3.1-3.6, s4 (the d3 = C paragraph, the consent-sheet restatement), s6, s8, s9 (DELETION_SECTION 043 and the email sentence), s10, s14. LR6 completeness after the change: what is collected and how (s3), every use (s3.6, s4), the equal-protection confirmation (s5 carve-out sentence, carving out OpenAI and the mailbox as today), retention and deletion (s8, s9), consent withdrawal (s4, s10), the deletion request path including the in-app path (s9, s10), access / correction / deletion / objection / restriction and the PDPA complaint (s10), children 13+ (s12), security (s13), transfers (s7), changes (s15), contact (s16).

### 3.3 Terms of Service v2 (full templates, EN then AR)

Numbering: sections 1-16 keep today's numbers and roles (s2, s4, s8, s9, s11 and s13 are pinned by number); 17 (indemnity) and 18 (general) are new; contact moves from 17 to 19. Cross-references updated: s1 -> section 16; s4 -> section 9; s5 -> section 8; s8 -> section 4 of the Privacy Policy; s13 survival list -> sections 8, 11, 12, 15, 17 and 18; the 043 deletion variant -> section 9 of the Privacy Policy and section 8. No other document cites a ToS section number (grep: privacy cites the Terms by name only). LR5 item -> section: 1 party (s1), 2 Apple (s16), 3 eligibility (s3 + MINORS_CLAUSE), 4 AI accuracy / no advice (s6, with s11 bullets), 5 third parties (s7), 6 inputs + OpenAI exchange (s8), 7 acceptable use (s5), 8 IP (s8), 9 suspension / termination / deletion (s13), 10 warranties + limitation with carve-outs (s11, s12), 11 narrow indemnity (s17, subject to counsel), 12 changes (s14), 13 governing law (s15), 14 boilerplate (s18), 15 contact (s19).

#### EN template (`tests/fixtures/legal_prefill_u8/terms_of_service.md`)

```
# Terms of Service

**MYEZ**

*Effective date: October 14, 2026*

## 1. Agreement and who we are

These Terms of Service ("Terms") are an agreement between you and <PLACEHOLDER:CONTROLLER_NAME>, an individual app developer in the Kingdom of Bahrain<PLACEHOLDER:TRADE_NAME_CLAUSE> ("we", "us"), the provider of MYEZ (the "App"). Postal address: <PLACEHOLDER:POSTAL_ADDRESS>. You can contact us at <PLACEHOLDER:SUPPORT_EMAIL>. By creating an account or using the App you agree to these Terms. If you do not agree, do not use the App. If you downloaded the App from the Apple App Store, these Terms are between you and us only, not Apple (section 16).

## 2. The service

MYEZ helps you compare two products. It gathers reviews and prices from public sources, uses AI to compile specifications from search results and, where those say nothing, from the AI model's general knowledge, and uses AI to write a verdict. MYEZ is a decision aid: it does not sell products, and prices come from third-party retailers and can change. We may change, add or remove features of the App, and we may stop offering the App or part of it.

## 3. Eligibility and your account

- You must be at least 13 years old to create an account.<PLACEHOLDER:MINORS_CLAUSE>
- You must give accurate information when you create an account.
- You are responsible for keeping your sign-in details secure and for activity under your account.
- One account per person. Creating accounts by automated means is not allowed.
- If you sign in with Apple or Google, their own terms also apply to that sign-in.

## 4. Free use and limits

Use of MYEZ is free. Each account can run a limited number of comparisons (currently up to 3 a day and up to 10 a month; your first 3 comparisons count toward these limits, and the referral rewards described in section 9 add to the monthly limit). Limits can differ between accounts, and we may change them. This version of the App sells no subscriptions or in-app purchases, and these Terms give you no right to a paid tier or to higher limits.

## 5. Acceptable use

You agree not to:

- use the App for any unlawful purpose, or to look up, compare or obtain products in order to harm yourself or others;
- send abusive, threatening or hateful content, or content that infringes someone else's rights, through any input (text, image or link);
- photograph or upload people, identity or other documents, payment cards or other personal or health details (see section 8);
- access the App or our servers by automated means (such as bots, scripts or scrapers), collect data from the App by automated means, or use the App to build a competing product or dataset;
- reverse-engineer, decompile or disassemble the App, except where the law allows this despite this restriction;
- get around usage limits, for example by creating several accounts or by resetting or disguising your device;
- interfere with or disrupt the App or our servers, or try to make the AI ignore its instructions through what you enter;
- impersonate another person or misrepresent who you are;
- present a comparison, or an edited version of one, as a statement by MYEZ when it is not, or use the App to make automated purchasing decisions without human review.

## 6. AI-generated content and accuracy

Verdicts, summaries, specifications and recommendations are generated by AI from public information and may be incomplete, wrong or out of date. Prices, availability, specifications and ratings come from third-party sources and can change or differ at the retailer; prices may be converted from another currency and may not include delivery, customs or taxes. Check them with the retailer before you buy.

Nothing in MYEZ is professional, medical, health, financial or legal advice. This also applies to comparisons of supplements, skincare and other health or beauty products: read the product label and follow its directions, and ask a doctor or pharmacist before you start, stop or change a medicine or supplement, especially if you are pregnant, have a medical condition or take other medicines. MYEZ does not calculate doses and is not for emergencies; in an emergency, contact your local emergency services.

## 7. Retailers, brands and links

MYEZ does not sell products and is not a party to any purchase. Links take you to third-party retailer websites that we do not control; any purchase is between you and the retailer, under the retailer's terms. We are not responsible for their products, prices, stock, delivery, returns or terms. If you believe information in MYEZ about your product or business is wrong, email <PLACEHOLDER:SUPPORT_EMAIL>.

## 8. Intellectual property, your content and our AI provider

The App, its design, code and branding belong to <PLACEHOLDER:IP_OWNER> (or are licensed to us). Product information and reviews, and retailer, brand and product names, belong to their owners; we use those names only to identify the products compared, and their appearance in MYEZ does not mean that their owners endorse MYEZ or that we endorse them. Your account's comparison history is yours to view, share and delete, and is handled under our Privacy Policy. You grant us a worldwide, royalty-free licence to use the content you submit to MYEZ (your queries, photos, links, feedback and preferences) to operate, secure and improve the service, to create de-identified comparison and preference datasets, and to obtain comparisons from our AI provider as our Privacy Policy describes. Our AI provider is OpenAI; section 4 of our Privacy Policy lists what we send it, and the App asks your permission before your first comparison. We own the de-identified comparison data that MYEZ compiles (the products compared, the verdicts and scores, the prices gathered and de-identified search queries) and the preference and usage statistics we derive from it in aggregated or anonymised form. We may use this data to operate and improve MYEZ, and we may share, license or sell aggregated or anonymised statistics derived from it (for example price trends or category popularity) to third parties; none of it identifies you. Apart from OpenAI's data-sharing programme described below, we do not sell or otherwise exchange your personal data for anything of value, and we do not share it with data brokers or advertisers. We take part in OpenAI's data-sharing programme, as section 4 of our Privacy Policy describes: OpenAI may use the inputs we send it and the outputs it generates from them to evaluate and train its models, and in return OpenAI gives us some free use of its service. Do not enter, photograph or link to content that you do not have the right to share, or personal or health details of yourself or others.

## 9. Smart Decision Referrals

(byte-identical to base terms_of_service.md:52-58)

## 10. Notifications

(byte-identical to base :62, with <PLACEHOLDER:INAPP_NOTIF_CLAUSE>)

## 11. Disclaimer of warranties

To the extent permitted by applicable law, the App is provided "as is" and "as available", without warranties of any kind, express or implied, including any implied warranty that the App is fit for a particular purpose, accurate or available without interruption. Where applicable law does not allow some of these exclusions, they apply to you only as far as that law allows.

(the four bullets of base :68-71, byte-identical: Prices / Specifications / Reviews / Recommendations)

## 12. Limitation of liability

Nothing in these Terms excludes or limits our liability for fraud, gross negligence or wilful misconduct, for death or personal injury, or for anything else that the law does not allow us to exclude or limit. Subject to that, and to the extent permitted by applicable law, we are not liable for:

- purchasing decisions you make based on information in the App;
- inaccurate prices, specifications or reviews;
- interruptions or downtime of the service;
- any indirect, incidental or consequential damages.

## 13. Suspension, termination and deletion

We may suspend or end your access to the App if you break these Terms, if the law requires it, or to protect users, the App or others. Where it is practical and lawful, we will tell you why, and you can ask us to review the decision by emailing <PLACEHOLDER:SUPPORT_EMAIL>. When your access ends, your right to use the App ends; sections 8, 11, 12, 15, 17 and 18 continue to apply.

<PLACEHOLDER:DELETION_SECTION>

## 14. Changes to these Terms

We may change these Terms, for example when the App or the law changes. If we do, we will update the effective date above and publish the new version in the App and on our website. If a change is material, we will also announce it in the App or on our website before it takes effect, unless the change is needed urgently for legal or security reasons. Where the law allows, if you keep using the App after a change takes effect, the changed Terms apply to you; if you do not agree, stop using the App and delete your account.

## 15. Governing law and disputes

These Terms are governed by the laws of <PLACEHOLDER:GOVERNING_LAW>. If a dispute arises, we will first try to resolve it with you informally; please email <PLACEHOLDER:SUPPORT_EMAIL>. If that does not work, the competent courts of <PLACEHOLDER:GOVERNING_LAW> will decide it. If you use the App as a consumer, nothing in these Terms takes away the protection you have under the mandatory laws of the country where you live.

## 16. Apple

If you downloaded the App from the Apple App Store, this section also applies:

- These Terms are an agreement between you and us only, not with Apple. We, not Apple, are solely responsible for the App and its content.
- Apple's Licensed Application End User License Agreement (the "Standard EULA") governs your licence to use the App software, and these Terms govern your use of the MYEZ service. If they conflict, the Standard EULA applies to the App software and these Terms apply to the service.
- Apple has no obligation to provide any maintenance or support for the App.
- If the App fails to conform to any applicable warranty, you may notify Apple, and Apple may refund the purchase price of the App to you (the App is free, so that amount is zero); to the extent permitted by law, Apple has no other warranty obligation for the App. As between you, us and Apple, any other claims, losses, liabilities, damages, costs or expenses caused by a failure to conform to a warranty are our responsibility, not Apple's, subject to sections 11 and 12.
- As between us and Apple, we, not Apple, are responsible for addressing any claims by you or a third party relating to the App or your use of it, including product liability claims, claims that the App fails to meet a legal or regulatory requirement, and claims under consumer protection, privacy or similar laws.
- If a third party claims that the App or your use of it infringes their intellectual property rights, we, not Apple, are solely responsible for investigating, defending, settling and discharging that claim.
- You confirm that you are not located in a country that is subject to a United States Government embargo or that the United States Government has designated as a "terrorist supporting" country, and that you are not on any United States Government list of prohibited or restricted parties.
- You must comply with any third-party terms that apply when you use the App, such as your mobile carrier's or internet provider's data terms and the terms of Sign in with Apple or Google Sign-In.
- Apple and its subsidiaries are third-party beneficiaries of these Terms. Once you accept these Terms, Apple has the right (and is deemed to have accepted the right) to enforce them against you as a third-party beneficiary.

## 17. Your responsibility for unlawful use

To the extent the law allows, you agree to compensate us for losses, damages and reasonable costs (including reasonable legal fees) that we suffer because of a third party's claim, where that claim results from your unlawful use of the App or from your breach of section 5. This does not apply to the extent that the loss was caused by our own fault.

## 18. General

- **Entire agreement:** these Terms, our Privacy Policy and, if you downloaded the App from the Apple App Store, the Standard EULA are the entire agreement between you and us about the App.
- **Severability:** if a court finds any part of these Terms invalid or unenforceable, the rest stays in effect.
- **No waiver:** if we do not enforce a right under these Terms straight away, we can still enforce it later.
- **Assignment:** you may not transfer your rights or obligations under these Terms. We may transfer ours to a successor that takes over the App, for example a company we set up to run it; this will not reduce your rights under these Terms.
- **Language:** these Terms are published in English and Arabic and both versions are meant to say the same thing; if they differ, the version more favourable to you applies.

## 19. Contact

- **Questions about these Terms:** <PLACEHOLDER:SUPPORT_EMAIL>
- **Privacy questions:** <PLACEHOLDER:PRIVACY_EMAIL>
- **Postal address:** <PLACEHOLDER:POSTAL_ADDRESS>
```

`MINORS_CLAUSE` terms true (EN): ` If you are under 18, or under the age of majority where you live if that is higher, you may use the App only with the permission of a parent or guardian, who must agree to these Terms for you and is responsible for your use of the App.`

`DELETION_SECTION` terms 043 (EN): `You can delete your account in the App at any time (Profile, then the settings icon, then Delete account). Section 9 of our Privacy Policy describes what deleting your account removes and the records we keep. Deleting your account does not delete data already shared with OpenAI under its data-sharing programme, which is governed by OpenAI's terms (section 4 of our Privacy Policy).`

#### AR template (`tests/fixtures/legal_prefill_u8/terms_of_service_ar.md`)

```
# شروط الاستخدام

**ميّز (MYEZ)**

*تاريخ السريان: 14 أكتوبر 2026*

## 1. الاتفاق ومن نحن

تُعدّ شروط الاستخدام هذه («الشروط») اتفاقًا بينك وبين <PLACEHOLDER:CONTROLLER_NAME>، مطوّر تطبيقات يعمل بصفة فردية في مملكة البحرين<PLACEHOLDER:TRADE_NAME_CLAUSE> («نحن»)، مقدّم تطبيق ميّز («التطبيق»). العنوان البريدي: <PLACEHOLDER:POSTAL_ADDRESS_AR>. ويمكنك التواصل معنا على <PLACEHOLDER:SUPPORT_EMAIL>. بإنشائك حسابًا أو استخدامك التطبيق، فإنك توافق على هذه الشروط. وإذا كنت لا توافق عليها، فلا تستخدم التطبيق. وإذا نزّلت التطبيق من متجر App Store التابع لشركة Apple، فإن هذه الشروط اتفاق بينك وبيننا فقط، وليست اتفاقًا مع Apple (القسم 16).

## 2. الخدمة

يساعدك ميّز على المقارنة بين منتجين. فهو يجمع المراجعات والأسعار من مصادر عامة، ويستخدم الذكاء الاصطناعي لتجميع المواصفات من نتائج البحث، ومن المعرفة العامة لنموذج الذكاء الاصطناعي حين لا تذكرها تلك النتائج، ولكتابة خلاصة المقارنة. ميّز أداة مساعدة على اتخاذ القرار: لا يبيع المنتجات، والأسعار مصدرها متاجر تابعة لأطراف ثالثة وقد تتغير. وقد نغيّر ميزات التطبيق أو نضيف إليها أو نزيل بعضها، وقد نتوقف عن تقديم التطبيق أو جزء منه.

## 3. الأهلية وحسابك

- يجب ألا يقل عمرك عن 13 عامًا لإنشاء حساب.<PLACEHOLDER:MINORS_CLAUSE>
- يجب أن تقدّم معلومات دقيقة عند إنشاء حسابك.
- أنت مسؤول عن الحفاظ على أمان بيانات تسجيل الدخول الخاصة بك، وعمّا يجري من خلال حسابك.
- حساب واحد لكل شخص. ولا يُسمح بإنشاء الحسابات بوسائل آلية.
- إذا سجّلت الدخول عبر Apple أو Google، فإن شروطهما الخاصة تسري أيضًا على تسجيل الدخول هذا.

## 4. الاستخدام المجاني وحدوده

استخدام ميّز مجاني. يمكن لكل حساب إجراء عدد محدود من المقارنات (حاليًا ما يصل إلى 3 مقارنات في اليوم وما يصل إلى 10 في الشهر؛ وتُحتسب مقارناتك الثلاث الأولى ضمن هذه الحدود، وتُضاف مكافآت الإحالة الموضّحة في القسم 9 إلى الحد الشهري). وقد تختلف هذه الحدود من حساب إلى آخر، وقد نغيّرها. ولا يبيع هذا الإصدار من التطبيق أي اشتراكات أو مشتريات داخل التطبيق، ولا تمنحك هذه الشروط حقًا في فئة مدفوعة أو في حدود أعلى.

## 5. الاستخدام المقبول

توافق على ألا تقوم بما يلي:

- استخدام التطبيق لأي غرض غير قانوني، أو للبحث عن منتجات أو مقارنتها أو الحصول عليها بقصد إلحاق الضرر بنفسك أو بغيرك؛
- إرسال محتوى مسيء أو مهدِّد أو يحض على الكراهية، أو محتوى ينتهك حقوق غيرك، عبر أي وسيلة إدخال (نص أو صورة أو رابط)؛
- تصوير أشخاص أو مستندات هوية أو غيرها من المستندات أو بطاقات دفع أو أي تفاصيل شخصية أو صحية أخرى، أو رفع صور لها (انظر القسم 8)؛
- الوصول إلى التطبيق أو إلى خوادمنا بوسائل آلية (مثل برامج الروبوت أو النصوص البرمجية أو أدوات استخراج البيانات)، أو جمع البيانات من التطبيق بوسائل آلية، أو استخدام التطبيق لبناء منتج منافس أو مجموعة بيانات منافسة؛
- إجراء هندسة عكسية للتطبيق أو فك ترجمته أو تفكيكه، إلا في الحدود التي يجيزها القانون رغم هذا القيد؛
- التحايل على حدود الاستخدام، مثل إنشاء عدة حسابات أو إعادة ضبط جهازك أو إخفاء هويته؛
- التدخل في عمل التطبيق أو خوادمنا أو تعطيله، أو محاولة دفع الذكاء الاصطناعي إلى تجاهل تعليماته عبر ما تُدخله؛
- انتحال شخصية شخص آخر أو تقديم معلومات مضللة عن هويتك؛
- تقديم مقارنة، أو نسخة معدّلة منها، على أنها بيان صادر عن ميّز وهي ليست كذلك، أو استخدام التطبيق لاتخاذ قرارات شراء آلية من دون مراجعة بشرية.

## 6. المحتوى المُنشأ بالذكاء الاصطناعي ودقته

تُنشأ خلاصات المقارنة والملخصات والمواصفات والتوصيات بالذكاء الاصطناعي من معلومات عامة، وقد تكون ناقصة أو غير صحيحة أو غير محدّثة. وتأتي الأسعار والتوفر والمواصفات والتقييمات من مصادر تابعة لأطراف ثالثة، وقد تتغير أو تختلف لدى المتجر؛ وقد تكون الأسعار محوّلة من عملة أخرى، وقد لا تشمل رسوم التوصيل أو الجمارك أو الضرائب. لذا تحقّق منها لدى المتجر قبل الشراء.

لا شيء في ميّز يُعدّ نصيحة مهنية أو طبية أو صحية أو مالية أو قانونية. وينطبق ذلك أيضًا على مقارنات المكملات الغذائية ومنتجات العناية بالبشرة وغيرها من المنتجات الصحية أو منتجات التجميل: اقرأ ملصق المنتج واتبع تعليماته، واستشر طبيبًا أو صيدليًا قبل أن تبدأ تناول دواء أو مكمل غذائي أو تتوقف عنه أو تغيّره، ولا سيما في حالة الحمل أو إذا كانت لديك حالة صحية أو كنت تتناول أدوية أخرى. ولا يحسب ميّز الجرعات، وهو غير مخصص لحالات الطوارئ؛ وفي حالة الطوارئ، اتصل بخدمات الطوارئ المحلية.

## 7. المتاجر والعلامات التجارية والروابط

لا يبيع ميّز المنتجات وليس طرفًا في أي عملية شراء. تنقلك الروابط إلى مواقع متاجر تابعة لأطراف ثالثة لا نتحكم فيها؛ وتتم أي عملية شراء بينك وبين المتجر وفق شروطه. ولسنا مسؤولين عن منتجاتها أو أسعارها أو مخزونها أو توصيلها أو سياسات الإرجاع لديها أو شروطها. وإذا كنت تعتقد أن معلومة في ميّز عن منتجك أو نشاطك التجاري غير صحيحة، فراسلنا على <PLACEHOLDER:SUPPORT_EMAIL>.

## 8. الملكية الفكرية والمحتوى الذي ترسله ومزوّد الذكاء الاصطناعي لدينا

تعود ملكية التطبيق وتصميمه وشيفرته وهويته التجارية إلى <PLACEHOLDER:IP_OWNER_AR> (أو هي مرخّصة لنا). وتعود معلومات المنتجات والمراجعات، وأسماء المتاجر والعلامات التجارية والمنتجات، إلى أصحابها؛ ولا نستخدم هذه الأسماء إلا للتعريف بالمنتجات التي تُقارَن، ولا يعني ظهورها في ميّز أن أصحابها يؤيدون ميّز أو أننا نؤيدهم. <ug12_ar.terms_history, byte-identical> <ug12_ar.terms_licence, byte-identical> ومزوّد الذكاء الاصطناعي لدينا هو OpenAI؛ ويبيّن القسم 4 من سياسة الخصوصية ما نرسله إليها، ويطلب التطبيق إذنك قبل مقارنتك الأولى. <ug12_ar.terms_derived, byte-identical> ولا تُدخل أو تصوّر أو تربط أي محتوى لا يحق لك مشاركته، ولا تفاصيل شخصية أو صحية تخصك أو تخص غيرك.

## 9. إحالات القرارات الذكية

(byte-identical to base terms_of_service_ar.md:52-58)

## 10. الإشعارات

(byte-identical to base :62)

## 11. إخلاء المسؤولية عن الضمانات

في الحدود التي يسمح بها القانون المعمول به، يُقدَّم التطبيق «كما هو» و«حسب توفره»، من دون أي ضمانات من أي نوع، صريحة كانت أو ضمنية، بما في ذلك أي ضمان ضمني بأن التطبيق مناسب لغرض معيّن أو دقيق أو متاح من دون انقطاع. وإذا كان القانون المعمول به لا يجيز بعض هذه الاستثناءات، فإنها تسري عليك فقط بالقدر الذي يجيزه ذلك القانون.

(the four bullets of base :68-71, byte-identical)

## 12. حدود المسؤولية

لا يستبعد أي شيء في هذه الشروط مسؤوليتنا ولا يحدّ منها في حالات الغش أو الإهمال الجسيم أو سوء السلوك المتعمَّد، أو الوفاة أو الإصابة الشخصية، أو أي أمر آخر لا يسمح لنا القانون باستبعاد مسؤوليتنا عنه أو الحدّ منها. ومع مراعاة ذلك، وفي الحدود التي يسمح بها القانون المعمول به، لا نتحمل المسؤولية عن:

(the four bullets of base :77-80, byte-identical)

## 13. التعليق والإنهاء والحذف

قد نعلّق وصولك إلى التطبيق أو ننهيه إذا خالفت هذه الشروط، أو إذا اقتضى القانون ذلك، أو لحماية المستخدمين أو التطبيق أو غيرهم. ومتى كان ذلك ممكنًا ومسموحًا به قانونًا، فسنخبرك بالسبب، ويمكنك أن تطلب منا مراجعة القرار بمراسلتنا على <PLACEHOLDER:SUPPORT_EMAIL>. وعند انتهاء وصولك، ينتهي حقك في استخدام التطبيق؛ وتظل الأقسام 8 و11 و12 و15 و17 و18 سارية.

<PLACEHOLDER:DELETION_SECTION>

## 14. التغييرات على هذه الشروط

قد نغيّر هذه الشروط، مثلًا عندما يتغير التطبيق أو القانون. وإذا فعلنا ذلك، فسنحدّث تاريخ السريان أعلاه وننشر النسخة الجديدة في التطبيق وعلى موقعنا الإلكتروني. وإذا كان التغيير جوهريًا، فسنعلن عنه أيضًا في التطبيق أو على موقعنا الإلكتروني قبل سريانه، إلا إذا كان التغيير مطلوبًا على وجه السرعة لأسباب قانونية أو أمنية. وفي الحدود التي يسمح بها القانون، إذا واصلت استخدام التطبيق بعد سريان التغيير، فإن الشروط المعدّلة تسري عليك؛ وإذا كنت لا توافق عليها، فتوقف عن استخدام التطبيق واحذف حسابك.

## 15. القانون الحاكم وتسوية النزاعات

تخضع هذه الشروط لقوانين <PLACEHOLDER:GOVERNING_LAW_AR>. وإذا نشأ نزاع، فسنحاول أولًا حله معك وديًا؛ لذا راسلنا على <PLACEHOLDER:SUPPORT_EMAIL>. وإذا لم ينجح ذلك، فستفصل فيه المحاكم المختصة في <PLACEHOLDER:GOVERNING_LAW_AR>. وإذا كنت تستخدم التطبيق بصفتك مستهلكًا، فلا يحرمك أي شيء في هذه الشروط من الحماية التي تمنحك إياها القوانين الإلزامية في البلد الذي تقيم فيه.

## 16. Apple

إذا نزّلت التطبيق من متجر App Store التابع لشركة Apple، فإن هذا القسم يسري أيضًا:

- هذه الشروط اتفاق بينك وبيننا فقط، وليست اتفاقًا مع Apple. ونحن، لا Apple، المسؤولون وحدنا عن التطبيق ومحتواه.
- تحكم اتفاقية ترخيص المستخدم النهائي للتطبيقات المرخّصة من Apple (Licensed Application End User License Agreement، «الاتفاقية القياسية») ترخيصك لاستخدام برنامج التطبيق، وتحكم هذه الشروط استخدامك لخدمة ميّز. وإذا تعارضتا، فإن الاتفاقية القياسية تسري على برنامج التطبيق، وتسري هذه الشروط على الخدمة.
- لا تتحمل Apple أي التزام بتقديم أي صيانة أو دعم للتطبيق.
- إذا لم يطابق التطبيق أي ضمان معمول به، يمكنك إبلاغ Apple، ويجوز لـ Apple أن تردّ إليك ثمن شراء التطبيق (والتطبيق مجاني، فيكون هذا المبلغ صفرًا)؛ وفي الحدود التي يسمح بها القانون، لا يقع على Apple أي التزام آخر بالضمان فيما يخص التطبيق. وفيما بينك وبيننا وبين Apple، تقع علينا، لا على Apple، أي مطالبات أو خسائر أو التزامات أو أضرار أو تكاليف أو نفقات أخرى تنشأ عن عدم مطابقة التطبيق لأي ضمان، مع مراعاة القسمين 11 و12.
- فيما بيننا وبين Apple، نحن، لا Apple، المسؤولون عن التعامل مع أي مطالبات منك أو من أي طرف ثالث تتعلق بالتطبيق أو باستخدامك له، بما في ذلك مطالبات المسؤولية عن المنتج، والمطالبات بأن التطبيق لا يستوفي أي متطلب قانوني أو تنظيمي، والمطالبات الناشئة بموجب قوانين حماية المستهلك أو الخصوصية أو القوانين المماثلة.
- إذا ادّعى طرف ثالث أن التطبيق أو استخدامك له ينتهك حقوق الملكية الفكرية الخاصة به، فإننا، لا Apple، المسؤولون وحدنا عن التحقيق في هذا الادعاء والدفاع فيه وتسويته والوفاء به.
- تقرّ بأنك لست موجودًا في بلد يخضع لحظر تفرضه حكومة الولايات المتحدة أو صنّفته حكومة الولايات المتحدة بلدًا «داعمًا للإرهاب»، وبأنك لست مدرجًا في أي قائمة لدى حكومة الولايات المتحدة للأطراف المحظورة أو المقيّدة.
- يجب أن تلتزم بأي شروط لأطراف ثالثة تسري عند استخدامك للتطبيق، مثل شروط البيانات لدى مشغّل شبكة الهاتف المحمول أو مزوّد خدمة الإنترنت لديك، وشروط تسجيل الدخول عبر Apple أو Google.
- Apple والشركات التابعة لها مستفيدون من الغير من هذه الشروط. وبمجرد قبولك لهذه الشروط، يحق لـ Apple (ويُعدّ أنها قبلت هذا الحق) أن تنفذ هذه الشروط في مواجهتك بصفتها مستفيدًا من الغير.

## 17. مسؤوليتك عن الاستخدام غير القانوني

في الحدود التي يسمح بها القانون، توافق على تعويضنا عن الخسائر والأضرار والتكاليف المعقولة (بما في ذلك أتعاب المحاماة المعقولة) التي تلحق بنا بسبب مطالبة من طرف ثالث، إذا نتجت تلك المطالبة عن استخدامك غير القانوني للتطبيق أو عن مخالفتك للقسم 5. ولا يسري ذلك بالقدر الذي يكون فيه الضرر ناتجًا عن خطئنا نحن.

## 18. أحكام عامة

- **الاتفاق الكامل:** تشكّل هذه الشروط وسياسة الخصوصية، والاتفاقية القياسية إذا نزّلت التطبيق من متجر App Store، الاتفاق الكامل بينك وبيننا بشأن التطبيق.
- **قابلية الفصل:** إذا قررت محكمة أن جزءًا من هذه الشروط باطل أو غير قابل للتنفيذ، يظل باقيها ساريًا.
- **عدم التنازل:** إذا لم نمارس حقًا من حقوقنا بموجب هذه الشروط على الفور، فيظل بإمكاننا ممارسته لاحقًا.
- **نقل الحقوق والالتزامات:** لا يجوز لك نقل حقوقك أو التزاماتك بموجب هذه الشروط. ويجوز لنا نقل حقوقنا والتزاماتنا إلى جهة تخلفنا في تشغيل التطبيق، مثل شركة ننشئها لتشغيله؛ ولن ينقص ذلك من حقوقك بموجب هذه الشروط.
- **اللغة:** تُنشر هذه الشروط باللغتين الإنجليزية والعربية، والمقصود أن تحمل النسختان المعنى نفسه؛ وإذا اختلفتا، فتسري النسخة الأكثر فائدة لك.

## 19. التواصل

- **أسئلة حول هذه الشروط:** <PLACEHOLDER:SUPPORT_EMAIL>
- **أسئلة الخصوصية:** <PLACEHOLDER:PRIVACY_EMAIL>
- **العنوان البريدي:** <PLACEHOLDER:POSTAL_ADDRESS_AR>
```

[AR-NEW] in the AR ToS: s1 (fork phrase, postal sentence, contact sentence, App Store sentence), s2 last sentence, s3 bullets 3 and 5, s4 the two last sentences, every s5 bullet except 5 (reverse engineering, extended) and 8 (impersonation, unchanged): bullets 1, 2, 3, 4, 5 (the "except" tail), 6, 7, 9, the whole of s6 except its first clause, s7 entirely (heading included), s8 heading and its four new sentences (the ownership sentence keeps the base wording; the `IP_OWNER_AR` value is new), s11 heading and paragraph, s12 the opening paragraph, s13 the first paragraph, s14 the second-to-fourth sentences, s15 the last two sentences and "لذا راسلنا على", s16 entirely, s17 entirely, s18 entirely, s19 the privacy line.

`MINORS_CLAUSE` terms true (AR) [AR-NEW]: ` وإذا كان عمرك أقل من 18 عامًا، أو كنت دون سن الرشد في مكان إقامتك إن كان أعلى من ذلك، فلا يجوز لك استخدام التطبيق إلا بإذن أحد والديك أو وليّ أمرك، الذي يجب أن يوافق على هذه الشروط نيابةً عنك ويكون مسؤولًا عن استخدامك للتطبيق.`

`DELETION_SECTION` terms 043 (AR) [AR-NEW]: `يمكنك حذف حسابك في التطبيق في أي وقت (الملف الشخصي، ثم أيقونة الإعدادات، ثم «حذف الحساب»). ويوضّح القسم 9 من سياسة الخصوصية ما يزيله حذف حسابك والسجلات التي نحتفظ بها. ولا يؤدي حذف حسابك إلى حذف البيانات التي سبقت مشاركتها مع OpenAI ضمن برنامج مشاركة البيانات لديها، والتي تخضع لشروط OpenAI (القسم 4 من سياسة الخصوصية).`

#### Consistency checks the texts were written against

- Privacy policy: the ToS never names a recipient the policy hides, claims no opt-out (D3 = C), repeats the OpenAI exchange word for word in substance (s8 keeps the pinned S77 / d3c sentences; the deletion variant says shared data is governed by OpenAI's terms, as privacy s4 does), points deletion to privacy s9 (TOS-12) and keeps the minors rule identical in both documents.
- Consent sheet (`SmartCompareApp/src/i18n/{en,ar}.json` `aiConsent.*`, `AiConsentSheet.tsx`, AI_CONSENT_VERSION 2): the ToS says the App asks permission before the first comparison and defers to privacy s4 for what is sent; no new claim about what is sent; the sheet's sha256 fence is untouched (no client copy change).
- App Store privacy label (S76 packet section 4, published 13 data types, no tracking, Phone Number / Physical Address / Health / Location not collected): the texts claim no new collection; s5 of the ToS asks users not to send health details, it does not collect them.
- `NOTES_DRAFT.txt`: "not medical, health or financial advice" (ToS s6), 13+ (s3), free with 3 a day / 10 a month (s4), no sales, payments or affiliate links (s7: not a party to any purchase), ratings only from published sources (s6 no longer calls ratings AI-generated), prices converted to BHD and labelled (s6), OpenAI named (s8, privacy s4-s5). The notes name infrastructure vendors to Apple privately; the public texts give categories, which is not a contradiction.
- Features the App lacks are not promised: no in-app consent-withdrawal control (withdrawal stays "by deleting your account" plus email), no re-consent prompt (the material-change notice is "in the App or on our website", which publishing on the website already satisfies), no archive of prior versions (LR4: none is published), no notice period in days.

## 4. Existing pins

### 4.1 Pins that change (deliberately, LR9), one row each

| # | test node (file:line) | asserts today | new assertion | reason |
|---|---|---|---|---|
| P1 | `tests/test_legal_docs_u8.py::test_t7a_policy_names_every_processor` (:979-1001) + `SPEC_RECIPIENTS_EN` (:782-785) | every personal-data row's `name_en` / `name_ar` is a whole word in privacy EN / AR; the 13 vendor names are rows | for every personal row whose gate is open: `category_en` / `category_ar` occur (whole word, `_name_in`) in privacy EN / AR; when `public_name` is true `name_en` / `name_ar` occur too; when false they occur in NONE of the six legal sources; `SPEC_RECIPIENTS_EN` becomes `SPEC_RECIPIENT_IDS` = the 14 ids supabase, railway, upstash, sentry, openai, expo_push, apple, google_sign_in, serper, bright_data, firecrawl, scrapedo, cloudflare, gmail (each must be a personal row) | LR3 categories |
| P2 | `test_t7_processor_manifest_schema` (:933) + `_ROW_KEYS` (:787) | 8 keys per row | 11 keys: add `category_en`, `category_ar` (non-empty strings), `public_name` (bool); `public_name` true exactly for openai, apple, google_sign_in, retailers | LR3 manifest stays internal but drives T7a |
| P3 | `test_fix_a1_sentry_sentence_scoped_to_servers_and_app_reports_disclosed` via `FIX_A1_EN["servers"]` (:1482) and `FIX_A1_AR["servers"]` (:1489) | "From our servers, Sentry receives exception types" (+ AR) | "From our servers, our error-reporting provider receives exception types" / AR `يتلقى مزوّد تقارير الأخطاء لدينا من خوادمنا أنواع الاستثناءات` (escaped in the file); "traces", "app", "products" markers unchanged | LR3 / LR6 |
| P4 | header docstring of `tests/test_legal_docs_u8.py` (:65-98, :143) | describes name_en in policy, "'Bright Data' removed -> T7a" | describe the category rule; mutation "a vendor name added back to s5 -> T7a" | documentation of P1-P2 |
| P5 | `tests/test_legal_docs_u8_polish.py::test_polish_b4_fill_in_end_to_end` (:470-473) + `AR["DATE_LINE"]` (:81) | snapshot line 5 equals live line 5 (kept) AND equals the literal `*Effective date: October 11, 2026*` / the AR literal | keep the snapshot-equals-live loop; the two literals are built from `consent_service.TERMS_VERSION` (EN month table; AR Gulf month table of `test_legal_docs_u8.GULF_MONTHS_AR`, Western digits) | LR4 date, re-date without editing this file |
| P6 | polish `COMPLETE_VALUES` (:96-116) | no `POSTAL_ADDRESS_AR` | add `"POSTAL_ADDRESS_AR": "عنوان تجريبي"` (synthetic "test address", no digits); keep the other synthetic values | new placeholder: without it every `Copy.complete()` run reports it missing (rc 2) |
| P7 | `test_polish_a12b_cloudflare_line_kept_whatever_the_mailboxes` (:581-600) | the `- **Cloudflare:**` line is in privacy EN / AR whatever the addresses | the `- **Our email providers:**` line (AR: `- **مزوّدو البريد الإلكتروني لدينا:**`) is in privacy EN / AR whatever the addresses; the changed-address refusal half unchanged | LR3 (Gmail -> email provider) |
| P8 | `test_fix2_p1_cloudflare_line_is_plain_text_not_derived` (:698-720), `P1_LINE_EN` / `P1_LINE_AR` (:675-688) | no fork / clause carries "Cloudflare"; the Cloudflare line is once in s5 | no fork / clause carries "email providers" (EN) or its AR label; `P1_LINE_EN` / `_AR` = the new email-providers line of section 3.2; the comment check unchanged | LR3 |
| P9 | `test_fix2_p1_fill_in_keeps_cloudflare_for_every_address_pair` (:723-737) | `P1_LINE` once in s5 and `<strong>Cloudflare:</strong>` once per privacy page | the new line once in s5; `<strong>Our email providers:</strong>` (AR label) once per privacy page | LR3 |
| P10 | `test_polish_f1_empty_hosting_regions_first_fill_is_accepted` (:498-504) | `"temporary-storage" not in` the WHOLE filled EN privacy | `"temporary-storage"` not in s7 only (s5 now has the category "temporary-storage provider") | LR3 category label |
| P11 | `tests/test_legal_docs_u8_d3c.py::test_d3c_m_hosting_regions_clause_names_only_the_measured_roles` (:1053-1075), `HOSTING_CLAUSE_EN` (:962) | the clause is `, and in {value} (our database and hosting providers)`; filled s7 reads "<regions> (our database and hosting providers)" and never temporary storage | the clause is `, and in {value}` (AR `، وفي {value}`); filled s7 contains the regions, no "(" right after them, no role word ("database", "hosting", "temporary") and no vendor name | LR3 countries only |
| P12 | `test_d3c_n_providers_sentence_carves_out_openai` (:1101) via `S5_OWN_TERMS_EN` (:972) + `fix3_ar.s5_own_terms` (fixture) | own-terms sentence names "Google as our mailbox provider" | own-terms sentence = section 3.2 ("... and our mailbox provider act under their own terms.") EN / AR; the carve-out half byte-identical | LR3 |
| P13 | `tests/fixtures/legal_d3c_u8.json` `ar_values` | no `POSTAL_ADDRESS_AR` | add `"POSTAL_ADDRESS_AR": "عنوان تجريبي"` (synthetic) | new placeholder (d3c `_complete_data`) |
| P14 | `tests/test_legal_disclosure_s77.py` `P5G_NEW_EN` (:104), fixture `privacy_s5_google_ar` | Google line ends "Google also receives the email you send to our addresses (see Cloudflare below)." | the Google line of section 3.2 (sign-in only), EN / AR | LR3 |
| P15 | s77 `P5C_NEW_EN` (:108), fixture `privacy_s5_cloudflare_ar` | the Cloudflare + Google (Gmail) line | the email-providers line of section 3.2, EN / AR | LR3 |
| P16 | s77 `OWN_TERMS_EN` (:112), fixture `privacy_s5_own_terms_ar` | "... and Google as our mailbox provider act under their own terms." | the section 3.2 sentence; add the old RL2 sentence to `RETIRED_EN` / `retired_ar` | LR3 |
| P17 | `test_s77_d6_privacy_s5_names_google_gmail` (:554-576) | s5 has P5C + P5G; rendered s5 contains "Google (Gmail)"; `<strong>Cloudflare:</strong>` once | s5 has the new two lines once each; rendered s5 contains neither "Gmail" nor "Cloudflare"; `<strong>Our email providers:</strong>` (AR label) once per page (node name kept, docstring updated) | LR3 |
| P18 | `test_s77_d7_processors_manifest_names_gmail` (:584-595), `ROW_M` (:169-178) | the gmail row equals the 8-key row M; its name in s5 | row M gains `category_en: "mailbox provider"`, `category_ar: "مزوّد صندوق بريدنا"` (escaped), `public_name: false`; its CATEGORY is in s5 and its NAME is in neither policy; still right after cloudflare | LR3 |
| P19 | `test_s77_d14_privacy_s7_names_openai_and_google` (:846-870), `S7_EN` (:132) | "United States (OpenAI and Google)" exactly once; AR parenthesis names OpenAI and Google | s7 (live, snapshot, rendered) names "United States" and "Germany (European Union)" (AR twins) and no vendor name, no "(OpenAI" anywhere in s7 | LR3 no mapping |
| P20 | `test_s77_d17_privacy_s7_transfer_sentence_covers_the_mailbox` (:959-998), `S7_TRANSFER_EN` (:941), fixture `privacy_s7_transfer_ar` | the transfer sentence names Google as mailbox provider | the section 3.2 TRANSFER_BASIS false sentence EN / AR; the old RF1 sentence joins the retired list | LR3 |
| P21 | `test_s77_d5_rendered_pages_and_api_serve_the_new_text` (:524-545) | `last_updated == "2026-10-11"` (RL1) | `last_updated == consent_service.TERMS_VERSION` and `> "2026-10-11"`; expected sentence lists follow P14-P16, P19 | LR4 supersedes RL1 |
| P22 | `test_s77_d18_privacy_s9_says_email_survives_account_deletion` (:1001-1031), `PRIVACY_PAGE_ADDRESSES = 11` (:956) | 11 site addresses per privacy page | the measured count after step C (expected 14; GREEN measures, never guesses) | the two postal lines and the on-request sentence add privacy@ mentions |
| P23 | s77 `RETIRED_EN` (:135-143) and fixture `retired_ar` | the S77 retired sentences | add the S77-era sentences this unit retires: old P5G, old P5C, the RL2 own-terms sentence, "United States (OpenAI and Google)", the RF1 transfer sentence (EN + AR) | regression guard |
| P24 | `tests/test_consent_capture_w3_16.py:39` `TERMS_VERSION = "2026-10-11"` (used by B12 :543) | the literal | `"2026-10-14"` (B12 keeps a literal on purpose; the re-date recipe edits it) | LR4 |
| P25 | `SmartCompareApp/__tests__/landing.brand.s69.test.ts:60-74` `ADDRESS_COUNTS` | privacy 11, terms 6, support 10 (EN and AR) | the measured counts after step C (expected privacy 14, terms 13, support 11 per language) | more role-address mentions; jest cannot run in the worktree (CI frontend-tests is the arbiter) |
| P26 | `app/legal/processors.json` `_comment` and `scripts/legal_variants_u8.json` `_comment` (read by polish Q5 / P1 checks) | name_en rule; Cloudflare line note | category rule; email-providers line note; Q5's "ProductImage" + "retailer row" words kept | P1 / P8 consistency |

### 4.2 Pins that must stay byte-identical (green before and after, no edit)

- `tests/test_legal_docs_u8.py`: T1 (both), T2 (both; holds because `POSTAL_ADDRESS_AR` has a fixture key), T3 (both), T4 (both; ToS 19/19, privacy unchanged), T5, T6 (both; holds because the twelve anchors move together), T7 scanner / client probes, T7b, T7c, T8 (all four; s4 untouched), T9 (all five; `last_updated` now IS `TERMS_VERSION`), T11 (both; the 043 privacy text untouched), UL12 copy policy, no tables, landing chrome, fix A2, A3, A4, B1 (all; the parametrised keys still exist).
- `tests/test_legal_docs_u8_d3c.py`: (a) x3, (b), (c) x2, (d), (e) x2, (f), (g), (h), (i) (s8 history / licence / derived sentences byte-identical and in that order), (j) (privacy s2, s3.6, s9), (k) x2 (every new sentence of section 3 was written against the scan; GREEN re-runs it), (l), (o).
- `tests/test_legal_docs_u8_polish.py`: a5, a6 (s2 and s11 keep their sentences), a7, a8, a9 (the Google line still starts `- **Google:**` and names the profile picture), a13, a14, f3, f5, a16, a17 (the new inline fork A occurs once in each support snapshot), q5, f2, b3, b6 x3, b7, f1 (parametrised), b2 x2, a10, b5, a11, a12a, a12c, a15 x2, new-answer keys, b8, the prefill-snapshot pin.
- `tests/test_legal_disclosure_s77.py`: D1, D2, D3, D4, D5a, D8, D9, D10, D11, D12 (with the updated constants), D13 (with P16), D15, D16.
- `tests/test_legal_routes.py` (11), `tests/test_domain_s76.py` (7; t4 holds: both UA literals equal and contain `(+https://getmyez.com/bot;`), `tests/test_robots_unreadable_ruling.py`, `tests/test_search_descriptor_d3.py`, `tests/test_u3c_referral_push_name.py`, `tests/test_landing_fallback_pages_s69.py`, and every source-scanning pin of section 6.

## 5. RED tests

New file `tests/test_legal_s78.py` (pure ASCII; Arabic and the town digests live in the new fixture `tests/fixtures/legal_s78.json`, read with `encoding="utf-8"`; failure messages escape non-ASCII; hermetic: file reads, a temp copy for fill-ins, the route handlers called directly, no network). No test embeds the address, a house / block / road number, a phone number, a personal email or the town name (LR8); the controller name is read from the fill-in data file, never written in the test.

Shared helpers: `SURFACES` = the six `app/legal/*.md`, the six legal regions (text between the markers, `html.unescape`d), the four route payloads (`get_privacy_policy` / `get_terms_of_service` with `lang` en / ar), and every `landing/**/*.html` page whole (`html.unescape`d). `normalise(text)` = NFKC, casefold, drop U+064B-U+065F, U+0670, U+0640, replace every non-letter by a space, collapse spaces.

Fixture `tests/fixtures/legal_s78.json` keys: `home_town_sha256` (list of two sha256 hex digests: `normalise(<HOME_TOWN>)` in Latin script as written in the base fixture's `POSTAL_ADDRESS`, and the Arabic name of the same town; the RED agent computes both in a throwaway Python process from `git show 4772d492:tests/fixtures/legal_fill_in_u8.json` without printing them, and commits only the digests), `activity_ar` (`مطوّر تطبيقات يعمل بصفة فردية في مملكة البحرين`), `postal_ar_markers` (`مملكة البحرين`, `عند الطلب`), `on_request_ar` (the AR on-request sentence with the address token replaced by `privacy@getmyez.com`), `categories_s5_ar` (the AR s5 labels), `apple_ar` (one marker per Apple item, section 3.3), `carveouts_ar` (`الغش`, `الإهمال الجسيم`, `سوء السلوك المتعمَّد`, `الوفاة أو الإصابة الشخصية`, `لا يسمح لنا القانون`), `minors_ar` (`أقل من 18 عامًا`, `سن الرشد`, `أحد والديك أو وليّ أمرك`), `tos_markers_ar`, `internals_ar` (the AR of "Administrative functions require a secret key" and of "certificate pinning", from the base AR s13), `retired_ar`.

| # | test | assertion | why RED at base | why GREEN after |
|---|---|---|---|---|
| R1 | `test_s78_r1_no_street_number_pattern_in_served_surfaces` | over SURFACES: no match of `(?i)\b(?:block\|blk\|road\|rd\|street\|str\|st\|avenue\|ave\|building\|bldg\|flat\|apartment\|apt\|house\|home\|villa\|lane\|way\|office\|unit\|floor)\b\.?\s*(?:no\.?\|number\|#)?\s*<D>` nor of `(?:مجمع\|طريق\|شارع\|منزل\|بيت\|مبنى\|عمارة\|بناية\|شقة\|فيلا\|جادة\|مكتب\|طابق)\s*(?:رقم\s*)?<D>`, `<D>` = `[0-9٠-٩۰-۹]`; positive control first: the pattern flags synthetic samples ("Block 12", "Rd. 5", "house no. 7", the AR "block" + Western and Arabic-Indic digits) | measured: 6 hits per privacy / terms markdown, 3 per support markdown, the same on the six pages and the API payloads | measured: 0 hits on every served file with the interim value substituted |
| R2 | `test_s78_r2_no_home_town_token_in_served_surfaces` | no 1-, 2- or 3-word window of `normalise(surface)` has a sha256 in `home_town_sha256`; control: the digest of a synthetic token added to a copy of the list is found in a synthetic text | `<HOME_TOWN>` is inside `<HOME_ADDRESS>` on every privacy / terms / support surface | no surface names the town (measured: the token occurs only inside the address) |
| R3 | `test_s78_r3_no_personal_email_or_phone_in_served_text_and_user_agents` | over SURFACES plus the formatted `sitemap_discovery_service._ROBOTS_UA` and the `USER_AGENT` literal of `scripts/resolve_search_descriptors.py` (read with the `test_domain_s76._ua_literal` regex, formatted with `robots_eval.NAMED_AGENT`): no `(?i)@gmail\.com`, no `(?:\+\|00)\s*973`, no bare Bahrain-shaped 8-digit number `(?<![\d.,])(?:3\d\|6[69]\|1[37])\d{2}[\s-]?\d{4}(?![\d.,])`, and every email address found is `privacy@getmyez.com` or `support@getmyez.com` | the two UA literals carry a personal Gmail address | UA carries support@ (step 13); surfaces were clean (measured) |
| R4 | `test_s78_r4_user_agent_is_the_lr7_value` | both formatted UAs equal `QarenBot/1.0 (+https://getmyez.com/bot; contact: support@getmyez.com)`; `landing/bot/index.html` carries `mailto:support@getmyez.com` (the same contact) | base contact is a personal address | step 13 |
| R5 | `test_s78_r5_no_gmail_literal_in_app_or_scripts` | no string constant (AST walk) in `app/**/*.py` or `scripts/**/*.py` contains `@gmail.com` | the two UA literals | step 13 |
| R6 | `test_s78_r6_controller_line_is_name_activity_and_postal_line` | with `name = data["placeholders"]["CONTROLLER_NAME"]`, `postal = POSTAL_ADDRESS`, `postal_ar = POSTAL_ADDRESS_AR` from the fill-in data: privacy s1 (EN / AR), ToS s1 (EN / AR) and the support markdown (EN / AR) each have one line holding `name`, the activity phrase (EN `an individual app developer in the Kingdom of Bahrain`, AR `activity_ar`), `trading as MYEZ` (AR `تحت الاسم التجاري MYEZ`) and the language's postal value; privacy s16 and ToS s19 hold the postal value; `name` occurs exactly once in each of the six markdown files and once in each of the six landing legal regions (LR2: identification lines only) | no activity phrase; no trade name; no POSTAL_ADDRESS_AR key | steps 1-8 |
| R7 | `test_s78_r7_postal_values_are_interim_or_po_box` | `POSTAL_ADDRESS` and `POSTAL_ADDRESS_AR` exist and are non-empty; neither matches R1 or R2; each either contains `Kingdom of Bahrain` / `مملكة البحرين` together with `privacy@getmyez.com` (interim, LR1), or matches `(?i)\bP\.?\s?O\.?\s?Box\s+\d{1,6}\b` / `ص\.?\s?ب\.?\s*\d{1,6}` (the later P.O. Box) and has no other digit run | the base value is a residence with street numbers and no AR key exists | step 5 |
| R8 | `test_s78_r8_openai_apple_google_stay_named` (PIN, green at base) | `OpenAI` in privacy s4 and s5 and ToS s8 (EN / AR); `Apple` and `Google` in privacy s5 (EN / AR); `Apple` in ToS s16 | (green at base; guard for LR3's allow-list) | kept |
| R9 | `test_s78_r9_privacy_s5_lists_recipients_by_category` | privacy s5 EN contains each label `Our database and sign-in provider`, `Our hosting provider`, `Our temporary-storage provider`, `Our error-reporting provider`, `Our notification and update provider`, `Web search and page-retrieval providers`, `Our email providers`, `The retailer websites and store search services we query` (bold list items), AR the `categories_s5_ar` labels; every `processors.json` personal row with an open gate has its `category_en` / `category_ar` in privacy EN / AR | no label exists; the manifest has no category keys | steps 1, 7 |
| R10 | `test_s78_r10_no_infrastructure_vendor_name_in_legal_surfaces` | none of `Supabase`, `Railway`, `Upstash`, `Sentry`, `Expo`, `Serper`, `Bright Data`, `BrightData`, `Firecrawl`, `Scrape.do`, `Scrapedo`, `Cloudflare`, `Gmail`, `Google Fonts`, `YouTube`, `Zyte`, `Frankfurter`, `PostHog`, `Railway.app` appears (case-insensitive, whole word, an AR proclitic waw / ba / lam allowed in front) in the six markdown files, the six regions or the four payloads; the only allowed names are OpenAI, Apple, Google (as the sign-in provider) and "retailer websites"; "Google" does not occur in privacy s7 (the retired mailbox phrasings are R26) | measured: 13 vendor names in privacy EN / AR, on both privacy pages and in the API | steps 1-8 |
| R11 | `test_s78_r11_providers_on_request_sentence` | filled privacy s5 EN contains exactly once `We will tell you the names of our service providers on request at privacy@getmyez.com.` (LR3 verbatim); AR contains `on_request_ar` once; the snapshot carries the token form | absent | step 1 |
| R12 | `test_s78_r12_transfers_name_countries_without_vendor_mapping` | privacy s7 EN contains `United States`, `Germany (European Union)` and `data["placeholders"]["HOSTING_REGIONS"]`, AR the twins; no vendor or role name; no parenthesis after a country except `(European Union)`; contains the TRANSFER_BASIS false sentence of section 3.2 once; no `adequa`, `Article 12`, `Article 13`, `consent and contract` claim (no stronger basis, LR3) | s7 maps OpenAI / Google / Sentry / "our database and hosting providers" to countries | steps 1, 6 |
| R13 | `test_s78_r13_tos_apple_section_carries_the_exhibit_b_items` | ToS s16 EN contains markers for item 1 `between you and us only, not with Apple`, item 3 `no obligation to provide any maintenance or support`, item 4 `refund the purchase price` + `no other warranty obligation`, item 5 `product liability claims` + `consumer protection`, item 6 `intellectual property rights` + `investigating, defending, settling and discharging`, item 7 `embargo` + `terrorist supporting` + `prohibited or restricted parties`, item 9 `third-party terms` + `mobile carrier`, item 10 `third-party beneficiar`, precedence `Standard EULA` + `If they conflict`; AR `apple_ar` markers; no phone shape (R3) in s16; the whole ToS has no licence-grant wording (`(?i)\bwe\s+(?:hereby\s+)?grant\s+you\b`, `(?i)\bis\s+licensed\s+to\s+you\b`, `(?i)\byou\s+(?:are\|will\s+be)\s+granted\b`) | s16 is one sentence | step 2 |
| R14 | `test_s78_r14_tos_liability_opens_with_the_carve_outs` | the first sentence of ToS s12 EN contains `fraud`, `gross negligence`, `wilful misconduct`, `death or personal injury`, `does not allow us to exclude or limit`; `to the extent permitted by applicable law` precedes the first bullet; s11 opens with `To the extent permitted by applicable law`; no currency amount (`\$\|USD\|BHD\|dollars`) in s11-s12; AR `carveouts_ar` in the first AR s12 sentence | no carve-out | step 2 |
| R15 | `test_s78_r15_minors_guardian_sentence` | ToS s3 and privacy s12 EN contain `under 18`, `age of majority` and `parent or guardian`; ToS s3 also `permission`; AR `minors_ar` in both | the base clause has no "18" | step 6 |
| R16 | `test_s78_r16_tos_v2_sections_and_lr5_items` | EN ToS headings are exactly the 19 of section 3.3 in order; markers: s3 `13 years`; s6 `Check them with the retailer`, `supplements`, `skincare`, `doctor or pharmacist`, `not for emergencies`; s7 `not a party to any purchase`, `do not control`; s8 `OpenAI`, `section 4 of our Privacy Policy`, `belong to their owners`, `only to identify`; s5 `automated means`, `several accounts`, `interfere`, `statement by MYEZ`; s13 `review the decision`, `Delete account`, `section 9 of our Privacy Policy`, no `erases your account data`; s14 `material`, `before it takes effect`; s15 `mandatory laws of the country where you live`; s17 `To the extent the law allows`, `unlawful use`, `section 5`; s18 `Entire agreement`, `Severability`, `No waiver`, `Assignment`, `successor`; s19 the two role addresses and the postal value; AR `tos_markers_ar` per section; the ToS contains no `opt out` and no `estimated` | 17 sections, none of the markers | step 2 |
| R17 | `test_s78_r17_en_ar_structural_parity` | for privacy, terms and support: the EN and AR markdown (filled and snapshot) have the same sequence of `##` / `###` numbers, the same number of `- ` list items per section, the same tokens per section in the snapshot (token names with `_AR` stripped); ToS has 19 `##` sections, privacy 16 | ToS has 17 sections (fails the 19 rule) | step 2 |
| R18 | `test_s78_r18_twelve_anchors_equal_and_moved` | the twelve anchors of section 1.6 (same parsers as T6, by content) all equal `consent_service.TERMS_VERSION`, which is later than `2026-10-11`; the four snapshot date lines carry the same date; `legal_routes` takes `last_updated` from `consent_service.TERMS_VERSION` (AST: the module imports the name and has no ISO date literal) | every anchor is 2026-10-11; the routes carry literals | steps 1, 10-12 |
| R19 | `test_s78_r19_render_check_clean_and_fill_idempotent` (PIN) | `render_legal_landing.stale_regions(REPO) == []`; `fill_in_legal.plan(REPO, data, variants)` reports no missing key and every output equals the current bytes | (green at base; the merge gate) | kept green by steps C-D |
| R20 | `test_s78_r20_po_box_swap_needs_no_code_change` | on a temp copy of the snapshot, the pages and the renderer, a data file equal to the committed one except `POSTAL_ADDRESS = "P.O. Box 0000, Kingdom of Bahrain"` and `POSTAL_ADDRESS_AR = "ص.ب 0000، مملكة البحرين"` (synthetic) fills with rc 0 and no missing key; the value reaches privacy s1 / s16, ToS s1 / s19 and support in each language; R1, R2, R3 and R7 hold on the result | at base the AR documents use `POSTAL_ADDRESS`, so `POSTAL_ADDRESS_AR` is an unused value and the fill-in refuses (`set it null`) | the AR templates use the `_AR` token |
| R21 | `test_s78_r21_privacy_has_no_security_internals` | privacy EN has none of `secret key`, `Administrative functions`, `certificate pinning`; AR none of `internals_ar`; s13 still says data is encrypted in transit and tokens are in secure storage | the base s13 sentences | step 1 |
| R22 | `test_s78_r22_manifest_categories` | every row has `category_en`, `category_ar` (non-empty) and `public_name` (bool); `public_name` is true exactly for openai, apple, google_sign_in, retailers; the T7b host coverage is unchanged (no row's `hosts` / `module` changed: compare with a frozen copy of the base values inside the test) | no category keys | step 7 |
| R23 | `test_s78_r23_privacy_strength_sentences` | privacy s11 contains `We do not use your personal data for direct marketing.` (AR twin); s15 contains `If a change is material, we will also announce it in the App or on our website before it takes effect.` (AR twin) | absent | step 1 |
| R24 | `test_s78_r24_privacy_keeps_the_required_elements` (PIN) | privacy EN keeps: the 16 section titles of base; s3.6 legal bases; the s5 carve-out sentence; s8 retention lines; s9 `Delete account`; s10 `Access and a copy`, `Correction`, `Deletion, objection and restriction`, `Withdrawing consent`, `Personal Data Protection Authority`; s12 `aged 13 and over`; s13 `encrypted in transit`; s16 the two role addresses (AR twins by section number and the base AR labels) | (green at base; guards LR6 against over-trimming) | kept |
| R25 | `test_s78_r25_new_text_passes_the_existing_scans` | the d3c `_personal_data_claims` scan (loaded by path, the S77 idiom) finds no claim in any EN / AR sentence of section 3 present in the filled documents; the S77 D4 not-sold rule holds over the six markdown files; the copy-policy AR lists find nothing in the AR documents | (the scan modules exist at base; the S78 sentences do not, so the node fails on their absence: it asserts the new ToS s8 OpenAI sentence and s13 deletion sentence are present before scanning) | step 2 |
| R26 | `test_s78_r26_retired_sentences_are_gone` | none of the retired EN / AR sentences (`retired_ar` + the EN list: the base Google mailbox sentence, the Cloudflare line, the RL2 own-terms sentence, "United States (OpenAI and Google)", the RF1 transfer sentence, the base ToS s16 sentence, "Deleting your account erases your account data from our servers") is in the six markdown files, the snapshot, the variants file, the regions or the payloads | they are all present | steps 1-8 |

R8, R19 and R24 are PINs (green at base, marked so in their docstrings); every other node is RED at base for the reason in its row. The RED agent proves each RED reason by running the file at base through the bounded runner and pastes the per-node outcome, then proves satisfiability on a throwaway detached worktree (`git worktree add --detach <scratchpad>/s78proto 4772d492`) with the section 2-3 changes applied (or reports the nodes it could not prototype), and removes the worktree.

## 6. Gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. Machinery: `fill_in_legal.py --dry-run` rc 0 with no `would write` after the fill; `render_legal_landing.py --check` rc 0; `git diff --stat` shows content lines only (CRLF kept) and touches exactly: the six snapshot templates, the six `app/legal/*.md`, the six landing pages (regions only: `git diff` must show no change outside `<!-- legal:begin -->` / `<!-- legal:end -->`), `tests/fixtures/legal_fill_in_u8.json`, `scripts/legal_variants_u8.json`, `app/legal/processors.json`, `app/api/legal_routes.py`, `app/services/consent_service.py`, `app/services/sitemap_discovery_service.py`, `scripts/resolve_search_descriptors.py`, `SmartCompareApp/src/services/consent.ts`, the pin files of section 4.1 (`tests/test_legal_docs_u8.py`, `tests/test_legal_docs_u8_d3c.py`, `tests/test_legal_docs_u8_polish.py`, `tests/test_legal_disclosure_s77.py`, `tests/test_consent_capture_w3_16.py`, `tests/fixtures/legal_d3c_u8.json`, `tests/fixtures/legal_disclosure_s77.json`, `SmartCompareApp/__tests__/landing.brand.s69.test.ts`), and the RED files.
2. Lint and syntax: `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache` and `-m py_compile` on every changed `.py` (legal_routes, consent_service, sitemap_discovery_service, resolve_search_descriptors, the five test files, `tests/test_legal_s78.py`). JSON: `json.loads` of the four changed JSON files.
3. Unit: `tests/test_legal_s78.py` (bound 600) -> all pass.
4. Legal pin files, one run each (bound 600): `tests/test_legal_docs_u8.py`, `tests/test_legal_docs_u8_d3c.py`, `tests/test_legal_docs_u8_polish.py`, `tests/test_legal_disclosure_s77.py`, `tests/test_legal_routes.py`, `tests/test_consent_capture_w3_16.py`.
5. Comm set (two chunks of at most 25 files, bound 1200 each), base and head, `comm -13` of the sorted FAILED node ids must be empty (base was all green: section 1.10). The set = every test that references the machinery or a changed module, unioned with the source-scanning pins (CLAUDE.md rule):
   - chunk 1 (legal + UA modules, 20 files): `test_consent_capture_w3_16`, `test_domain_s76`, `test_landing_fallback_pages_s69`, `test_legal_disclosure_s77`, `test_legal_docs_u8`, `test_legal_docs_u8_d3c`, `test_legal_docs_u8_polish`, `test_legal_routes`, `test_robots_unreadable_ruling`, `test_search_descriptor_d3`, `test_u3c_referral_push_name`, `test_sitemap_discovery`, `test_m6_c1_normalize_and_sitemap_match`, `test_m6_c2_sitemap_pdp_markers`, `test_bolo_adapter`, `test_boutiqaat_adapter`, `test_nasser_adapter`, `test_retro_w0_4`, `test_s77_redis_offloop`, `test_transient_negcache`, plus `test_legal_s78`;
   - chunk 2 (source-scanning pins, 8 files): `test_model_config`, `test_model_config_enforced`, `test_prompt_fence`, `test_u3c_store_false_pin`, `test_start_command`, `test_migration_index_predicate_immutability`, `test_openai_key_log_hygiene_s69`, `test_sentry_channels_u8d_unit`; add any file that `grep -rl "SmartCompareApp" tests/` lists and that reads `consent.ts` or `landing/` (at base: `test_consent_capture_w3_16`, `test_legal_docs_u8`, already in chunk 1).
   - The route handlers are reached by every TestClient test through `app.main`; the full-suite CI run is the final arbiter for that import path (the change is one import of a stdlib-only module).
6. Frontend note: `consent.ts` TERMS_VERSION is imported (not pinned by literal) by `__tests__/LoginScreen.consent.w3-16.test.tsx:16`, `__tests__/RegisterScreen.consent.w3-16.test.tsx:26`, `__tests__/services/authService.consent.w3-16.test.ts:17`, `__tests__/auth/appleButton.s69.test.tsx:30`; `__tests__/landing.brand.s69.test.ts` pins the page address counts (P25) and `__tests__/landing.domain.s76.test.ts` scans addresses outside the legal regions (unchanged). The worktree has no `node_modules`, so jest is not run locally: CI `frontend-tests` (BLOCKING since S77) is the arbiter; GREEN reports the measured counts it wrote and states jest as NOT MEASURED locally.
7. Personal-data sweep of the diff (no value printed): `git diff 4772d492` contains no added line matching R1, R3 or the R2 digests, and no added line containing the base `POSTAL_ADDRESS` value (Python, comparing in memory, printing only counts). The pre-commit hook's `sk-` rule: no added line matches `\bsk-[A-Za-z0-9_-]{20,}`.

## 7. Stated limits and open questions

### 7.1 Stated limits (true after the unit; written down so nobody reads more into the change)

- L1. The interim postal line is a known PDPL Art 17(1)(a) gap ("his address" is required; "available on request" is not an address). The law lens rates it low risk (Art 55: a corrective order comes before any penalty). It closes only with the owner's P.O. Box (OA-1), a two-value re-fill (R20 proves no code change is needed).
- L2. The home address stays in git history, in the S73-S77 state folders, the review JSONs, the closed PRs and every existing clone; this unit changes HEAD and the served surfaces only (LR10: masking and history are owner / orchestrator actions). The on-device legal cache (`LegalScreen` `legal_cache_{doc}_{lang}`) keeps the old text until a refetch.
- L3. Production changes only after the owner's merge yes, the Railway deploy of the API and the landing redeploy from a clean detached checkout of the merge SHA (LR11); until the landing redeploy, getmyez.com still serves the old pages.
- L4. Phones keep sending `terms_version` "2026-10-11" until the first post-approval OTA carries `consent.ts`; the server records the version the client sends and never checks it for equality (`consent_service.py:58-64`, `auth_routes.py:591, 1151`), so registration on the build in review is unaffected, and recorded versions on those accounts name the 2026-10-11 text (no archive of it is published, LR4).
- L5. Recipients by category are lawful under PDPL Art 17(1)(c)(1) / Art 18; the Saudi PDPL Art 13 "entities ... capacity" reading (UNVERIFIED primary text) is covered only by the on-request sentence. Answering such a request uses `app/legal/processors.json`, which is public today only through the public repository (OA-3).
- L6. The equal-protection sentence of privacy s5 still carves out OpenAI and "our mailbox provider" (the consumer mailbox acts under its own terms), exactly as today; Apple 5.1.1(i) wants an unqualified confirmation, which becomes true only after the mailbox moves to a controller-owned business mailbox under a processor contract (owner D10). Not strengthened here, because a stronger sentence would be false today.
- L7. The transfer sentence keeps today's basis ("required by contract"), which the audit says is not an Art 12/13 basis; LR3 forbids strengthening it, and only the United States is verified on the Resolution 42/2022 adequacy annex (Germany, India and Singapore are unverified). Counsel.
- L8. The aggregated-or-anonymised statistics sale right stays in privacy s2 and ToS s8 (LR5, D9) and still conflicts with the in-app "never paid by sellers" copy; the conflict becomes a false statement on the first sale to a seller.
- L9. The web pages still load fonts from Google's font service (chrome outside the regions); the policy now calls it "a web-font service". Self-hosting the fonts (plan LR-3) would remove the recipient.
- L10. The privacy s9 deletion text (043) keeps its mechanics ("a random account number", "the end of the deletion", "the inviter's code"): it explains retention and deletion as Apple requires and is pinned by T11; LR6's "internal detail" list (flag, cache-key and module names, exact infrastructure) does not cover it. s14 keeps "Keychain" (Apple's own store, a user-facing fact).
- L11. The Arabic of section 3 is machine-drafted Modern Standard Arabic; every `[AR-NEW]` sentence goes on the native-review list (D11). The ToS s18 language clause makes the version more favourable to the user prevail, so an AR drafting slip cannot be used against a user.
- L12. The ToS acceptable-use list does not address offensive display names on shared invite links (Apple 1.2 user-generated content): the review notes say no user content is shared between users, and a display-name rule would contradict that without an in-app report or block mechanism.
- L13. R2's town check is only as good as its two digests; a sha256 of a town name in a public repo is reversible by a dictionary of Bahraini towns, which LR8 accepts ("via a hash of the normalised token"). A later P.O. Box in the same town as the home would be refused by R2 (intended: it would still point at the locality) and needs the owner's decision (Q2).
- L14. The re-date path still touches seven places by hand (section 2 G); the md dates are not placeholders (UL3 is kept), only the two route anchors became derived.

### 7.2 Open questions (for the orchestrator / owner / counsel)

- Q1 (counsel). Does a P.O. Box satisfy PDPL Art 17(1)(a) "his address" and the Art 14 notification? (law lens: nothing in the text excludes it; UNVERIFIED with the PDPA.) Until then, is the interim "available on request" line acceptable for the App Review window? The ruling says yes; counsel should confirm the exposure is only Art 55.
- Q2 (owner). If the P.O. Box is at the post office of the home town, may the postal line name that town? R2 refuses it as written; the alternative is a box in another town, or dropping R2's town digest at the swap (one fixture edit).
- Q3 (owner). Exact controller-name spelling: the unit records "Husain Aseeri" (the App Store Connect account name on 2026-10-14, LR2); `ledger.md:7` and the old fixture said "Hussain". If the Apple membership (developer.apple.com > Membership) shows another spelling, it is a one-value re-fill (restore + fill). Is "trading as MYEZ" correct for an individual with no commercial registration, or should the trade-name clause stay empty until a CR exists (counsel)?
- Q4 (counsel). The narrow indemnity (ToS s17) in a consumer adhesion contract (Bahrain Civil Code art 58: arbitrary terms may be modified); the carve-out list (arts 181, 219); the precedence sentence against the Standard EULA (California law and the USD 50 cap on the Licensor there; our Terms set no cap); "the version more favourable to you" language rule.
- Q5 (counsel). Age: is guardian permission enough for users from 13 to the age of majority (reportedly 21 in Bahrain, UNVERIFIED), given that those users' inputs also enter OpenAI's data-sharing programme (D8 option C: exclude minors from the programme, a product change)?
- Q6 (owner, D9). Keep, restrict or drop the right to sell aggregated statistics, and change the in-app "never paid by sellers" copy if it stays.
- Q7 (date). If the merge slips past 2026-10-14, the orchestrator re-dates in one mechanical commit (section 2 G); R18 and the polish / S77 date pins derive the date from `TERMS_VERSION`, so only the seven listed places change.
- Q8 (owner). App Store Connect must keep Apple's Standard EULA and must not get a custom EULA: a custom EULA triggers DPLA Exhibit B item 8 (name, address, telephone, email), which the interim line and the no-phone rule do not meet. Same for the EU DSA trader status (not a trader; GCC storefronts only).
- Q9 (orchestrator). Out of LR7's scope but personal data in the public repo: `pyproject.toml:6` and `backend/pyproject.toml:6` (`authors` email) and `tests/test_abuse_detection.py:122` (a personal-looking address as a test value). Fold into this unit (two TOML lines and one test value, no behaviour change) or into the session docs PR?
- Q10 (owner). The audit's critic gaps not covered by any legal text: the getmyez.com WHOIS / RDAP record, the Google OAuth consent-screen support email, the Supabase auth email sender, the EAS update manifest, web archives of the old pages. Each can publish the same personal data independently of this unit.
