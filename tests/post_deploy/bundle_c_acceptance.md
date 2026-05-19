# Bundle C — Post-Deploy Acceptance Checklist

**Purpose:** Mechanically re-runnable 6-criteria checklist (plan D.6.2) for verifying Bundle C ship quality after every deploy that touches scoring / value / confidence / personalization code paths.

**When to run:**
- Once after D.4.3 (flag flipped ON in Railway).
- Once again 24h later as part of D.6.4 Sentry baseline diff window.
- Any future deploy that touches `scoring_service.py`, `extraction_service.py`, `response_builder.py`, `structured_comparison_service.py` while `ENABLE_BUNDLE_C_SCORING=true`.

**Plan reference:** `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` Section D.6.2.
**Spec reference:** `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` §8d / §8f.

---

## Probe set (7 queries — 6 categories + 1 `other` car-like)

| Slot | Category | Query | Expected `comparison_quality` |
|---|---|---|---|
| 1 | electronics | `iPhone+16+vs+Galaxy+S25` | `normal` |
| 2 | skincare | `CeraVe+vs+Cetaphil+Moisturizing+Cream` | `normal` |
| 3 | supplements | `Centrum+vs+One+A+Day` | `normal` |
| 4 | fragrances | `Tom+Ford+Oud+Wood+vs+Creed+Aventus` | `normal` |
| 5 | fashion | `Levis+501+vs+Wrangler+Texas` | `normal` |
| 6 | grocery | `Nestle+Pure+Life+vs+Aquafina` | `normal` |
| 7 | other (car) | `Toyota+Corolla+vs+Honda+Civic+2024` | `normal` (sub-scale `other_ultra` per spec §3f) |
| 8 (extra) | weird | `iPhone+16+vs+CeraVe+Moisturizer` | `weird` — verify hero overall renders `—`, verdict text reframes, NO banner |

```bash
mkdir -p /tmp/bundle-c-postdeploy
declare -A probes=(
  [electronics]="iPhone+16+vs+Galaxy+S25"
  [skincare]="CeraVe+vs+Cetaphil+Moisturizing+Cream"
  [supplements]="Centrum+vs+One+A+Day"
  [fragrances]="Tom+Ford+Oud+Wood+vs+Creed+Aventus"
  [fashion]="Levis+501+vs+Wrangler+Texas"
  [grocery]="Nestle+Pure+Life+vs+Aquafina"
  [other_car]="Toyota+Corolla+vs+Honda+Civic+2024"
  [weird]="iPhone+16+vs+CeraVe+Moisturizer"
)
for cat in "${!probes[@]}"; do
  q="${probes[$cat]}"
  curl -s "https://web-production-58776.up.railway.app/api/v1/text/compare?q=${q}&region=bahrain&nocache=true" > "/tmp/bundle-c-postdeploy/${cat}.json"
  sleep 8
done
```

---

## 6 acceptance criteria (per probe)

> Pass threshold: ≥6 of 7 mainstream probes (slots 1-7) satisfy all 6 criteria. Weird probe (slot 8) is asserted separately (see "Weird-comparison surface" below). If <6 → emergency hold; flip flag to false; re-investigate.

### Criterion 1 — Real prices land (not estimated)

```bash
jq '[.products[].price.source_method] | map(. == "estimated") | any' \
   /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:** `false` (no product is `estimated`) for ≥5 of 7 mainstream probes.

**Note:** This is the §1c fix verification. If the regression returns, A.3.3 root cause re-investigation needed.

### Criterion 2 — Pros + cons populated

```bash
jq '[.products[] | (.pros | length), (.cons | length)] | min' \
   /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:** `≥ 1` (every product has at least 1 pro AND at least 1 con).

**Note:** This is the §1a fix verification. If `0` for any probe, A.3.1 root cause re-investigation needed.

### Criterion 3 — Dimensions emit ≥ 3

```bash
jq '.scoring_v2.dimensions | length' /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:** `≥ 3` for mainstream probes. Weird probe may emit fewer per §2e silent omission.

### Criterion 4 — Confidence pills correct

```bash
jq '.scoring_v2.confidence_legs' /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:**
- Each pill has `level: "strong" | "acceptable" | "weak"`.
- **Price pill HIDDEN** when any product `source_method == "estimated"` (per spec §5c). Verify in UI screenshot for slot 7 (`other_car`) which may legitimately have one estimated leg.

