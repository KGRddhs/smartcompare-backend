# Robots-unreadable ruling — the 5-minute decision (U4, 2026-08-31)

**Decision owner:** Ahmed. **Prepared by:** M11 U4 (docs-only unit; no app behavior changed).
**Live evidence:** 22 hosts' `/robots.txt` fetched fresh today from the Bahrain residential IP,
throttled 2.2s/host, evaluated with `app.services.robots_eval` as `QarenBot` (the registry
`NAMED_AGENT`). Raw per-host results: `docs/policies/2026-08-31-robots-probe-evidence.json`.
Datacenter-side states are from the U01 Railway egress probe (`RESULTS.txt`, 65-host panel,
2026-08-31) and the B3 wall census (328-row global corpus, 2026-08-30).

---

## The question, stated plainly

When a host's `robots.txt` is **UNREADABLE** (the robots file itself returns 403 / a WAF
challenge page / times out), do we:

- **fail-closed** — skip the host entirely (today's operating policy in every probe, census and
  cohort computation), or
- **fail-open-with-care** — treat "no readable policy" as "no stated prohibition" and fetch
  under tight limits?

This is NOT about hosts that disallow us — a readable robots that forbids a path is always
obeyed, no ruling needed. It is only about hosts where the policy document itself is walled.

## What the RFC actually says (precision matters here)

- RFC 9309 **sec 2.3.1.3 "Unavailable" (HTTP 400–499)**: a crawler **MAY access any resources**
  — i.e. the RFC itself permits fail-open on a 403'd robots.txt.
- RFC 9309 **sec 2.3.1.4 "Unreachable" (5xx / network error)**: **MUST assume complete
  disallow**; only after the file is unreachable for a long period (RFC: 30 days) MAY the
  crawler fall back to allow.
- **But**: every 403 measured here is not an origin-authored 403 — it is a **bot-management
  challenge page** (Cloudflare "Just a moment...", Akamai reference page, AWS WAF challenge)
  served *to automated clients specifically*. The operator has deployed technology whose whole
  purpose is to restrict clients like us. Reading that as "no stated prohibition" is
  technically defensible under 2.3.1.3 and obviously against the operator's intent.

## RECOMMENDATION: fail-closed stays (Option A)

Reasoning:

1. **Intent beats letter.** A WAF-403 on robots.txt is restriction intent expressed at the
   network layer instead of the policy layer. The RFC's MAY is permission to fail open, not an
   instruction to; the conservative reading is the one consistent with how we already treat
   named disallows (house rule 7 / the Fragrantica precedent — where reading only the
   permissive part of the signal led to the wrong conclusion).
2. **The stake is small.** The entire unreadable cohort is 15 corpus rows out of 328 (~4.6%),
   every one of them ALSO hard-walled on the PDP itself (see Table 3) — so failing open buys
   almost nothing without ALSO buying a render fight against Cloudflare/Akamai on the content
   pages. The two decisions travel together; skipping the robots fight skips the whole fight.
3. **Unreadable is often transient, so fail-closed is cheap.** 5 of the 13 "unreadable" render
   hosts (notino.de/.it/.nl/.pl, primor.eu) served a clean, permissive robots 200 to the SAME
   residential IP today that 403'd the census reads days ago. A retry schedule converts
   fail-closed skips back into readable-and-allowed hosts for free, with zero policy risk.
4. **Consistency with shipped code.** The app's one robots-consuming runtime path
   (`search_descriptor_service.resolve_descriptor`) currently treats a non-200 robots read as
   allow-all (empty body ⇒ RFC-unparseable ⇒ allow) — RFC-legal, but if this ruling lands as
   fail-closed, that branch should be tightened to match in a later code unit (it is dark today:
   flag off, store empty, so nothing live disagrees with the ruling).

## The 2–3 options to pick from

- **Option A — fail-closed, with a scheduled re-read (RECOMMENDED).** Unreadable robots ⇒ skip
  host; re-probe `/robots.txt` on a schedule (weekly is plenty; the notino flip took < a week).
  Readable-again hosts rejoin automatically under their actual policy. Zero policy risk; codifies
  today's behavior.
