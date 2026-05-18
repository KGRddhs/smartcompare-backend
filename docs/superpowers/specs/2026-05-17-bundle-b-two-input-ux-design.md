# Bundle B — Two-Input UX Redesign (Design Specification)

**Date:** 2026-05-17
**Status:** Approved (Ahmed)
**Bundle:** B — Comparison entry redesign
**Brand:** Qaren (قارن)
**Anchors:** Inherits all Build Principles + Section 1 visual system + Section 4a chip rail from `docs/plans/2026-05-06-qaren-ux-redesign-design.md`. Where this spec is silent, the 2026-05-06 design rules.

---

## 1. Goals

1. Convert text-compare from one search box (`SearchOverlay`) to **two text boxes (Product A / Product B)** with explicit per-box semantics.
2. Re-skin URL-compare's two existing URL boxes to the same Qaren visual identity (today they sit inside the camera card slot with bare `bg.secondary` styling).
3. Establish a **single shared shell** (`TwoInputShell`) that both modes render through, so future polish (recent searches, autocomplete) lands in one place.
4. Add **output-side content moderation** so the app never surfaces explicit, illicit, or violent comparisons regardless of input source (text, URL, camera).
5. Extend the **dual-shape Pydantic pattern** to `/api/v1/text/compare` so explicit `product_a` + `product_b` skip `parse_product_query()` for higher-confidence extraction.
6. Preserve every Build Principle from the 2026-05-06 redesign — especially #4 "Nothing scary."

## 2. Non-goals

- No change to the 3-mode equal chip rail (Scan / Link / Type) — § 4a of 2026-05-06 redesign stands.
- No change to `ScanCameraScreen` photo capture flow — only the "ready" celebration moment is added.
- No change to Results screen.
- No change to backend price pipeline, scoring, personalization, cohort matching.
- No new fonts, colors, or motion tokens — everything reuses `theme/index.ts` + `theme/motion.ts`.
- No sound — `Haptics.NotificationFeedbackType.Success` is the auditory layer.

---

## 3. Component Anatomy & Layout

### 3.1 The shared shell

```
┌──────────────────────────────────────────────────┐
│  Compare anything.                                │ ← hero (16pt body emphasis, unchanged)
│                                                   │
│  Categories ──── [📱][💄][💊][👗][🛒][→]         │ ← unchanged
│                                                   │
│   ╭─────────────────────────────────────────╮     │
│  ①│ Product A · e.g. iPhone 15         ⊗  │     │ ← Box A, 16px radius
│   ╰─────────────────────────────────────────╯     │
│  │                                                │
│  │  ◜  vs  ◝   ← emerald-tinted pill on hairline  │
│  │                                                │
│   ╭─────────────────────────────────────────╮     │
│  ②│ Product B · Galaxy S24             ⊗  │     │ ← Box B
│   ╰─────────────────────────────────────────╯     │
│                                                   │
│  ┌─────────────────────────────────────────┐      │
│  │              Compare                     │     │ ← full-width black CTA
│  └─────────────────────────────────────────┘      │
│                                                   │
│  [📷 Scan]  [🔗 Link]  [✎ Type] ●                │ ← existing mode chips
│                                                   │
│  (BonusCountdownCard if active)                   │ ← existing, unchanged
│  2 of 5 comparisons left this month               │ ← ComparisonCounter, unchanged
└───────────────────────────────────────────────────┘
```

### 3.2 Visual specs