### Criterion 5 — `value_match` captions fire

```bash
jq '[.products[].value_match] | unique' /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:** Each product has a `value_match` enum value (`in_range` | `above_range` | `below_range`).

**UI verification:** When `value_match != in_range`, caption renders per spec §4d:
- `above_range` → "Above your usual range".
- `below_range` → "Within your range".
- 2+ tiers off → "Above your usual range — but here's why" + `key_tradeoff` snippet.

### Criterion 6 — Personalization chip renders when shifts exist

```bash
jq '.scoring_v2.personalization.applied_shifts' /tmp/bundle-c-postdeploy/<probe>.json
```

**Pass:** Array present (may be empty `[]` for anonymous / no-priorities users). If the probe used a test user with priorities set, array length ≥ 1.

**UI verification:** When `applied_shifts[]` empty → chip HIDDEN entirely (per spec §7a).

---

## Granular evidence-acceptance criteria

### Per-category Phase 1 wall budget

| Probe | Cold-cache target | Warm-cache target | Hard cap |
|---|---|---|---|
| electronics | ≤17s | ≤10s | 25s (`STREAM_HARD_CAP_SECONDS`) |
| skincare | ≤17s | ≤10s | 25s |
| supplements | ≤14s | ≤8s | 25s |
| fragrances | ≤22s | ≤14s | 25s |
| fashion | ≤22s | ≤14s | 25s |
| grocery | ≤14s | ≤8s | 25s |
| other_car | ≤25s | ≤17s | 25s |

Inspect: `metadata.total_time_ms` or curl `time -v` for total wall.

### Confidence pill color sanity

- Probe with `source_method == "firecrawl"` or `"page_scrape"` → Price pill emerald or amber (not gray).
- Probe with `source_method == "estimated"` → Price pill **ABSENT** from UI (not gray, not amber — absent per spec §5c).

### Weird-comparison surface (slot 8)

For probe `iPhone+16+vs+CeraVe+Moisturizer`:
- `scoring_v2.comparison_quality === "weird"`.
- Hero overall score renders `—` (em-dash), not a number.
- Verdict text reframes naturally (e.g., "These products serve different purposes" — see spec §2e).
- **NO** top-of-screen banner. **NO** warning bar. **NO** apology copy.

### Personalization chip empty path

For brand-new anonymous user (no priorities set):
```bash
curl -s "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+16+vs+Galaxy+S25&region=bahrain&nocache=true&user_id=<fresh-uuid>"
```
- `applied_shifts` is `[]`.
- UI does NOT render the personalization chip.

### Backend-internals leak grep

```bash
cat /tmp/bundle-c-postdeploy/*.json \
  | jq '..' \
  | grep -iE '(weight|coefficient|cap_pct|shift_magnitude|scaling_factor)'
```
**Pass:** Zero matches. Backend may compute these internally; they MUST NEVER appear in any API response field that the mobile client could parse (per `memory/feedback_no_backend_internals_in_reveals.md`).

### Forbidden vocabulary grep (i18n + response copy)

```bash
cat /tmp/bundle-c-postdeploy/*.json | grep -iE "(estimated|reference price|indicative|couldn't|try again|Failed to|تعذر|فشل)"
```
**Pass:** Zero matches in user-facing strings (`winner_declaration`, `winner_reason`, `key_tradeoff`, `factual_verdict.line1`, `factual_verdict.line2`, `value_context`, `best_for`, `dimensions[].label`, `dimensions[].delta_text`).

> Note: `source_method == "estimated"` is acceptable as the BACKEND ENUM (not displayed). The grep above will match the enum string in the JSON — verify any match is the enum value, not a copy string.

---

## Sign-off block

| Field | Value |
|---|---|
| Run timestamp | TBD |
| Railway deploy SHA | TBD |
| `ENABLE_BUNDLE_C_SCORING` state | TBD |
| Probes passed | TBD / 7 |
| Weird probe outcome | TBD |
| Sentry baseline diff (24h) | TBD |
| EAS Update group ID | TBD |
| Tester-device confirmation (D.6.5) | TBD |
| qa-bundle-c sign-off | TBD |