- **Option B — fail-open-with-care (RFC 2.3.1.3 reading).** Only where (a) robots.txt is 4xx
  AND (b) the content pages themselves serve 200 (today that is exactly ONE host:
  www.perfume.com — its PDPs serve 200 while robots is walled), fetch under a hard cap
  (e.g. ≤5 req/day/host, named UA, stop on first 403). Buys ~3 corpus rows. Defensible but
  inconsistent with how we read walls everywhere else.
- **Option C — residential-read-through for egress artifacts.** Where robots is readable from
  residential but walled from the datacenter (klinq.com, nazih.qa, numberc.com today), treat the
  residential-read policy as the authoritative policy document and let Railway fetches proceed
  ONLY per that policy. This is not fail-open — a policy WAS read and IS obeyed; the wall is on
  the *reader's IP*, not on the rule. Recommended as a small rider on Option A (it is what the
  U01 probe's "corpus numbers HOLD" conclusion already implicitly relies on for klinq's GraphQL
  side-door).

**Suggested ruling: A + C rider.** B only if we want www.perfume.com specifically.

---

# Pinned per-host facts

`QarenBot` is named by **zero** of the 22 hosts. Wherever robots is readable, QarenBot falls to
the `*` group and is **allowed** on the registry sample/PDP path AND on `/` (verified through
`robots_eval.can_fetch` today; per-group evidence in the JSON sidecar).

## Table 1 — the 6 "named-disallow" registry hosts (GCC panel)

U01's probe tagged these `named-disallow / policy-skip` from Railway. Residential reads today
show that tag conflates THREE different shapes — none of which names QarenBot:

| host | registry (tier / ccy / frag?) | datacenter (U01) | residential today | named AI groups actually say | QarenBot verdict today | at stake |
|---|---|---|---|---|---|---|
| bh.afnan.com | bahrain / BHD / fragrances | named-disallow → policy-skip | robots 200, 12,622B, 19 groups | ClaudeBot, anthropic-ai, GPTBot, PerplexityBot etc. each: Disallow /cart,/checkout,/account + **Allow /products/, /collections/, /blogs/** — AI bots are WELCOMED on PDPs | ALLOWED (sample + /) | live registry source, Gulf-panel CAPTURED |
| oman.afnan.com | gcc / OMR / fragrances | named-disallow → policy-skip | robots 200, 12,664B, 19 groups | identical to bh.afnan.com (same Shopify robots) | ALLOWED (sample + /) | live registry source, Gulf-panel CAPTURED |
| ashrafsbahrain.com | bahrain / BHD / frag+elec+grocery | named-disallow → policy-skip | robots 200, 6,164B, 73 groups | ClaudeBot, ClaudeBot/1.0, **Claude-SearchBot, Claude-User**, GPTBot, ChatGPT-User, CCBot, PerplexityBot, Bytespider, Amazonbot, Google-Extended, meta-externalagent — each **Disallow: /** | ALLOWED via `*` (sample + /) | live registry source, Gulf-panel CAPTURED |
| bh.cosmostore.org | gcc / USD / frag+skincare+makeup | named-disallow → policy-skip | robots 200, 2,859B, 11 groups | ClaudeBot, GPTBot, CCBot, Bytespider, Amazonbot, Google-Extended, meta-externalagent — each **Disallow: /** (no Claude-User) | ALLOWED via `*` (sample + /) | live registry source, Gulf-panel CAPTURED |
| bawwaba.om | gcc / OMR / frag+elec+makeup | named-disallow → policy-skip | robots 200, 1,947B, 10 groups | same 7-token AI ban set as cosmostore — each **Disallow: /** | ALLOWED via `*` (sample + /) | live registry source, Gulf-panel CAPTURED |
| oudworlds.com | gcc / OMR / fragrances | named-disallow → policy-skip | robots 200, 2,815B, 16 groups | CONTRADICTORY: template block disallows-all for ClaudeBot/GPTBot/CCBot/…, a LATER block re-allows `/` for ClaudeBot/GPTBot/Google-Extended/PerplexityBot. Under RFC same-token merge + Allow-beats-Disallow tie-break, ClaudeBot ends ALLOWED; CCBot/Bytespider/Amazonbot stay banned | ALLOWED via `*` (sample + /) | live registry source, Gulf-panel LOST_TO_EXTRACTOR (extractor bug, not access) |

**Sub-ruling implied (no code change today):** "named-disallow" ≠ "disallows us". For the two
Afnan stores it is a false positive — their robots explicitly allows AI bots on PDPs. For
ashrafsbahrain / cosmostore / bawwaba the AI-exclusion intent is explicit and site-wide; whether
QarenBot-via-`*` is inside or outside that intent is Ahmed's call (the Fragrantica precedent says
respect the intent; the letter of RFC 9309 says the `*` group governs an unnamed token).
ashrafsbahrain is the sharpest case: it names **Claude-User** with `Disallow: /` — the exact
token that triggered house rule 7 for Fragrantica.

## Table 2 — the 3 "unreadable-403" registry hosts (GCC panel)

| host | registry (tier / ccy) | datacenter (U01) | residential today | policy content (residential read) | QarenBot verdict | at stake |
|---|---|---|---|---|---|---|
| klinq.com | bahrain / BHD (magento_graphql) | robots unreadable-403; PDP 403 walled | robots 200, 3,343B, 40 groups | AI groups (ClaudeBot, anthropic-ai, GPTBot, ChatGPT-User, CCBot, PerplexityBot) explicitly **Allow: /**; `Mozilla` (browser UA) Disallow: /; meta-externalagent Disallow: / ; `*` allows PDPs, blocks logins/category-filter noise | ALLOWED (sample + /) | registry source; GQL side-door covers it from Railway (U01) |
| nazih.qa | gcc / QAR | robots unreadable-403; PDP 403 walled | robots 200, 1,511B, 1 group | plain Magento default `*` file (admin/app/lib paths); zero AI tokens | ALLOWED (sample + /) | registry source, Gulf-panel CAPTURED |
| numberc.com | gcc / KWD | robots unreadable-403; PDP 403 walled | robots 200, 5,575B, 9 groups | Shopify default `*` file; zero AI tokens | ALLOWED (sample + /) | registry source, Gulf-panel CAPTURED |

**Fact worth pinning:** for all three, "unreadable" is an **egress-IP artifact** — the WAF walls
the Railway ASN's reads of robots.txt itself; the policy, read from residential, is permissive.
This is the cohort Option C exists for. (klinq is also the measured case where identifying
honestly beats impersonating: its `Mozilla` group bans browser-shaped UAs while named tokens
ride the permissive `*` group — already documented in `robots_eval.py`.)

## Table 3 — the 13 render-residual hosts with unreadable robots (global corpus, B3)

Recovered verbatim from `B3/wall_census.json` → `policy_blocked_robots_unreadable` (13 hosts,
15 of 328 corpus rows; www.perfume.com has 3 rows, all others 1). None is in the U01 Railway
panel (that panel is GCC-registry-only) — "datacenter" state below is therefore *not measured*;
the census state was measured from the residential IP during the corpus build. All 15 rows have
`has_price: false` today, i.e. the price at stake is currently ZERO captured — these hosts are
the render-residual cohort this ruling gates.

| host | region | corpus rows (price today) | census state (residential, 2026-08-26/30) | residential TODAY | QarenBot verdict today |
|---|---|---|---|---|---|
| notino.de | DACH | 1 (none) | robots itself 403, Cloudflare challenge 5,988B | **robots 200**, 2,549B, permissive `*` (blocks images/order paths only) | ALLOWED on / |
| www.notino.it | EU-South | 1 (none) | robots 403, CF Turnstile | **robots 200** (same file) | ALLOWED on / |
| www.notino.nl | EU-South | 1 (none) | robots 403, CF | **robots 200** (same file) | ALLOWED on / |
| www.notino.pl | EU-South | 1 (none) | not fetched (CF challenge on PDP) | **robots 200** (same file) | ALLOWED on / |
| www.primor.eu | EU-South | 1 (none) | robots HTTP 202 AWS-WAF challenge page | **robots 200**, 6,503B, permissive `*` (query-param noise blocks) | ALLOWED on / |
| galeria.de | DACH | 1 (none) | robots 403, CF challenge 6,347B | still 403 (5,703B challenge) | UNREADABLE |
| fragrancebuy.ca | US/CA | 1 (none) | robots 403, CF "Just a moment" | still 403 (4,551B) | UNREADABLE |
| www.perfume.com | US/CA | 3 (none; PDPs serve 200!) | robots 403 CF; PDPs 200 usable | still 403 (5,393B) | UNREADABLE (content reachable — the Option-B host) |
| www.perfumeemporium.com | US/CA | 1 (none) | robots 403, CF | still 403 (4,555B) | UNREADABLE |
| www.pinalli.it | EU-South | 1 (none) | robots 403, CF managed challenge | still 403 (5,414B) | UNREADABLE |
| www.riteaid.com | US/CA | 1 (none) | robots 403, CF | still 403 (5,389B) | UNREADABLE |
| www.saksfifthavenue.com | US/CA | 1 (none) | robots 403, Akamai reference page 782B | still 403 (779B Akamai) | UNREADABLE |
| www.shoppersdrugmart.ca | US/CA | 1 (none) | robots 403, Akamai "Access Denied" 377B | still 403 (391B) | UNREADABLE |

**Net today:** the "13 unreadable" is really **8 unreadable + 5 recovered**. The 5 recovered
(notino ×4, primor) are readable-and-allowed and simply leave the cohort under Option A's
re-read schedule — no ruling needed for them anymore. The 8 that remain are all
Cloudflare/Akamai-walled on BOTH robots and PDPs (except perfume.com's PDPs), so fail-open on
robots alone recovers nothing without a render/vendor decision that is out of this ruling's
scope.

---

## bh.afnan.com adjudication — TODO (blocked on the descriptor-seed unit)

> **TODO [do not resolve in this unit]:** the search-descriptor seed unit (M7 D3 /
> `scripts/resolve_search_descriptors.py` run) will produce its own robots-checked verdict for
> bh.afnan.com's search surface. Adjudicate bh.afnan.com's registry status HERE once that
> verdict lands, combining: (a) this dossier's finding that its robots explicitly ALLOWS AI
> agents on `/products/` and `/collections/` (the U01 "named-disallow / policy-skip" tag is a
> false positive for this host), (b) the descriptor unit's search-surface verdict, and (c) the
> BHD-vs-SAR style currency check if flagged. Until then the U01 policy-skip stands
> operationally.

## Method + provenance (for re-runs)

- Live probe: 22 hosts, `GET /robots.txt` ONLY, one request per host, 2.2s spacing,
  `curl_cffi`, UA `QarenBot/1.0`, 2026-08-31, Bahrain residential IP. No PDP, no search, no
  render, no paid vendor was touched; fragrantica.com / parfumo.com were not contacted (house
  rule 7).
- Evaluation: `app.services.robots_eval.can_fetch(body, NAMED_AGENT, url)` at `a05a4f0`, plus
  `parse_groups` for the per-group facts. "ALLOWED" rows verified on both the registry
  `sample_url` and `/`.
- Inputs: U01 `RESULTS.txt` (65-host Railway egress tally: robots readable 56 / named-disallow
  6 / unreadable-403 3); `B3/wall_census.json` (the 13-host list + 328-row corpus);
  `_proof/global/corpus.json` (per-row `robots_note`, `has_price`); `data/bh_gcc_sources.json`
  (registry rows); B9 `bakeoff_table.md` / Gulf 94-host panel (capture verdicts).
- Compact per-host evidence (statuses, byte counts, matched groups, verdicts):
  `docs/policies/2026-08-31-robots-probe-evidence.json`. Raw bodies live in the U4 session
  scratchpad only (they are third-party content; not committed).
