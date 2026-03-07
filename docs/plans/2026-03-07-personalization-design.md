# Personalization Feature — Design Document

**Date:** March 7, 2026 (Session 19)
**Goal:** Personalize comparison results based on user preferences, collected once after first sign-in.

---

## 1. Overview

Add a one-time preference collection flow after first login/registration. Preferences are stored in Supabase and injected into the GPT comparison verdict prompt at zero extra API cost. The verdict changes from "best overall" to "best for YOU" with common-sense reasoning.

**Principles:**
- No false positives (don't recommend something that doesn't fit the user)
- No false negatives (don't miss a product that would be perfect for them)
- Zero extra API cost (preferences ride on existing GPT prompt tokens)
- One-time collection only — no per-comparison friction

---

## 2. User Flow

```
First Login/Register → preferences_completed=false detected
  → Navigate to PreferencesScreen (4 swipeable cards)
  → Card 1: Priority Weights (pick up to 3 chips)
  → Card 2: Budget Comfort (single level: budget/mid/premium)
  → Card 3: Lifestyle Tags (pick any that apply)
  → Card 4: Brand Attitude (single-select: brand_loyal/function_first/best_of_both)
  → ALL mandatory — no skip buttons, must answer all 4
  → Submit → POST /api/v1/auth/preferences → preferences_completed=true
  → Navigate to HomeScreen (never see preferences flow again)

Returning Login → preferences_completed=true → straight to HomeScreen
Edit Later → AccountScreen → "My Preferences" section → same UI
```

---

## 3. Preference Data Schema

### 3.1 Four Preference Dimensions (ALL mandatory — no skip buttons)

**Q1: Priority Weights** — "What matters most to you?"
Pick up to 3 from: `price`, `quality`, `brand_reputation`, `durability`, `latest_features`, `ease_of_use`, `eco_friendly`, `health_safety`

**Q2: Budget Comfort** — "How do you usually spend?"
Single general level that applies across all categories:
- `budget` — "I look for the best deals"
- `mid` — "I balance price and quality"
- `premium` — "I go for the best, price is secondary"

This is category-agnostic. The backend maps it contextually: "budget" for tech means <$300, for supplements means <$15. The mapping happens in the prompt, not in stored data.

**Q3: Lifestyle Tags** — "What describes you?"
Pick any: `gamer`, `photographer`, `fitness_enthusiast`, `vegan`, `sensitive_skin`, `parent`, `student`, `professional`, `outdoor_adventurer`, `minimalist`, `tech_enthusiast`

**Q4: Brand Attitude** — "When choosing products, what's your approach?"
Single-select:
- `brand_loyal` — "I stick with brands I trust"
- `function_first` — "I go with whatever works best, brand doesn't matter"
- `best_of_both` — "I prefer good brands, but functionality wins if the difference is clear"

### 3.2 Supabase Storage

Add `preferences` JSONB column to existing `public.users` table + `preferences_completed` boolean:

```sql
ALTER TABLE public.users
  ADD COLUMN preferences JSONB DEFAULT '{}',
  ADD COLUMN preferences_completed BOOLEAN DEFAULT false;
```

Example stored value:
```json
{
  "priorities": ["price", "durability", "health_safety"],
  "budget": "mid",
  "lifestyle": ["vegan", "fitness_enthusiast", "student"],
  "brand_attitude": "best_of_both"
}
```

---

## 4. Backend Changes

### 4.1 New API Endpoints

```
GET  /api/v1/auth/preferences        → returns current preferences (auth required)
PUT  /api/v1/auth/preferences        → saves/updates preferences (auth required)
```

Both use existing `get_current_user()` dependency.

### 4.2 Preference Injection into Verdict Prompt

In `extraction_service.py` → `generate_comparison()`:

Append to the existing comparison prompt (only when user_preferences is provided):

```
## User Preferences (personalize your verdict to this user)
- Top priorities: {priorities}
- Budget level: {budget} (interpret contextually for this product category)
- Lifestyle: {lifestyle_tags}
- Brand attitude: {brand_attitude}

Based on these preferences, your recommendation MUST:
1. Explain WHY this product is better FOR THIS USER (not generically)
2. Reference specific preferences ("You prioritize battery life, and Product A has 5000mAh vs 3349mAh")
3. Interpret budget contextually: "budget" for phones means <$300, for supplements means <$15
4. Flag if a product conflicts with lifestyle (e.g., non-vegan supplement for vegan user)
5. For brand_loyal users: weight established brand reputation higher
6. For function_first users: ignore brand entirely, focus on specs and value
7. For best_of_both users: prefer branded options when specs are similar, but recommend better-performing product even if lesser brand
```

### 4.3 Comparison Service Changes

In `structured_comparison_service.py` → `compare_from_text()`:
- Accept optional `user_preferences: dict` parameter
- Pass through to `generate_comparison()`

In `text_routes.py`:
- When user is authenticated, fetch preferences from user profile
- Pass to comparison service

### 4.4 Response Changes

Add to comparison response:
```json
{
  "personalized": true,
  "personalization_factors": ["budget_match", "lifestyle_vegan", "priority_price"]
}
```

When no preferences: `"personalized": false` (generic verdict, same as today).

---

## 5. Frontend Changes

### 5.1 New Screen: PreferencesScreen.tsx

A swipeable card-based screen with 4 steps + progress indicator.

**Components:**
- `PreferencesScreen.tsx` — main screen with step navigation
- Reuses existing chip/tag UI patterns from `CategorySelector.tsx`

**Navigation:**
- Added to `RootStackParamList` as `Preferences`
- App.tsx: after login success, check `preferences_completed` → route to Preferences or Home

### 5.2 App.tsx Flow Changes

```typescript
const handleLoginSuccess = async () => {
  setIsAuthenticated(true);
  // Check if preferences completed
  const user = await getSavedUser();
  if (!user?.preferences_completed) {
    setNeedsPreferences(true);  // show PreferencesScreen first
  }
};
```

Three-state navigator:
1. `isAuthenticated=false` → AuthNavigator
2. `isAuthenticated=true, needsPreferences=true` → PreferencesScreen
3. `isAuthenticated=true, needsPreferences=false` → MainNavigator

### 5.3 AccountScreen Addition

Add "My Preferences" section below existing profile fields:
- Shows current preferences as chips
- "Edit Preferences" button → navigates to PreferencesScreen in edit mode

### 5.4 ResultsScreen Changes

When `personalized: true` in response:
- Show subtle banner: "Personalized for you" with user icon
- Verdict text already includes personalized reasoning (from GPT)

---

## 6. Budget Contextual Interpretation

Budget is stored as a single value (`budget`/`mid`/`premium`). The GPT prompt interprets it contextually per product category. No mapping table needed — GPT understands that "budget" for phones means $200-300 and for vitamins means under $15. This is handled entirely in the prompt instruction:

> "Interpret the user's budget level contextually for the product category being compared."

---

## 7. What Stays the Same

- Anonymous users: no personalization, generic verdicts (unchanged)
- API cost: ~$0.010/comparison (50-100 extra tokens = ~$0.00002)
- Specs, prices, ratings, reviews: completely unchanged
- Existing comparison endpoint: backward compatible (preferences optional)
- All 4 preference cards are mandatory (no skip), so every authenticated user has a complete profile

---

## 8. Test Coverage Target: 80%+

### Unit Tests (free, no API calls)
- Preference validation (invalid priorities, empty preferences)
- Prompt injection with various preference combinations
- Category-to-budget mapping
- API endpoint request/response models
- Navigation flow (preferences_completed true/false)
- Edge cases: empty preferences, partial preferences, brand-only preferences

### Live Tests (optional, costs ~$0.02)
- Full comparison with vs without preferences → verify verdict changes
- Preferences persist across sessions

---

## 9. Files to Create/Modify

### Backend (create)
- None — all changes are additions to existing files

### Backend (modify)
- `app/api/auth_routes.py` — add GET/PUT /preferences endpoints + Pydantic models
- `app/services/auth_service.py` — add get_preferences(), save_preferences()
- `app/services/extraction_service.py` — modify generate_comparison() prompt
- `app/services/structured_comparison_service.py` — pass preferences through
- `app/api/text_routes.py` — fetch user preferences when authenticated

### Frontend (create)
- `SmartCompareApp/src/screens/PreferencesScreen.tsx` — 4-card preference flow

### Frontend (modify)
- `SmartCompareApp/src/types/types.ts` — add UserPreferences type, update User type, add Preferences to nav
- `SmartCompareApp/App.tsx` — three-state auth flow (auth → preferences → main)
- `SmartCompareApp/src/screens/AccountScreen.tsx` — "My Preferences" section
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — "Personalized for you" banner
- `SmartCompareApp/src/services/api.ts` — getPreferences(), savePreferences() API calls
- `SmartCompareApp/src/services/authService.ts` — include preferences_completed in saved user

### Database (migration)
- Add `preferences` JSONB + `preferences_completed` boolean to `public.users`

### Tests (create)
- `tests/test_personalization.py` — preference validation, prompt injection, API endpoints, edge cases

---

## 10. Team Structure (4 Opus Agents)

| Agent | Responsibilities |
|---|---|
| **backend-agent** | DB migration, auth endpoints, auth_service, prompt injection, comparison service changes |
| **frontend-agent** | PreferencesScreen, App.tsx flow, AccountScreen section, ResultsScreen banner, types, api.ts |
| **test-agent** | Write test_personalization.py (80%+ coverage), red-green TDD for all backend logic |
| **qa-agent** | Cross-QA all agents' work, verify integration, check for regressions, final approval |

### Cross-QA Protocol
- Each agent QAs another's work after completing their own tasks
- QA failures get sent back to the original agent
- Idle agents write tests until their QA comes back
- All 4 agents must sign off before team is dismissed
