# Category Selection Feature - Design Document

**Date:** 2026-03-05
**Author:** Design Session with User
**Status:** Approved for Implementation

---

## Overview

Add category selection to SmartCompare to guide users and improve AI accuracy. Users select a product category upfront (Electronics, Makeup, Skincare, etc.), which serves as a hint to the AI. The AI makes the final decision on which category schema to use, ensuring accurate comparisons even when users select the wrong category.

### Goals
- Guide users to think about product domains before comparing
- Improve AI accuracy by providing category context
- Use category-specific spec schemas for better comparisons
- Maintain zero additional API cost
- Keep implementation simple for upcoming Figma redesign

### Non-Goals
- Pre-submit validation or blocking (keep it simple)
- Real-time category detection (no extra API calls)
- Multi-category comparisons (out of scope)

---

## User Experience

### Flow: Category-First Selection

```
1. User opens HomeScreen
2. User selects category from dropdown (e.g., "Electronics")
3. User picks input method (Camera/Text/URL)
4. User enters their comparison
5. User submits
6. Backend AI detects actual category
7. Results displayed with category-specific specs
8. If category switched, show info banner:
   "ℹ️ We identified these as Makeup products for accurate comparison."
```

### The 7 Categories

**Existing:**
1. Electronics - phones, laptops, TVs, etc.
2. Grocery - food, beverages, household items
3. Supplements - vitamins, minerals, health supplements

**New (Beauty & Personal Care):**
4. Makeup - foundation, lipstick, mascara, eyeshadow
5. Skincare - moisturizers, serums, cleansers, sunscreen
6. Haircare - shampoos, conditioners, treatments, styling
7. Fragrances - perfumes, colognes, body sprays

### Validation Approach: Soft Guidance (Option B)

- Selected category is a **hint** for user guidance
- Backend AI always makes final category decision
- If mismatch detected (selected ≠ detected), backend uses **AI-detected category**
- User sees info banner after results load explaining the switch
- No blocking, no pre-submit warnings (keep it simple)

**Rationale:** Forcing electronics schema on lipstick would produce garbage results. Trust the AI to use the correct schema for accurate comparisons.

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────┐
│           Frontend (React Native)           │
│                                             │
│  HomeScreen:                                │
│  - Category Selector (dropdown, 7 options) │
│  - Input Method Tabs (Camera/Text/URL)     │
│  - Query Input                              │
│                                             │
│  ResultsScreen:                             │
│  - Category Switch Banner (if applicable)  │
│  - Comparison Results                       │
└──────────────────┬──────────────────────────┘
                   │ API Request
                   │ { q, region, selected_category }
                   ↓
┌─────────────────────────────────────────────┐
│         Backend (FastAPI + Python)          │
│                                             │
│  text_routes.py:                            │
│  - Accept selected_category param          │
│                                             │
│  structured_comparison_service.py:          │
│  - AI detects category (PRODUCT_PARSER)    │
│  - Track category_switched flag            │
│  - Use detected category for specs         │
│                                             │
│  extraction_service.py:                     │
│  - 4 new category schemas (makeup, etc.)   │
│  - Extract specs using category schema     │
└──────────────────┬──────────────────────────┘
                   │ API Response
                   │ { category_used, category_switched,
                   │   original_category, products, ... }
                   ↓
