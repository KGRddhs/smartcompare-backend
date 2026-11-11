# WDQS robots exemption (owner ruling 2026-11-07)

Status: RULED by the owner 2026-11-07: "Document exemption" (06:28) and, after the measured comparison of the two read paths, "check both and test them and pick the best one for outcome" (06:3x); the pick (two Opus judges, medium confidence, 06:40, relayed by session 82) = the SPARQL path under this documented exemption. In force only once the code unit S81-16c WDQS-EXEMPTION (scripts/seed_kb_brands_wikidata.py) encodes it: the script's robots check is code, so a docs-only record changes nothing. Filed by the session-87 orchestrator (the record: docs/investigations/2026-10-22-session-81-state/ledger.md, the 2026-11-07 06:25 / 06:30 / 06:31 lines and the ruling line).

## What is exempted (exactly one host, one path, one query per run)
- URL: https://query.wikidata.org/sparql (the SPARQL_ENDPOINT constant of scripts/seed_kb_brands_wikidata.py), read by that script only, under ENABLE_KB_BRANDS (dry / apply), ONE GET per run with LIMIT 2000 under the production QarenBot User-Agent (the project URL + the support mailbox name), never a generic agent.
- Condition: the exemption applies only when https://query.wikidata.org/robots.txt is readable AND its parsed rule sets for QarenBot and for '*' are exactly ((Disallow, /sparql), (Disallow, /bigdata)). Any other or extra rule, a QarenBot-specific group, or "Disallow: /" refuses as today; an unreadable robots.txt (403, 5xx, timeout) stays fail-closed; the refusal line names the check that refused.
- Every other URL, including www.wikidata.org (whose robots.txt disallows /w/ for '*', which covers /w/api.php), keeps the fail-closed rule of docs/policies/2026-08-31-robots-unreadable-ruling.md.
- Politeness: one bounded retry on 429 / 503 (Retry-After, else the body's "retry in N seconds", the wait capped, never a loop), then the run stops with a logged count.

## Why (measured 2026-11-07 06:31-06:40, read-only, three measurement agents + two judges)
- Coverage is equal: SPARQL COUNT 342 distinct brands; CirrusSearch totalhits 342.
- The SPARQL answer: one GET, 2.1 s, 430 bindings, 340 of 342 brands with an en label, 59 mul, 38 ar, 379 distinct hosts after www-stripping, under LIMIT 2000.
- The MediaWiki Action API alternative: 8 to 9 serial calls against a lagging CirrusSearch index with rank semantics unlike wdt: truthy, about 140-200 script lines plus 150-250 test lines, at least three frozen pins rewritten; and it fails the same can_fetch gate (Disallow: /w/ for '*').
- Documentary ground: Wikidata:Data_access and the Wikidata Query Service User Manual document programmatic GET / POST to /sparql with per-client limits; the data is CC0 (no attribution or share-alike duty). Recorded as well: Wikimedia's wikitech Robot policy says "Honor every directive" with no explicit API carve-out, so this is an owner-ruled exemption, not a reading of robots.txt.
- Observed: the evaluation User-Agent (Python-urllib) received a first-request 429 ("retry in 120 seconds", no Retry-After header); the production QarenBot UA was not measured.

## How it amends the 2026-08-31 ruling
The fail-closed ruling (a readable robots.txt that forbids a path is obeyed; an unreadable one is treated as forbidding) stands for every host and path. This document carves out exactly one host, one path, one query per run, under the conditions above, and nothing else; a second exemption needs its own dated document and owner ruling.

## Stated limits (not scope)
- Arabic labels cover 38 of 342 brands at the measurement (the labels are label_ar where present, else the mul / en fallback the script already applies).
- 379 hosts exceed MAX_BRAND_HOSTS = 300, so the cap trims the host list; a cap change is its own owner ruling.
- gzip Accept-Encoding is missing from the script's request headers (a separate app/ item).
- No live Wikidata request by anyone until this document is filed and S81-16c is merged; the first owner-approved DRY run then confirms about 342 brands.