| Element | Spec |
|---|---|
| **Numeral circles ①/②** | 24px diameter, leading-edge of each box. Outlined (border `border.medium`, bg white) when empty/typing. Filled (`accent` emerald + white tick) when validated on blur. RTL: numerals + hairline swap to right edge. |
| **Hairline** | 1px `border.light`, runs from inside circle ① to inside circle ②, behind the "vs" pill. |
| **"vs" pill** | Height 24px, padding-x 12px, bg `accent.light` (#ECFDF5), text `accent.dark` (#059669), 11pt Geist SemiBold. Caps for EN ("VS"), uncased AR ("مقابل"). Sits on the hairline midpoint. |
| **Boxes** | 16px radius, 48px tall, 1px `border.light` resting / 2px `text.primary` on focus. Bg white. 16pt body input. |
| **⊗ clear button** | Trailing-edge inside box (or leading in AR). Visible only when box has content AND is focused. 16px size, color `text.placeholder`. |
| **Compare CTA** | Full-width below the boxes, 48px tall, 12px radius, bg `cta.primary` (black) / 50% opacity when disabled. White 16pt SemiBold label. On "ready" → emerald glow ring expand 0 → 12px alpha over 240ms. |

### 3.3 State preservation across modes

- **Text mode** and **Link mode** keep independent Box A / Box B state in their own controlled refs inside `TwoInputShell`.
- Switching Text → Link → Text restores the user's text inputs.
- Auto-mode-switch on URL paste (§ 4.1) transfers content to the destination mode **without clearing the origin**.

### 3.4 BonusCountdownCard placement

- Visible above `ComparisonCounter` when an active referral bonus exists AND `canCompare === true`.
- **Hidden** when `canCompare === false` (paywall-banner state — see § 6.2). Bonus surface is a distraction from the conversion moment.

---

## 4. Interaction Behaviors

### 4.1 Paste-detection

**4.1.1 Auto-split** (Text + URL modes)
- **Trigger:** user pastes a string into Box A (or Box B, while the other is empty).
- **Predicate:** `looksLikeTwoProducts(s)` — extracted from `SearchOverlay.tsx` into `src/utils/parseComparisonShape.ts` (shared util). Regex matches `\s(vs|&|and|or|أو|مقابل)\s|,`. Both halves must be ≥2 chars after split.
- **Behavior:** fill Box A with left half, Box B with right half. Both halves trimmed. Cursor lands at end of Box B.
- **Feedback:** inline emerald caption below Box B for 2.5s — `home.compare.paste_split_caption`. No modal, no toast.
- **Edge:** if Box B already has content when paste hits Box A, fall back to raw paste (don't clobber user's typing).

**4.1.2 Auto-mode-switch** (Text mode only)
- **Trigger:** user pastes a string matching `^https?://` into Text-mode Box A or Box B.
- **Predicate:** `^https?://[^\s]+$` (basic URL shape; final validation runs at submit via `URL` constructor).
- **Behavior:** animate mode chip from Type → Link (240ms cross-fade, same as existing chip transitions). Transfer pasted URL into Link-mode's Box A. Focus stays on Link-mode Box A.
- **Feedback:** inline emerald caption below Box A for 2.5s — `home.compare.mode_switch_caption`.
- **Edge:** if both Link-mode boxes already have URLs from a prior session, skip the switch and just raw-paste into the current Text box (don't overwrite Link state).

### 4.2 Validation timing

- **Per-box validation runs on `onBlur`** — neutral while typing, validates the moment user moves on.
- **Text mode predicate:** `trimmed.length >= 2 && trimmed.length <= 80 && !controlCharsRegex.test(trimmed)`. Control chars stripped silently before predicate.
- **URL mode predicate:** `new URL(trimmed).protocol in ['http:', 'https:'] && trimmed.length <= 2048`.
- **Visual transitions:**
  - Empty → outlined circle, neutral border, no tick.
  - Valid (post-blur) → emerald-filled circle + white tick, spring scale 1.0 → 1.12 → 1.0 over 320ms.
  - Invalid (post-blur, non-empty) → circle stays outlined, no red border (Build Principle #4 — never frame as scary). Box border stays neutral. Compare CTA simply stays disabled. Re-focus + edit → predicate re-runs on next blur.
- **No keystroke-level re-validation** — avoids red/green flicker while typing.

### 4.3 "Ready to compare" celebration

Fires the moment both circles flip to emerald (Text/URL: both boxes blur-valid; Scan: `capturedImages.length === 2`).

Three things happen simultaneously:
1. **Both circles** pulse — spring scale 1.0 → 1.12 → 1.0 (320ms, damping 18) in unison.
2. **Compare CTA "lights up"** — 50% → 100% opacity over 200ms + emerald glow ring (`accent.glow`) expands 0 → 12px alpha over 240ms.
3. **Haptic** — `Haptics.NotificationFeedbackType.Success`, single pulse. Wrapped in the same try/catch pattern as `ModeChip` to survive test mocks.

**Pattern is shared across modes.** Establishes a learnable cross-mode signal.

**No shake animation anywhere.** Shake is iOS error convention (Apple Mail / Settings / Safari). Build Principle #4 explicitly forbids it. Negative-assertion test required.

**Reverse direction:** if user edits a valid box back to invalid → circle un-fills smoothly (300ms ease-out, no haptic), CTA dims back to disabled state. No "un-celebrate" haptic.

### 4.4 Focus + keyboard flow

- **Mode entry → Box A auto-focuses after 250ms** (lets mode-chip spring + box hairline animation settle).
- **Box A `returnKeyType="next"`** → focuses Box B.
- **Box B `returnKeyType="search"`** in Text mode, **`"go"`** in URL mode → submits if both valid; dismisses keyboard otherwise.
- **`KeyboardAvoidingView`** wraps the shell — CTA always visible above keyboard.
- **`ScrollView`** wraps the content — small phones with keyboard up can still scroll to see everything.
- **Tap outside boxes** (hero, chip rail, category strip) → dismisses keyboard.
- **⊗ clear button** empties box without dismissing keyboard or losing focus.
- **Per-mode focus memory:** switching mode + returning keeps the last-focused box highlighted but does NOT auto-focus again (only first entry auto-focuses).

---

## 5. Backend Contract + Content Moderation Pipeline

### 5.1 Dual-shape on `/api/v1/text/compare`

`TextCompareRequest` widens to accept both shapes via Pydantic `model_validator`:

```python
class TextCompareRequest(BaseModel):
    query: Optional[str] = None              # legacy single-string
    product_a: Optional[str] = None          # NEW
    product_b: Optional[str] = None          # NEW
    region: str = "bahrain"
    include_specs: bool = True
    include_reviews: bool = True
    include_pros_cons: bool = True
    selected_category: Optional[str] = None

    @model_validator(mode="after")
    def normalize_shape(self) -> "TextCompareRequest":
        has_pair = bool(self.product_a and self.product_b)
        has_query = bool(self.query)
        if has_pair and has_query:
            raise ValueError("Send EITHER query OR product_a+product_b")
        if not has_pair and not has_query:
            raise ValueError("Send product_a+product_b OR query")
        if has_pair:
            self.query = f"{self.product_a.strip()} vs {self.product_b.strip()}"
        return self
```

When `product_a` + `product_b` arrive, the service **skips `parse_product_query()`** entirely — the inputs ARE the parsed pair, with higher confidence than regex extraction. `compare_from_text()` gains an optional `explicit_pair: tuple[str, str] | None` kwarg routed past the parser.

**URL endpoint untouched** — `/api/v1/url/compare` already takes `url1` + `url2`.

**Backwards compat:** all existing clients (shared comparison links, web embeds) still post `query: "X vs Y"` and work unchanged.

### 5.2 Content moderation pipeline

| Layer | Where it sits | Cost |
|---|---|---|
| **L1 — Query pre-filter** | `app/services/content_safety_service.py` (NEW). Called at the top of `compare_from_text()` + `compare_from_urls()`. Keyword + lightweight pattern check against EN+AR blocklist: weapons, illegal drugs, adult products, gore, self-harm. Reject → return `{success: false, code: "CONTENT_UNAVAILABLE"}`. | $0 |
| **L2 — Image / shopping result filter** | Inside `price_service.py` Tier 1 (Serper Shopping). Drop any `shopping_item` whose title/snippet hits the same blocklist BEFORE it reaches GPT extraction. | $0 |
| **L3 — Output moderation** | `openai_service.moderate(text)` → `omni-moderation-latest`. Called once on the assembled response (verdict text + product names + review excerpts joined). If flagged for sexual / violence / hate / self-harm / illicit → wipe response, return graceful refusal. **SSE flow:** moderation runs before the `complete` event; if rejected, replace the streamed accumulator with the refusal payload. | $0 (free per OpenAI) |
| **L4 — Camera vision** | `image_routes.py` runs L3 on the GPT-4o-mini vision identification output BEFORE triggering compare. If flagged, identification "fails" silently with the existing "Sharper match coming up" copy. | $0 |

**Graceful refusal copy** (`home.compare.unavailable_*`):
- EN: "We don't compare this category" / "Try a different product — Qaren works best with everyday shopping items."
- AR: "لا نقارن منتجات من هذا النوع" / "جرّب منتجاً مختلفاً — قارن يعمل أفضل مع منتجات التسوّق اليومية."

No "blocked" / "rejected" / "forbidden" language — Build Principle #4.

**Audit logging:** every L1/L3 rejection writes one row to `admin_audit_log` with event `content_blocked`, layer (`query_prefilter` / `moderation_api` / `image_filter` / `vision_moderation`), and a SHA-256 hash of the offending input (not the input itself — privacy).

### 5.3 Backend regression tests (`tests/test_security_regression.py` extensions)

- `test_dual_shape_product_a_b_hits_sanitizer` — explicit pair shape can't bypass injection sanitizer
- `test_content_safety_query_prefilter_blocks_weapons`
- `test_content_safety_moderation_api_wipes_explicit_output`
- `test_content_safety_image_filter_drops_unsafe_shopping_items`
- `test_camera_vision_moderation_blocks_explicit_capture`

---

## 6. Freemium Behavior

### 6.1 When `canCompare === true`

- `BonusCountdownCard` visible above counter if active bonus
- `ComparisonCounter` "X of Y left" at bottom (unchanged placement)
- Normal `TwoInputShell` with both boxes + CTA

### 6.2 When `canCompare === false` — paywall takeover

Single, undiluted conversion moment. Strip every distraction.

| Element | State |
|---|---|
| **Paywall banner** | Replaces `TwoInputShell` in the boxes slot. Only thing competing for attention in the middle of the screen. |
| **BonusCountdownCard** | **Hidden.** Surfacing a future bonus invites "I'll wait" and dilutes conversion. Returns the moment `canCompare` flips back. |
| **`ComparisonCounter`** | **Hidden.** "0 of 3 left" is depressing + redundant — banner copy says it cleaner. |
| **Mode chips** | Dimmed to 50% opacity, still tappable but show the same banner regardless. Doing nothing on tap would feel broken; dim communicates "these still work, but the answer is the same." |
| **Category strip** | Hidden — no value when user can't compare. |
| **Hero "Compare anything."** | Hidden — banner title takes its place. |

**Banner anatomy:**

```
┌─────────────────────────────────────┐
│  ┌───────────────────────────────┐  │
│  │ ⊙                             │  │ ← small emerald-tinted icon
│  │                               │  │
│  │ You've used your free         │  │ ← title (display 28pt)
│  │ comparisons                   │  │
│  │                               │  │
│  │ Unlock unlimited compares     │  │ ← body (16pt)
│  │ with a friend code or         │  │
│  │ premium.                      │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │     See options         │  │  │ ← black CTA → Paywall screen
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Banner CTA → Paywall screen.** Paywall already presents premium AND referral entry points side-by-side, so referral isn't gone — it's one layer deeper behind explicit conversion intent.

**Recovery:** once `canCompare` flips to `true` (purchase / new month / bonus credits) → banner unmounts → full TwoInputShell + counter + bonus card return with empty boxes.

---

## 7. RTL, i18n, Copy

### 7.1 RTL behavior

| Element | LTR (EN) | RTL (AR) |
|---|---|---|
| Numeral circles | Leading-edge **left** of each box | Leading-edge **right** of each box |
| Connecting hairline | Runs along **left** edge between ①/② | Runs along **right** edge between ②/① |
| "vs" pill | Centered on hairline | Same — label switches to "مقابل" |
| ⊗ clear button | Inside box, **right** edge | Inside box, **left** edge |
| Box text alignment | `textAlign: 'auto'` → LTR | `textAlign: 'auto'` → RTL |
| Mode chips | Scan / Link / Type left → right | Type / Link / Scan right → left (`I18nManager.isRTL` flip) |

**Cairo line-height multiplier 1.7x** applied to all AR text. Box height stays 48px — AR placeholders fit vertically without clipping.

### 7.2 i18n keys

Add to both `en.json` + `ar.json`:

```json
{
  "home.compare.box_a_text": "Product A · e.g. iPhone 15",
  "home.compare.box_b_text": "Product B · e.g. Galaxy S24",
  "home.compare.box_a_url": "First link · paste from Amazon, Noon, etc.",
  "home.compare.box_b_url": "Second link",
  "home.compare.vs_pill": "VS",
  "home.compare.cta": "Compare",
  "home.compare.cta_loading": "Comparing…",
  "home.compare.paste_split_caption": "Split into two — edit if needed",
  "home.compare.mode_switch_caption": "Detected a link — switched to Link",
  "home.compare.paywall_banner_title": "You've used your free comparisons",
  "home.compare.paywall_banner_body": "Unlock unlimited compares with a friend code or premium.",
  "home.compare.paywall_banner_cta": "See options",
  "home.compare.unavailable_title": "We don't compare this category",
  "home.compare.unavailable_body": "Try a different product — Qaren works best with everyday shopping items.",
  "home.compare.a11y_box_a_valid": "Product A entered",
  "home.compare.a11y_box_b_valid": "Product B entered",
  "home.compare.a11y_ready": "Ready to compare"
}
```

Arabic mirror — see same set with translations from § 4b of brainstorm transcript (copied verbatim into both locales by Frontend agent).

### 7.3 Deprecated keys (removed in same PR)

```
home.url.placeholder1    → home.compare.box_a_url
home.url.placeholder2    → home.compare.box_b_url
home.url.cta             → home.compare.cta
home.url.empty_title     → (removed — disabled CTA replaces error toast)
home.url.empty_body      → (removed)
home.url.invalid_title   → (removed)
home.url.invalid_body    → (removed)
home.search.needTwoHint  → (removed — two boxes obviate the hint)
```

`home.search.placeholder` kept (still used by History search bar).

### 7.4 Copy tone audit (Build Principle #4)

Every new string passes the "never scary" rule:
- ✅ No "couldn't", "failed", "error", "try again"
- ✅ AR forbidden words ("تعذر", "فشل") absent
- ✅ Paywall banner reframes "out of comparisons" as "you've used your free ones" + "unlock"
- ✅ Content-unavailable refusal reframes as "we don't compare this category" — Qaren's choice, not a failure
- ✅ Invalid state has no error copy — disabled CTA + outlined circle do the work silently

Validator: `SmartCompareApp/src/i18n/.copy-policy.json` updated with the new key allowlist.

---

## 8. Analytics

All events fire via the existing `trackEvent()` helper in `src/services/api.ts`. snake_case payloads.

| Event | Payload | Fire condition |
|---|---|---|
| `compare_entry_view` | `{ mode: 'text'\|'url'\|'scan' }` | Shell renders OR mode chip selected. One event per mode-entry. |
| `compare_entry_paste_split` | `{ source_box: 'a'\|'b', mode }` | Auto-split fills both boxes. |
| `compare_entry_mode_autoswitch` | `{ from, to, trigger: 'url_paste' }` | URL-paste fires mode chip animation. |
| `compare_entry_ready` | `{ mode, time_to_ready_ms }` | Both circles flip emerald (celebration fires). Timing measured from most recent `compare_entry_view`. |
| `compare_entry_submit` | `{ mode, used_paste_split, used_autoswitch }` | CTA tapped while both valid. Booleans capture polish usage. |
| `compare_entry_paywall_banner_view` | `{ mode }` | Banner replaces boxes. |
| `compare_entry_paywall_banner_tap` | `{ mode }` | User taps banner CTA. |
| `compare_entry_content_block` | `{ mode, layer }` | Output safety pipeline rejected. `layer ∈ {query_prefilter, image_filter, moderation_api, vision_moderation}`. Fired from unified error parser when backend returns `code: "CONTENT_UNAVAILABLE"`. |

**Funnels:**
- View → Ready → Submit (per mode) — drop-off detection
- View → Banner View → Banner Tap — paywall conversion rate
- Submit → Content Block — moderation visibility

**Privacy:** no payload contains the user's typed text or pasted URLs. Only mode, booleans, timing, `source_box` enum.

---

## 9. File Inventory + Build Sequence

### 9.1 New files

| Path | Purpose |
|---|---|
| `SmartCompareApp/src/components/TwoInputShell.tsx` | Shared shell — props: `mode: 'text' \| 'url'`, validation predicates, callbacks. Renders numerals, hairline, vs pill, boxes, CTA, captions. |
| `SmartCompareApp/src/components/PaywallBanner.tsx` | Renders in TwoInputShell's slot when `!canCompare`. |
| `SmartCompareApp/src/utils/parseComparisonShape.ts` | Extracted from `SearchOverlay.tsx`. Exports `looksLikeTwoProducts(s)` + `splitComparisonShape(s) → [a, b] \| null`. |
| `SmartCompareApp/src/utils/urlPasteDetect.ts` | `looksLikeUrl(s) → boolean`. |
| `app/services/content_safety_service.py` | L1 query pre-filter + L2 shopping result filter + L3 moderation API wrapper. Singleton loaded at startup. |
| `app/data/content_blocklist.json` | EN+AR keyword/pattern lists for L1 + L2. Committed; not gitignored. |
| `tests/test_content_safety_service.py` | Unit tests per layer (mock OpenAI moderation client for L3). |
| `tests/test_two_input_shape.py` | Backend regression for dual-shape `product_a`/`product_b` endpoint. |
| `SmartCompareApp/src/components/__tests__/TwoInputShell.test.tsx` | Component tests — render, paste-split, mode-switch, validation, celebration, negative-assertion (no shake anywhere). |
| `SmartCompareApp/src/components/__tests__/PaywallBanner.test.tsx` | Banner render + tap analytics. |

### 9.2 Modified files

| Path | Change |
|---|---|
| `SmartCompareApp/src/screens/HomeScreen.tsx` | Remove inline URL inputs + inline text routing. Render `TwoInputShell` for Text + Link modes. Add `canCompare`-gated branching to `PaywallBanner`. Wire new analytics events. Keep camera modal launch + BonusCountdownCard logic. |
| `SmartCompareApp/src/components/SearchOverlay.tsx` | **Delete.** TwoInputShell replaces it. (Recent-searches surface deferred — § 11.) |
| `SmartCompareApp/src/screens/ScanCameraScreen.tsx` | Add 3-part celebration (photo-slot ticks, glow on Capture-done CTA, Success haptic) when `capturedImages.length === 2`. |
| `SmartCompareApp/src/services/api.ts` | Add `compareTextPair(productA, productB, opts)`. Update `streamComparison()` to accept either `query` OR `{ product_a, product_b }`. |
| `SmartCompareApp/src/i18n/en.json` + `ar.json` | Add `home.compare.*`. Remove deprecated keys per § 7.3. |
| `SmartCompareApp/src/i18n/.copy-policy.json` | Add new keys to audit allowlist. |
| `app/api/text_routes.py` | Widen `TextCompareRequest` with dual-shape `model_validator`. Wire `product_a`/`product_b` through `compare_from_text(explicit_pair=...)`. |
| `app/services/structured_comparison_service.py` | Accept `explicit_pair: tuple[str, str] \| None` kwarg in `compare_from_text` + `compare_from_text_streaming`. When provided, skip `parse_product_query()`. Call L1 pre-flight, L3 on assembled response before sync return / before SSE `complete` event. |
| `app/services/price_service.py` | Apply L2 image/shopping filter inside Tier 1 — drop unsafe `shopping_item` entries before GPT extraction. |
| `app/api/image_routes.py` | Add L4 vision moderation between identify and compare. If flagged, return `need_second_product`-style graceful response. |
| `app/services/audit_service.py` | Add `log_content_blocked(layer, query_hash)` helper. |
| `tests/test_security_regression.py` | Add 5 new tests from § 5.3. |

### 9.3 Build sequence

1. **Backend (Opus 1):** content_safety_service skeleton + blocklist JSON + dual-shape `TextCompareRequest` + `structured_comparison_service` kwarg + `image_routes` L4 + `price_service` L2 + audit logging.
2. **Frontend (Opus 2):** `TwoInputShell` + `PaywallBanner` + utils + i18n keys + `HomeScreen` wiring + `ScanCameraScreen` celebration + `api.ts` dual-shape helper. Blocked by Opus 1 endpoint shape stabilizing (Pydantic commit lands within ~30 min so Opus 2 starts in parallel after that).
3. **Tests (Opus 3):** `test_content_safety_service`, `test_two_input_shape`, `test_security_regression` extensions, `TwoInputShell.test.tsx`, `PaywallBanner.test.tsx`. Blocked by Opus 1 + 2 each landing module skeletons.
4. **QA (Opus 4):** cross-mode integration walkthrough, RTL pass on emulator (AR locale), copy audit against `.copy-policy.json`, analytics event firing verification, regression that existing `/text/compare` `query:` clients still work, freemium banner state walkthrough at each `canCompare` transition, content_safety pipeline end-to-end with seeded blocklist entries.

---

## 10. Testing Strategy

- **Backend unit:** `content_safety_service` per layer (mock OpenAI moderation for L3). Dual-shape Pydantic validators. Image filter dropping shopping items. ~30 new tests, target 90% coverage on new modules.
- **Backend regression:** `tests/test_security_regression.py` extensions (§ 5.3). All 98 existing security tests must still pass.
- **Backend integration:** `tests/test_two_input_shape.py` hits Railway via real endpoint with both shapes + content_unavailable refusal path. Marked `@pytest.mark.live_unit` (~$0.05).
- **Frontend component:** `@testing-library/react-native`. Render `TwoInputShell` in both modes, simulate paste with split-shape + URL-shape strings, assert auto-split + mode-switch fire, assert numeral circle states, assert haptic + celebration fires, assert analytics events emitted with correct payloads. **Negative assertion: shake animation never runs anywhere.**
- **Frontend i18n audit:** existing `.copy-policy.json` validator catches forbidden words in new keys.
- **Frontend RTL:** snapshot tests in both EN + AR locales; visual diff on numeral positions, hairline edge, ⊗ button placement.
- **Manual QA checklist:** AR keyboard auto-focus, paste split with Arabic separators (`أو`, `مقابل`), iPhone SE narrow-screen layout, slow network during celebration (don't fire celebration if backend fails), banner state on each `canCompare` source (used base, used bonus, new month tick).

**Coverage target:** 80% on every new module (`TwoInputShell`, `PaywallBanner`, `parseComparisonShape`, `urlPasteDetect`, `content_safety_service`). Lower thresholds rejected by reviewer.

---

## 11. Out of Scope (deferred to follow-up PRs)

These were considered during brainstorming and intentionally deferred. **They must be done later** — not abandoned. Tracked in `MEMORY.md` Pending follow-ups after this spec ships.

| Item | Why deferred | Trigger to revisit |
|---|---|---|
| **Recent-searches chips below TwoInputShell** | Adds per-mode storage complexity (chip taps fill which box? both?). Baseline ships cleaner without it. | Tester feedback shows users re-typing recent queries OR analytics shows high "view → no submit" drop |
| **Per-box autocomplete from Serper** | Doubles API budget per typing session; premium polish, not baseline. | Tester data shows confusion typing product names OR conversion lift hypothesis from PM |
| **"Doesn't look like a product name" soft hint** | Niche; only valuable if tester confusion is observed for non-product inputs ("hello world", "lol"). | Support volume on bad-input comparisons |
| **Admin dashboard `content_safety` tile** | Audit logging lands in v1 (queryable via SQL); visual dashboard follows. | Once content_blocked volume exceeds ~50/day OR ops asks for it |
| **Sound on "ready" celebration** | Sound design + `expo-av` + audio-session-category + silent-switch respect + in-app on/off toggle = ~1 day work + dependency. Haptic is enough for v1. | Tester feedback explicitly asks for sound |
| **Per-mode shared CTA label variants** | "Compare links" vs "Compare products" — today one shared "Compare" label. Could specialize. | A/B test hypothesis |
| **Voice input for boxes** | Native speech-to-text via `@react-native-voice/voice` — interesting accessibility win. Out of scope for Bundle B. | Accessibility audit pre-App-Store soft-launch |

**Memory entry to add post-PR:** Bundle B deferred items become a follow-ups bullet in `MEMORY.md` under "Pending follow-ups."

---

## 12. Team Execution Rules (4-Opus mandate)

This bundle ships via a **4-agent TeamCreate** with the following hard rules:

### 12.1 Composition

- **All Opus.** No Sonnet, no Haiku, no exceptions.
- Four roles: **Backend**, **Frontend**, **Test**, **QA**.
- `mode: "bypassPermissions"` (REQUIRED — sandbox blocks Bash otherwise, per CLAUDE.md Session 47 learning).

### 12.2 Completion bar — feature is 100% or it doesn't ship

- The team is **not disassembled** until every spec section above is implemented, tested, and reviewed.
- "Done" is not the agent declaring done. "Done" is **another team member signing off** on it.
- Partial implementations are sent back. Skipped tests are sent back. Stubbed-out files are sent back.

### 12.3 Cross-QA — every member reviews another's work

- **Backend's work is QA'd by Test agent + QA agent.**
- **Frontend's work is QA'd by Test agent + QA agent.**
- **Test agent's tests are QA'd by Backend (for backend tests) + Frontend (for frontend tests) — they validate the tests actually exercise the spec, not just pass trivially.**
- **QA agent runs the end-to-end manual walkthrough + cross-mode integration + RTL pass + copy audit + analytics verification.**

When any reviewer finds an issue, the work goes **back to the original author** with a specific failure note. Author re-does, re-submits. Loop until QA'd clean.

### 12.4 Idling discipline — no agent sits doing nothing

If an agent is waiting for another's output (e.g., Frontend blocked on Backend's Pydantic shape), the idling agent picks up **one of these in priority order:**

1. **Write red-green tests** for unstubbed spec sections — drive coverage toward the 80% target. Red tests committed first; green tests follow once dependencies land.
2. **Wait for QA feedback to return** — if the agent has work currently in cross-QA, they wait for the reviewer's notes.
3. **Triage open follow-ups** in `MEMORY.md` Pending follow-ups (only if 1 and 2 are exhausted).

Idle agents **must not** start new features outside this spec. Out-of-scope work (§ 11) waits for a follow-up PR.

### 12.5 Coverage target — 80% on every new module

Modules listed in § 9.1 must each hit ≥80% line coverage before merge. Coverage measured via existing pytest-cov (backend) + jest --coverage (frontend) tooling. The Test agent owns hitting the bar; QA agent verifies via coverage report attached to PR.

### 12.6 Delegation discipline — who writes what

| Agent | Owns |
|---|---|
| **Backend** | `app/services/content_safety_service.py`, `app/data/content_blocklist.json`, `app/api/text_routes.py` widening, `app/services/structured_comparison_service.py` kwarg, `app/services/price_service.py` L2 filter, `app/api/image_routes.py` L4 vision moderation, `app/services/audit_service.py` helper |
| **Frontend** | `SmartCompareApp/src/components/TwoInputShell.tsx`, `PaywallBanner.tsx`, `src/utils/parseComparisonShape.ts`, `urlPasteDetect.ts`, `HomeScreen.tsx` rewiring, `ScanCameraScreen.tsx` celebration, `api.ts` dual-shape helper, i18n key adds/removes + `.copy-policy.json` update, `SearchOverlay.tsx` deletion |
| **Test** | `tests/test_content_safety_service.py`, `tests/test_two_input_shape.py`, `tests/test_security_regression.py` extensions, `TwoInputShell.test.tsx`, `PaywallBanner.test.tsx`, coverage report generation |
| **QA** | Cross-mode integration walkthrough, AR/RTL pass, copy audit, analytics event verification, freemium banner state walkthrough, content_safety end-to-end with seeded blocklist, regression that existing `query`-shape clients still work, manual checklist execution |

### 12.7 Path-restricted commits — avoid sweeping teammates' work

Per `MEMORY.md` `feedback_git_staging_in_team.md`: every commit uses `git commit -m "msg" -- <paths>` to scope to the agent's owned files. The `--` is a path separator; anything after it is paths and `-m` must come before. Failure to use this pattern bundles other agents' staged work into the wrong commit.

### 12.8 Disassembly criteria

Team disassembles **only when all of the following are true:**

1. Every file in § 9.1 + § 9.2 is committed.
2. Coverage report shows ≥80% on every new module.
3. Every backend regression test in § 5.3 + § 10 passes.
4. Every frontend component test in § 10 passes — including the negative-assertion test that shake never runs.
5. QA agent has signed off on the end-to-end walkthrough in writing (committed checklist in the PR description).
6. `MEMORY.md` Pending follow-ups updated with § 11 deferred items.
7. PR description includes: spec link, plan link, deferred items list, screenshots (EN + AR), coverage report summary.

If any criterion fails, the relevant work returns to its owner and the team stays assembled.

---

## 13. Open questions resolved during brainstorm

These were the decision points during the 2026-05-17 brainstorm session, captured for future reference:

| # | Question | Decision |
|---|---|---|
| 1 | Layout pattern (stacked / side-by-side / numbered) | **C — Stacked with numeral circles + connecting hairline + emerald vs pill** |
| 2 | Backend contract (concat / dual-shape / second endpoint) | **B — Dual-shape `model_validator` on existing `/text/compare`** |
| 2-side | Content moderation pipeline | **L1 query pre-filter + L2 image filter + L3 OpenAI moderation API + L4 vision moderation. Free. Graceful refusal copy.** |
| 3 | Paste-detection (split / mode-switch / both / neither) | **A — Both auto-split AND auto-mode-switch, with edge protections** |
| 4 | Keyboard ergonomics + celebration | **A — Auto-focus + chained returns + 3-part visual+haptic celebration (no shake, no sound)** |
| 5a | Validation timing (blur / keystroke / submit) | **A — On blur** |
| 5b | Paywall placement (banner / hint / current) | **A — Banner replaces boxes, with BonusCountdownCard + counter hidden during paywall takeover** |
| 6a | Analytics events | **8-event taxonomy approved as-is** |
| 6b | Counter placement | **A — Keep current bottom placement** |

---

**End of design specification.** Implementation plan to follow in `docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md`, produced by the 4-Opus team per § 12.