┌─────────────────────────────────────────────┐
│            Frontend Results Display         │
│                                             │
│  if category_switched:                      │
│    Show banner with explanation             │
└─────────────────────────────────────────────┘
```

### Design Principles
- **Simple**: No pre-submit validation, no extra API calls
- **Smart**: AI always uses correct category for best results
- **Transparent**: User sees when category was corrected
- **Flexible**: Minimal UI coupling, ready for Figma redesign
- **Zero Cost**: No additional API calls beyond existing flow

---

## Implementation Details

### Backend Changes

#### 1. New Category Schemas (`app/services/extraction_service.py`)

Add 4 new schemas to `CATEGORY_SPEC_SCHEMAS`:

```python
CATEGORY_SPEC_SCHEMAS = {
    # Existing
    "electronics": ["display", "processor", "ram", "storage", "battery",
                   "rear_camera", "front_camera", "os", "connectivity",
                   "weight", "water_resistance"],
    "grocery": ["count", "size", "ingredients", "nutrition_calories",
               "nutrition_protein", "nutrition_fat", "nutrition_carbs",
               "origin", "organic", "allergens", "shelf_life"],
    "supplements": ["count", "serving_size", "active_ingredient", "dosage",
                   "form", "allergens", "certifications", "origin",
                   "organic", "shelf_life", "nutrition_calories"],
    "other": ["count", "dimensions", "weight", "material", "color",
             "warranty", "power", "features", "included",
             "compatibility", "origin"],

    # NEW - Beauty & Personal Care
    "makeup": [
        "shade_range",      # e.g., "50 shades", "Light to Deep"
        "finish",           # matte, glossy, satin, dewy
        "coverage",         # sheer, medium, full
        "skin_type",        # oily, dry, combination, sensitive
        "ingredients",      # key ingredients list
        "cruelty_free",     # yes/no
        "vegan",           # yes/no
        "spf",             # sun protection factor
        "volume",          # ml/oz
        "waterproof",      # yes/no
        "long_lasting",    # hours or yes/no
    ],

    "skincare": [
        "skin_type",           # oily, dry, combination, sensitive
        "skin_concern",        # acne, aging, hydration, brightening
        "ingredients",         # key ingredients
        "active_ingredient",   # retinol, vitamin C, niacinamide, etc.
        "spf",                # sun protection factor
        "fragrance_free",     # yes/no
        "cruelty_free",       # yes/no
        "vegan",              # yes/no
        "volume",             # ml/oz
        "ph_level",           # pH balance
    ],

    "haircare": [
        "hair_type",        # straight, wavy, curly, coily
        "hair_concern",     # frizz, damage, volume, color-treated
        "ingredients",      # key ingredients
        "sulfate_free",     # yes/no
        "paraben_free",     # yes/no
        "silicone_free",    # yes/no
        "cruelty_free",     # yes/no
        "vegan",            # yes/no
        "volume",           # ml/oz
        "scent",            # fragrance description
    ],

    "fragrances": [
        "scent_family",     # floral, woody, oriental, fresh, etc.
        "notes_top",        # top notes (first impression)
        "notes_heart",      # heart/middle notes (main character)
        "notes_base",       # base notes (lasting impression)
        "longevity",        # hours of wear
        "sillage",          # projection (soft, moderate, strong)
        "season",           # spring, summer, fall, winter, all-season
        "occasion",         # day, evening, formal, casual
        "volume",           # ml/oz
        "concentration",    # eau de toilette, eau de parfum, parfum
    ],
}
```

#### 2. API Endpoint Changes (`app/api/text_routes.py`)

```python
@router.get("/compare")
async def compare_text(
    q: str,
    region: str = "bahrain",
    nocache: bool = False,
    selected_category: Optional[str] = None,  # NEW PARAMETER
    user: Optional[User] = Depends(get_optional_user)
):
    """
    Compare products via text query.

    Args:
        q: Product comparison query
        region: GCC region
        nocache: Bypass cache
        selected_category: User-selected category hint (optional)
        user: Authenticated user (optional)
    """
    result = await service.compare_from_text(
        query=q,
        region=region,
        nocache=nocache,
        selected_category=selected_category  # Pass to service
    )
    return result
