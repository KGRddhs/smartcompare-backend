# Bundle C — D.1 Diagnostic Gate Evidence (Cold-Cache Probes)

**Status:** SKELETON — populated by qa-bundle-c (D.1.3) after backend-bundle-c ships A.2.1/A.2.2/A.2.3 logging hooks and Ahmed runs the 6-category cold-cache probe window.

**Plan reference:** `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` Section D.1.
**Spec reference:** `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` §1a / §1b / §1c.
**Branch:** `feature/bundle-c-scoring`.

> **GATE:** A.3.1 (§1a fix), A.3.2 (§1b factual_verdict builder), A.3.3 (§1c price-pipeline fix) MAY NOT land in the codebase until the three "Diagnosed root cause" subsections below are populated AND committed by qa-bundle-c.

---

## Probe configuration

- Endpoint: `https://web-production-58776.up.railway.app/api/v1/text/compare`
- Query params: `?q=<query>&region=bahrain&nocache=true`
- Railway env vars during window (set by Ahmed via team-lead handoff):
  - `DEBUG_STAGE_TIMINGS=true`
  - `DEBUG_VERDICT_RAW=true` (A.2.1 hook)
  - `DEBUG_FIRECRAWL_INVOCATIONS=true` (A.2.3 hook, if added)
  - `DEBUG_SCRAPEDO_INVOCATIONS=true` (A.2.3 hook, if added)
- Sleep 5-8s between probes to avoid rate-limit / breaker false trips.

### 6 probe queries (one per category)

| Category | Query | Status |
|---|---|---|
| electronics | `iPhone+16+vs+Galaxy+S25` | pending |
| skincare | `CeraVe+vs+Cetaphil+Moisturizing+Cream` | pending |
| supplements | `Centrum+vs+One+A+Day` | pending |
| fragrances | `Tom+Ford+Oud+Wood+vs+Creed+Aventus` | pending |
| fashion | `Levis+501+vs+Wrangler+Texas` | pending |
| grocery | `Nestle+Pure+Life+vs+Aquafina` | pending |

---

## §1a — Pros/cons empty diagnostic

**Symptom:** Brainstorm probes (2026-05-17, iPhone 16 vs Galaxy S25 + CeraVe vs Cetaphil) returned `pros: []` and `cons: []` on every product.

**Suspect list (per spec §1a):**
1. Verdict GPT JSON dropping `product_0_pros` / `product_1_pros` keys, silently swallowed by `comparison.pop(..., [])`.
2. `model_router.get_model(priority="high")` returning gpt-4o at `temperature=0.1` paired with long preference + cohort block — model omits fields.
3. `validate_verdict` (`extraction_service.py:700-701`) stripping fields before pop.
4. Prompt structural issue — pros/cons keys not specified clearly enough in the JSON schema example.

### Raw verdict capture (per category)

> Backend agent: paste raw `response.choices[0].message.content` payloads here, one per category. qa-bundle-c categorises each.

| # | Category | Raw payload contains `product_0_pros` key? | Raw payload contains `product_1_pros` key? | If present: length | Diagnosed cause |
|---|---|---|---|---|---|
| 1 | electronics | TBD | TBD | TBD | TBD |
| 2 | skincare | TBD | TBD | TBD | TBD |
| 3 | supplements | TBD | TBD | TBD | TBD |
| 4 | fragrances | TBD | TBD | TBD | TBD |
| 5 | fashion | TBD | TBD | TBD | TBD |
| 6 | grocery | TBD | TBD | TBD | TBD |

### Diagnosed root cause (FILL BEFORE A.3.1 LANDS)

> One sentence stating which of the 4 suspects above is firing, with file:line evidence.

**Root cause:** TBD

**Proposed fix scope (A.3.1):** TBD (must target the diagnosed cause; NO speculative re-prompt fallback unless evidence proves model genuinely cannot fit all fields).

**Sign-off (backend-bundle-c):** TBD

---

## §1b — `scoring_v2.factual_verdict` is None on every probe

**Symptom:** All brainstorm probes returned `scoring_v2.factual_verdict: null`.

**Suspect:** `_build_scoring_v2` (`response_builder.py:36`) calls a builder that never emits `line1` / `line2`.

### Trace evidence

> Backend agent: paste the relevant snippet from `response_builder.py` + the missing builder line numbers (or absence) here.

**File:line of `_build_scoring_v2`:** TBD
**Missing builder reference:** TBD
**Existing fields available for template (per spec §1b):**
- `line1` template — winner declaration with strongest factual delta (price gap / rating gap / top dim margin).
- `line2` template — runner-up's strongest counter-fact.

### Diagnosed root cause (FILL BEFORE A.3.2 LANDS)

**Root cause:** TBD

**Proposed fix scope (A.3.2):** Pure template builder, ZERO GPT cost. Add `line1` + `line2` from existing scoring fields. Regression test: `scoring_v2.factual_verdict` populated on every successful probe.

**Sign-off (backend-bundle-c):** TBD

---

## §1c — Price pipeline regression (mainstream queries fall to `estimated`)

**Symptom:** Both brainstorm probes hit `source_method="estimated"` for products that should hit Tier 1 Serper Shopping.

**Suspect list (per spec §1c, ranked by prior plausibility):**
1. Serper Shopping regional gap (Bahrain coverage thin for flagship products).
2. `api_budget_service` reporting exhausted Firecrawl credits (450 lifetime).
3. Circuit breakers tripped from earlier failures (3 failures → 10-min cooldown).
4. `_validate_price_query` rejecting queries upstream.
5. `_extract_price_from_html` parser regression.

### Per-category root-cause table (FILL FROM PROBE EVIDENCE)

| Category | Phase 1 wall (ms) | Tier traversed (1 → 1.5a → 1.5d → 2 → 3) | Final `source_method` | Firecrawl fired? (Y/N + outcome) | Scrape.do fired? (Y/N + outcome) | Serper Shopping response size | Diagnosed root cause |
|---|---|---|---|---|---|---|---|
| electronics | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| skincare | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| supplements | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| fragrances | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| fashion | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| grocery | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### API budget + circuit-breaker snapshot during window

> qa-bundle-c: capture from `api_budget_service` logs.

| Service | Credits remaining | Circuit-breaker state | Last failure timestamp |
|---|---|---|---|
| Firecrawl (lifetime 450) | TBD | TBD | TBD |
| Scrape.do (monthly 900) | TBD | TBD | TBD |
| Serper (lifetime 2200) | TBD | TBD | TBD |

### Diagnosed root cause (FILL BEFORE A.3.3 LANDS)

> Narrow the 5 suspects above to 1-2 actual causes per category.

**Root cause:** TBD

**Proposed fix scope (A.3.3):** TBD (must target the diagnosed cause).

**Sign-off (backend-bundle-c):** TBD

---

## D.1.4 — Diagnostic window closure

**Closed at:** TBD (timestamp once Ahmed unsets the four DEBUG_* env vars on Railway)

**Verification:** 1 probe run post-closure → `metadata.stage_timings_ms` MUST be absent from the response body.

**Per `memory/feedback_measure_before_optimize.md`:** diagnostic env vars cost zero in production with flag off, but leaving them on long-term invites accidental dependencies. Close the window cleanly.

---

## Next-action ranked list (qa-bundle-c populates after D.1.2 capture)

> Which Section A subsection unblocks each root cause.

1. TBD
2. TBD
3. TBD