```

#### 3. Service Logic (`app/services/structured_comparison_service.py`)

```python
async def compare_from_text(
    self,
    query: str,
    region: str = "bahrain",
    nocache: bool = False,
    selected_category: Optional[str] = None,  # NEW
    vision_products: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Main comparison orchestrator.

    Args:
        query: Text query
        region: GCC region
        nocache: Bypass cache
        selected_category: User-selected category (hint)
        vision_products: Pre-identified products from camera
    """
    # ... existing code ...

    # AI detects actual category (existing logic, unchanged)
    parsed = await parse_product_query(query, region)
    product_info = parsed["products"][0]  # First product
    detected_category = product_info.get("category", "other")

    # Track if category was switched
    category_switched = False
    original_category = None

    if selected_category and selected_category != detected_category:
        category_switched = True
        original_category = selected_category
        logger.info(f"Category switch: selected={selected_category}, detected={detected_category}")

    # ALWAYS use detected category (AI decision)
    category_to_use = detected_category

    # ... continue with category_to_use for specs extraction ...

    # Add to response
    return {
        "success": True,
        "query": query,
        "products": products_data,
        "verdict": verdict,
        "category_used": category_to_use,          # NEW
        "category_switched": category_switched,     # NEW
        "original_category": original_category,     # NEW (only if switched)
        # ... rest of response ...
    }
```

### Frontend Changes

#### 1. Category Selector Component (`SmartCompareApp/src/components/CategorySelector.tsx`)

Create new component:

```typescript
interface CategorySelectorProps {
  value: string | null;
  onChange: (category: string) => void;
}

const CATEGORIES = [
  { value: 'electronics', label: '📱 Electronics', icon: '📱' },
  { value: 'grocery', label: '🛒 Grocery', icon: '🛒' },
  { value: 'supplements', label: '💊 Supplements', icon: '💊' },
  { value: 'makeup', label: '💄 Makeup', icon: '💄' },
  { value: 'skincare', label: '✨ Skincare', icon: '✨' },
  { value: 'haircare', label: '💇 Haircare', icon: '💇' },
  { value: 'fragrances', label: '🌸 Fragrances', icon: '🌸' },
];

export default function CategorySelector({ value, onChange }: CategorySelectorProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>What are you comparing?</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {CATEGORIES.map(cat => (
          <TouchableOpacity
            key={cat.value}
            style={[styles.chip, value === cat.value && styles.chipActive]}
            onPress={() => onChange(cat.value)}
          >
            <Text style={styles.chipIcon}>{cat.icon}</Text>
            <Text style={[styles.chipText, value === cat.value && styles.chipTextActive]}>
              {cat.label.replace(/^.\s/, '')} {/* Remove emoji from label */}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}
```

#### 2. HomeScreen Integration (`SmartCompareApp/src/screens/HomeScreen.tsx`)

```typescript
export default function HomeScreen({ navigation, onLogout }: HomeScreenProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('electronics'); // Default

  // ... existing state ...

  const handleTextCompare = async () => {
    // ... validation ...

    const response = await api.get('/api/v1/text/compare', {
      params: {
        q: textQuery.trim(),
        region: 'bahrain',
        selected_category: selectedCategory,  // NEW
        ...(needsCacheBust && { nocache: true }),
      }
    });

    // ... rest of handler ...
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>...</View>

      {/* NEW: Category Selector */}
      <CategorySelector
        value={selectedCategory}
        onChange={setSelectedCategory}
      />

      {/* Input Method Tabs */}
      <View style={styles.methodSelector}>...</View>

      {/* Rest of screen */}
    </SafeAreaView>
  );
}
```

#### 3. Results Screen Banner (`SmartCompareApp/src/screens/ResultsScreen.tsx`)

```typescript
export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { result } = route.params;

  return (
    <SafeAreaView style={styles.container}>
      {/* NEW: Category Switch Banner */}
      {result.category_switched && (
        <View style={styles.infoBanner}>
          <Text style={styles.infoBannerIcon}>ℹ️</Text>
          <Text style={styles.infoBannerText}>
            We identified these as {result.category_used} products for accurate comparison.
          </Text>
        </View>
      )}

      {/* Rest of results display */}
      <TabView>...</TabView>
    </SafeAreaView>
  );
}
```

#### 4. Type Definitions (`SmartCompareApp/src/types/types.ts`)

```typescript
export interface ComparisonResponse {
  success: boolean;
  query: string;
  products: Product[];
  verdict: Verdict;
  category_used: string;           // NEW
  category_switched: boolean;       // NEW
  original_category?: string;       // NEW (optional)
  // ... existing fields ...
}
```

---

## Error Handling & Edge Cases

### Edge Case 1: Invalid Category Selection
- **Frontend:** Dropdown only allows valid categories
- **Backend:** Validate `selected_category`, fall back to `null` if invalid
- **Result:** AI auto-detects as normal

### Edge Case 2: No Clear Category Detected
- **Scenario:** AI can't confidently determine category
- **Behavior:** Default to `"other"` category
- **Result:** Generic specs used, no category_switched flag

### Edge Case 3: Multi-Category Queries
- **Scenario:** "iPhone vs lipstick" (electronics + makeup)
- **Behavior:** AI picks dominant category or defaults to "other"
- **Result:** Acceptable degradation (rare case)

### Edge Case 4: Camera Input
- **Scenario:** User selects "Makeup", takes photo of electronics
- **Behavior:** Vision AI identifies electronics, backend uses detected category
- **Result:** Category switch banner shown

### Edge Case 5: No Category Selected
- **Scenario:** User doesn't select category (null)
- **Behavior:** Backend AI auto-detects (existing behavior)
- **Result:** Works as today, no category_switched flag

### Error States
- **Missing category:** Default to `null`, AI auto-detects
- **Backend AI failure:** Graceful fallback to `"other"` category
- **Invalid schema:** Use `"other"` schema as fallback

---

## Testing Strategy

### Testing Requirements
- **Coverage Target:** 80% for new code
- **Team Structure:** Cross-QA between team members
- **Test-First:** Idle team members write red-green tests

### Backend Tests

**Unit Tests (`tests/test_category_selection.py`):**
```python
def test_new_category_schemas_exist():
    """Verify all 4 new schemas are defined"""
    assert "makeup" in CATEGORY_SPEC_SCHEMAS
    assert "skincare" in CATEGORY_SPEC_SCHEMAS
    assert "haircare" in CATEGORY_SPEC_SCHEMAS
    assert "fragrances" in CATEGORY_SPEC_SCHEMAS

def test_makeup_schema_fields():
    """Verify makeup schema has required fields"""
    makeup = CATEGORY_SPEC_SCHEMAS["makeup"]
    assert "shade_range" in makeup
    assert "finish" in makeup
    assert "coverage" in makeup
    assert len(makeup) >= 10  # At least 10 fields

def test_selected_category_param_accepted():
    """API accepts selected_category parameter"""
    response = client.get("/api/v1/text/compare?q=test&selected_category=electronics")
    assert response.status_code == 200

def test_category_switching_logic():
    """Backend detects and tracks category switches"""
    result = await service.compare_from_text(
        query="MAC lipstick vs Dior lipstick",
        selected_category="electronics"
    )
    assert result["category_used"] == "makeup"
    assert result["category_switched"] == True
    assert result["original_category"] == "electronics"

def test_no_switch_when_categories_match():
    """No switch flag when selected matches detected"""
    result = await service.compare_from_text(
        query="iPhone 15 vs Galaxy S24",
        selected_category="electronics"
    )
    assert result["category_used"] == "electronics"
    assert result["category_switched"] == False
    assert result.get("original_category") is None

def test_null_selected_category():
    """Handles null selected_category gracefully"""
    result = await service.compare_from_text(
        query="iPhone 15 vs Galaxy S24",
        selected_category=None
    )
    assert result["category_used"] == "electronics"
    assert result["category_switched"] == False
```

**Schema Extraction Tests:**
```python
@pytest.mark.live_unit
async def test_makeup_extraction():
    """Extract makeup specs using new schema"""
    specs = await extract_specs(
        brand="MAC",
        name="Ruby Woo Lipstick",
        variant="",
        category="makeup",
        search_context="MAC Ruby Woo lipstick matte finish"
    )
    assert "finish" in specs
    assert "shade_range" in specs or specs.get("finish") is not None

@pytest.mark.live_unit
async def test_skincare_extraction():
    """Extract skincare specs using new schema"""
    specs = await extract_specs(
        brand="CeraVe",
        name="Moisturizing Cream",
        variant="",
        category="skincare",
        search_context="CeraVe moisturizing cream for dry skin"
    )
    assert "skin_type" in specs or "skin_concern" in specs

@pytest.mark.live_unit
async def test_haircare_extraction():
    """Extract haircare specs using new schema"""
    specs = await extract_specs(
        brand="Olaplex",
        name="No. 3 Hair Perfector",
        variant="",
        category="haircare",
        search_context="Olaplex No. 3 treatment for damaged hair"
    )
    assert "hair_type" in specs or "hair_concern" in specs

@pytest.mark.live_unit
async def test_fragrance_extraction():
    """Extract fragrance specs using new schema"""
    specs = await extract_specs(
        brand="Chanel",
        name="No. 5",
        variant="Eau de Parfum",
        category="fragrances",
        search_context="Chanel No. 5 floral aldehyde perfume"
    )
    assert "scent_family" in specs or "notes_top" in specs
```

### Frontend Tests

**Component Tests:**
```typescript
describe('CategorySelector', () => {
  it('renders all 7 categories', () => {
    const { getByText } = render(<CategorySelector value={null} onChange={jest.fn()} />);
    expect(getByText('Electronics')).toBeTruthy();
    expect(getByText('Makeup')).toBeTruthy();
    expect(getByText('Skincare')).toBeTruthy();
    expect(getByText('Haircare')).toBeTruthy();
    expect(getByText('Fragrances')).toBeTruthy();
  });

  it('calls onChange when category selected', () => {
    const onChange = jest.fn();
    const { getByText } = render(<CategorySelector value={null} onChange={onChange} />);
    fireEvent.press(getByText('Makeup'));
    expect(onChange).toHaveBeenCalledWith('makeup');
  });
});

describe('HomeScreen', () => {
  it('passes selected_category in API request', async () => {
    const { getByText, getByPlaceholderText } = render(<HomeScreen />);

    // Select category
    fireEvent.press(getByText('Makeup'));

    // Enter query
    fireEvent.changeText(getByPlaceholderText(/iPhone/), 'MAC lipstick vs Dior lipstick');

    // Submit
    fireEvent.press(getByText('Compare'));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/api/v1/text/compare', {
        params: expect.objectContaining({
          selected_category: 'makeup'
        })
      });
    });
  });
});

describe('ResultsScreen', () => {
  it('shows banner when category switched', () => {
    const result = {
      category_switched: true,
      category_used: 'makeup',
      original_category: 'electronics',
      // ... rest of data
    };

    const { getByText } = render(<ResultsScreen route={{ params: { result } }} />);
    expect(getByText(/We identified these as makeup products/i)).toBeTruthy();
  });

  it('hides banner when categories match', () => {
    const result = {
      category_switched: false,
      category_used: 'electronics',
      // ... rest of data
    };

    const { queryByText } = render(<ResultsScreen route={{ params: { result } }} />);
    expect(queryByText(/We identified/i)).toBeNull();
  });
});
```

### Integration Tests

**End-to-End Tests (`tests/test_integration.py`):**
```python
@pytest.mark.integration
async def test_category_selection_electronics_match():
    """E2E: Select electronics, query electronics, verify no switch"""
    response = client.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={
            "q": "iPhone 15 vs Galaxy S24",
            "region": "bahrain",
            "selected_category": "electronics",
            "nocache": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category_used"] == "electronics"
    assert data["category_switched"] == False

@pytest.mark.integration
async def test_category_selection_mismatch():
    """E2E: Select electronics, query makeup, verify switch to makeup"""
    response = client.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={
            "q": "MAC Ruby Woo vs Dior 999 lipstick",
            "region": "bahrain",
            "selected_category": "electronics",
            "nocache": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category_used"] == "makeup"
    assert data["category_switched"] == True
    assert data["original_category"] == "electronics"

    # Verify makeup specs were extracted
    product = data["products"][0]
    assert "finish" in product["specs"] or "shade_range" in product["specs"]

@pytest.mark.integration
async def test_all_new_categories():
    """E2E: Test all 4 new categories with matching queries"""
    test_cases = [
        ("makeup", "MAC lipstick vs Dior lipstick"),
        ("skincare", "CeraVe moisturizer vs Cetaphil lotion"),
        ("haircare", "Olaplex No. 3 vs K18 treatment"),
        ("fragrances", "Chanel No. 5 vs Dior Sauvage"),
    ]

    for category, query in test_cases:
        response = client.get(
            f"{BASE_URL}/api/v1/text/compare",
            params={
                "q": query,
                "region": "bahrain",
                "selected_category": category,
                "nocache": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category_used"] == category
        assert data["category_switched"] == False
```

### Red-Green Test Writing (for idle team members)

Team members waiting for QA can write tests following TDD:

1. **Red:** Write failing test for new feature
2. **Green:** Implement feature to pass test
3. **Refactor:** Clean up code while keeping tests green

Example workflow:
```python
# RED: Test fails (feature not implemented)
def test_fragrances_schema_has_concentration_field():
    assert "concentration" in CATEGORY_SPEC_SCHEMAS["fragrances"]
# FAIL: KeyError 'fragrances'

# GREEN: Add schema to make test pass
CATEGORY_SPEC_SCHEMAS["fragrances"] = [
    "concentration",
    # ... other fields
]
# PASS

# REFACTOR: Complete the schema with all fields
CATEGORY_SPEC_SCHEMAS["fragrances"] = [
    "scent_family", "notes_top", "notes_heart", "notes_base",
    "longevity", "sillage", "season", "occasion", "volume", "concentration"
]
# PASS (still green)
```

---

## Team Implementation Requirements

### Team Structure
- **Agent Type:** Opus (not Sonnet or Haiku)
- **Team Size:** 3-4 agents
- **Roles:** Frontend, Backend, Test/QA, Integration

### Quality Gates
1. **Feature Completeness:** 100% of design implemented before team disbands
2. **Cross-QA:** Each member must QA another member's work
3. **Subpar Work:** If QA finds issues, send work back for revision
4. **Idle Work:** Write red-green tests to achieve 80% coverage
5. **No Shortcuts:** All validation must pass before completion

### Work Delegation
- **Backend Agent:** Implement new schemas, API changes, service logic, backend tests
- **Frontend Agent:** Implement category selector, HomeScreen changes, ResultsScreen banner, frontend tests
- **Test/QA Agent:** Write integration tests, perform cross-QA, ensure 80% coverage
- **Integration Agent:** End-to-end testing, deploy verification, documentation updates

### QA Checklist
- [ ] All 4 new category schemas defined with correct fields
- [ ] API endpoint accepts `selected_category` parameter
- [ ] Service logic tracks category switching correctly
- [ ] Response includes `category_used`, `category_switched`, `original_category`
- [ ] Frontend category selector renders all 7 categories
- [ ] Selected category passed to API in all input methods (text, camera, URL)
- [ ] Category switch banner shown correctly on ResultsScreen
- [ ] Type definitions updated to match API response
- [ ] Backend tests pass (unit + live_unit)
- [ ] Frontend tests pass (component + integration)
- [ ] Integration tests pass against Railway production
- [ ] 80% code coverage achieved for new code
- [ ] No regressions in existing features
- [ ] Documentation updated (CLAUDE.md, MEMORY.md)

---

## Success Metrics

### Implementation Success
- All 7 categories selectable in UI
- Category switching works correctly (AI overrides when needed)
- 80% test coverage for new code
- Zero cost increase (no extra API calls)
- No regressions in existing features

### User Experience Success
- Users understand category selection purpose
- Category switch banner is clear and non-intrusive
- Comparison quality improves for beauty products
- No increase in error rates

### Future Expansion
- Design is flexible for Figma UI redesign
- Easy to add new categories (just add schema + update dropdown)
- Can upgrade to real-time validation if needed (Approach 2)
- Foundation for category-based personalization

---

## Future Considerations

### Phase 2 Enhancements (Post-Launch)
1. **Category Analytics:** Track which categories are most used
2. **Smart Defaults:** Remember user's last selected category
3. **Category Suggestions:** "Looking for makeup? Try the Makeup category"
4. **Expanded Schemas:** Add more specific categories (e.g., split Makeup into Face/Eyes/Lips)
5. **Regional Customization:** Different popular categories per GCC region

### Figma Redesign Compatibility
- Current implementation uses simple dropdown/chips
- Easy to swap with custom Figma designs
- Category state management is clean and reusable
- Banner styling can be fully customized

### Multi-Category Support (Future)
- Out of scope for v1
- Would require: category per product, mixed schema handling
- Example: "iPhone vs lipstick" → show both electronics + makeup specs

---

## Appendix

### Related Documentation
- `CLAUDE.md` - Project instructions
- `docs/CONTEXT_ARCHITECTURE.md` - System architecture
- `docs/CONTEXT_SESSION_LOG.md` - Development history
- `app/services/extraction_service.py` - Current category schemas

### API Contract Changes

**Request:**
```json
GET /api/v1/text/compare?q=query&region=bahrain&selected_category=makeup
```

**Response:**
```json
{
  "success": true,
  "query": "MAC lipstick vs Dior lipstick",
  "category_used": "makeup",
  "category_switched": false,
  "original_category": null,
  "products": [
    {
      "name": "MAC Ruby Woo",
      "specs": {
        "shade_range": "Red",
        "finish": "Matte",
        "coverage": "Full",
        // ... makeup-specific specs
      }
    }
  ],
  "verdict": "...",
  // ... rest of response
}
```

**Response with Category Switch:**
```json
{
  "success": true,
  "query": "MAC lipstick vs Dior lipstick",
  "category_used": "makeup",
  "category_switched": true,
  "original_category": "electronics",
  "products": [...],
  "verdict": "..."
}
```

---

**End of Design Document**
