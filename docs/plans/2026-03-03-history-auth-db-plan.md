# History, Auth & Database Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the broken history feature by wiring up auth, saving full comparison responses, updating the DB schema, and adding search_logs + product dedup.

**Architecture:** 3-agent team (Auth, History, DB) working in parallel with circular cross-QA. Auth agent fixes the JWT pipeline end-to-end. History agent wires up save/load with full JSONB blobs. DB agent updates schema, adds search_logs and product dedup. Each agent QAs one other's work before team disbands.

**Tech Stack:** FastAPI (Python 3.12), Supabase (PostgreSQL), React Native (Expo), Axios, AsyncStorage

**Team execution:** All agents are Opus. Use `bypassPermissions` mode. QA circle: Auth→History, History→DB, DB→Auth.

---

## Agent 1: Auth Agent

### Task 1: Add axios request interceptor to attach JWT

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts:13-16`

**Step 1: Write the interceptor code**

Add after the `api` instance creation (after line 16):

```typescript
// Auth interceptor — attach JWT to every request
api.interceptors.request.use(
  async (config) => {
    // Import here to avoid circular dependency
    const { getToken } = require('./authService');
    const token = await getToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);
```

**Step 2: Verify no TypeScript errors**

Run: `cd SmartCompareApp && npx tsc --noEmit 2>&1 | findstr "api.ts"`
Expected: No new errors in api.ts (pre-existing errors in other files are OK)

**Step 3: Commit**

```bash
git add SmartCompareApp/src/services/api.ts
git commit -m "feat(auth): add axios request interceptor for JWT"
```

### Task 2: Add axios response interceptor for 401 token refresh

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts`

**Step 1: Add response interceptor after the request interceptor**

```typescript
// Response interceptor — auto-refresh on 401
let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (token) prom.resolve(token);
    else prom.reject(error);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only retry once, and only for 401s
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Skip refresh for auth endpoints themselves
    if (originalRequest.url?.includes('/auth/')) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const { refreshSession, getToken } = require('./authService');
      await refreshSession();
      const newToken = await getToken();
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        processQueue(null, newToken);
        return api(originalRequest);
      }
      processQueue(new Error('No token after refresh'));
      return Promise.reject(error);
    } catch (refreshError) {
      const { clearSession } = require('./authService');
      await clearSession();
      processQueue(refreshError);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
```

**Step 2: Verify no TypeScript errors**

Run: `cd SmartCompareApp && npx tsc --noEmit 2>&1 | findstr "api.ts"`
Expected: No new errors

**Step 3: Commit**

```bash
git add SmartCompareApp/src/services/api.ts
git commit -m "feat(auth): add 401 response interceptor with token refresh"
```

### Task 3: Add optional auth to text comparison endpoints

**Files:**
- Modify: `app/api/text_routes.py:4-6` (imports)
- Modify: `app/api/text_routes.py:44-79` (POST /compare)
- Modify: `app/api/text_routes.py:82-109` (GET /compare)

**Step 1: Add imports**

At top of `text_routes.py`, update imports:

```python
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict

from app.api.auth_routes import get_optional_user
```

**Step 2: Add `user` dependency to POST endpoint**

Change line 45 from:
```python
async def text_compare(request: TextCompareRequest):
```
to:
```python
async def text_compare(request: TextCompareRequest, user: Optional[Dict] = Depends(get_optional_user)):
```

**Step 3: Add `user` dependency to GET endpoint**

Change the GET function signature to add user param:
```python
async def text_compare_get(
    q: str = Query(..., description="Comparison query, e.g., 'iPhone 15 vs S24'"),
    region: str = Query("bahrain", description="GCC region for pricing"),
    specs: bool = Query(True, description="Include specifications"),
    reviews: bool = Query(True, description="Include reviews"),
    pros_cons: bool = Query(True, description="Include pros/cons"),
    nocache: bool = Query(False, description="Bypass cache for fresh data"),
    user: Optional[Dict] = Depends(get_optional_user),
):
```

**Step 4: Syntax check**

Run: `python -m py_compile app/api/text_routes.py`
Expected: No output (success)

**Step 5: Commit**

```bash
git add app/api/text_routes.py
git commit -m "feat(auth): add optional auth dependency to text comparison endpoints"
```

### Task 4: Add optional auth to image endpoint

**Files:**
- Modify: `app/api/image_routes.py:14` (imports)
- Modify: `app/api/image_routes.py:28-30` (endpoint signature)

**Step 1: Add imports**

Add to imports:
```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from typing import List, Optional, Dict

from app.api.auth_routes import get_optional_user
```

**Step 2: Add `user` param to endpoint**

Add `user: Optional[Dict] = Depends(get_optional_user)` to the `identify_and_compare` function signature.

**Step 3: Syntax check**

Run: `python -m py_compile app/api/image_routes.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add app/api/image_routes.py
git commit -m "feat(auth): add optional auth dependency to image endpoint"
```

### Task 5: Write auth unit tests

**Files:**
- Create: `tests/test_auth_interceptor.py`

**Step 1: Write tests**

```python
"""Tests for auth pipeline — optional user dependency and token handling."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── get_optional_user tests ──

@pytest.mark.asyncio
async def test_optional_user_returns_none_when_no_header():
    """get_optional_user returns None when no Authorization header."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization=None)
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_bad_format():
    """get_optional_user returns None for malformed header."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="NotBearer abc123")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_missing_token():
    """get_optional_user returns None when just 'Bearer' with no token."""
    from app.api.auth_routes import get_optional_user
    result = await get_optional_user(authorization="Bearer")
    assert result is None


@pytest.mark.asyncio
async def test_optional_user_returns_user_on_valid_token():
    """get_optional_user returns user dict when token is valid."""
    from app.api.auth_routes import get_optional_user
    mock_user = {"id": "user-123", "email": "test@example.com"}
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, return_value=mock_user):
        result = await get_optional_user(authorization="Bearer valid-token-123")
    assert result == mock_user


@pytest.mark.asyncio
async def test_optional_user_returns_none_on_expired_token():
    """get_optional_user returns None when verify_token raises."""
    from app.api.auth_routes import get_optional_user
    with patch("app.api.auth_routes.verify_token", new_callable=AsyncMock, side_effect=Exception("Token expired")):
        result = await get_optional_user(authorization="Bearer expired-token")
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_no_header():
    """get_current_user raises 401 when no auth header (unlike optional)."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_bad_format():
    """get_current_user raises 401 for malformed header."""
    from app.api.auth_routes import get_current_user
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization="Basic abc123")
    assert exc_info.value.status_code == 401
```

**Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_interceptor.py -v`
Expected: 7 passed

**Step 3: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test(auth): add 7 unit tests for auth dependency functions"
```

---

## Agent 2: History Agent

### Task 6: Update save_comparison() to accept full response blob

**Files:**
- Modify: `app/services/database_service.py:91-134`

**Step 1: Rewrite save_comparison()**

Replace the existing `save_comparison()` function (lines 91-134) with:

```python
async def save_comparison(
    full_response: Dict,
    query: str,
    input_type: str = "text",
    user_id: Optional[str] = None,
) -> Optional[Dict]:
    """
    Save a comparison to the database.

    Args:
        full_response: The entire API response dict (products, comparison, metadata, etc.)
        query: Original search query
        input_type: "text" or "camera"
        user_id: Authenticated user's ID, or None for anonymous

    Returns:
        Saved comparison record or None on failure
    """
    try:
        client = get_supabase_client()

        # Extract product names for indexing
        products = full_response.get("products", [])
        product_names = []
        for p in products:
            name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
            if name:
                product_names.append(name)

        record = {
            "full_response": full_response,
            "query": query,
            "input_type": input_type,
            "product_names": product_names,
        }

        if user_id:
            record["user_id"] = user_id

        response = client.table("comparisons").insert(record).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        # Fire-and-forget — never break the comparison response
        print(f"Error saving comparison: {e}")
        return None
```

**Step 2: Syntax check**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add app/services/database_service.py
git commit -m "feat(history): rewrite save_comparison() for full JSONB blob storage"
```

### Task 7: Update get_user_comparisons() for new schema

**Files:**
- Modify: `app/services/database_service.py:137-156`

**Step 1: Rewrite get_user_comparisons()**

Replace lines 137-156:

```python
async def get_user_comparisons(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
) -> List[Dict]:
    """Get user's comparison history, optionally filtered by product name search."""
    try:
        client = get_supabase_client()
        query = (
            client.table("comparisons")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )

        if search:
            query = query.ilike("query", f"%{search}%")

        response = query.range(offset, offset + limit - 1).execute()
        return response.data or []
    except Exception as e:
        print(f"Error getting comparisons: {e}")
        return []
```

**Step 2: Syntax check**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output

**Step 3: Commit**

```bash
git add app/services/database_service.py
git commit -m "feat(history): update get_user_comparisons() with search support"
```

### Task 8: Add delete_comparison() function

**Files:**
- Modify: `app/services/database_service.py` (add after get_comparison_by_id)

**Step 1: Add function**

Add after the `get_comparison_by_id()` function:

```python
async def delete_comparison(comparison_id: str, user_id: str) -> bool:
    """Delete a comparison (only if owned by user)."""
    try:
        client = get_supabase_client()
        response = (
            client.table("comparisons")
            .delete()
            .eq("id", comparison_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        print(f"Error deleting comparison: {e}")
        return False
```

**Step 2: Syntax check**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output

**Step 3: Commit**

```bash
git add app/services/database_service.py
git commit -m "feat(history): add delete_comparison() with user ownership check"
```

### Task 9: Wire save_comparison into text_routes.py

**Files:**
- Modify: `app/api/text_routes.py:65-79` (POST)
- Modify: `app/api/text_routes.py:94-109` (GET)

**Step 1: Add import**

Add to imports at top of text_routes.py:
```python
import asyncio
from app.services.database_service import save_comparison
```

**Step 2: Add save call to POST endpoint**

Replace the return block (around line 73-79) with:

```python
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    # Fire-and-forget: save to history if user is authenticated
    if user and user.get("id"):
        asyncio.create_task(save_comparison(
            full_response=result,
            query=request.query,
            input_type="text",
            user_id=user["id"],
        ))

    return result
```

**Step 3: Add save call to GET endpoint**

Replace the return block (around line 103-109) with:

```python
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Comparison failed")
        )

    # Fire-and-forget: save to history if user is authenticated
    if user and user.get("id"):
        asyncio.create_task(save_comparison(
            full_response=result,
            query=q,
            input_type="text",
            user_id=user["id"],
        ))

    return result
```

**Step 4: Syntax check**

Run: `python -m py_compile app/api/text_routes.py`
Expected: No output

**Step 5: Commit**

```bash
git add app/api/text_routes.py
git commit -m "feat(history): save text comparisons to database (fire-and-forget)"
```

### Task 10: Wire save_comparison into image_routes.py

**Files:**
- Modify: `app/api/image_routes.py:148-149` (success return point)

**Step 1: Add imports at top**

```python
import asyncio
from app.services.database_service import save_comparison
```

**Step 2: Add save call before success return**

Before `return result` at line 149, add:

```python
        # Fire-and-forget: save to history if user is authenticated
        if user and user.get("id"):
            asyncio.create_task(save_comparison(
                full_response=result,
                query=query,
                input_type="camera",
                user_id=user["id"],
            ))
```

Note: `query` variable is already defined earlier in the function (around line 128, constructed from product names).

**Step 3: Syntax check**

Run: `python -m py_compile app/api/image_routes.py`
Expected: No output

**Step 4: Commit**

```bash
git add app/api/image_routes.py
git commit -m "feat(history): save camera comparisons to database (fire-and-forget)"
```

### Task 11: Update history endpoint to use real auth

**Files:**
- Modify: `app/api/routes.py:346-363`

**Step 1: Add import**

At top of routes.py, add:
```python
from app.api.auth_routes import get_current_user
from app.services.database_service import delete_comparison
```

**Step 2: Rewrite history endpoint**

Replace lines 346-363 with:

```python
@router.get("/comparisons/history")
async def comparison_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by product name or query"),
    user: dict = Depends(get_current_user),
):
    """Get comparison history for authenticated user."""
    user_id = user["id"]

    comparisons = await get_user_comparisons(user_id, limit, offset, search=search)
    total = await get_user_comparison_count(user_id)

    return {
        "comparisons": comparisons,
        "total": total,
        "page": (offset // limit) + 1,
        "per_page": limit,
    }
```

**Step 3: Add delete endpoint**

Add after the history endpoint:

```python
@router.delete("/comparisons/{comparison_id}")
async def delete_comparison_endpoint(
    comparison_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a comparison from history (only own comparisons)."""
    deleted = await delete_comparison(comparison_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return {"success": True, "deleted_id": comparison_id}
```

**Step 4: Update imports at top of routes.py**

Ensure `Depends` is imported from fastapi. Check existing imports and add if missing.

**Step 5: Syntax check**

Run: `python -m py_compile app/api/routes.py`
Expected: No output

**Step 6: Commit**

```bash
git add app/api/routes.py
git commit -m "feat(history): update history endpoint to use real auth, add delete endpoint"
```

### Task 12: Add frontend API functions for delete and search

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts:198-203`

**Step 1: Update getComparisonHistory to support search**

Replace lines 198-203:

```typescript
export async function getComparisonHistory(limit: number = 20, offset: number = 0, search?: string) {
  const response = await api.get('/api/v1/comparisons/history', {
    params: { limit, offset, ...(search ? { search } : {}) },
  });
  return response.data;
}
```

**Step 2: Add deleteComparison function**

Add after `getComparisonHistory`:

```typescript
export async function deleteComparison(comparisonId: string) {
  const response = await api.delete(`/api/v1/comparisons/${comparisonId}`);
  return response.data;
}
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/services/api.ts
git commit -m "feat(history): add search param and delete function to API service"
```

### Task 13: Update HistoryScreen — full blob passthrough + search + delete

**Files:**
- Modify: `SmartCompareApp/src/screens/HistoryScreen.tsx`

**Step 1: Update HistoryItem interface (lines 29-38)**

Replace with:

```typescript
interface HistoryItem {
  id: string;
  full_response: any;  // Complete API response blob
  query: string;
  input_type: string;
  product_names: string[];
  created_at: string;
}
```

**Step 2: Update imports (line 23)**

```typescript
import { getComparisonHistory, deleteComparison } from '../services/api';
```

**Step 3: Add search state after existing state vars (around line 44)**

```typescript
  const [searchQuery, setSearchQuery] = useState('');
```

**Step 4: Update loadHistory to pass search param**

```typescript
  const loadHistory = async () => {
    try {
      const data = await getComparisonHistory(50, 0, searchQuery || undefined);
      setHistory(data.comparisons || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error loading history:', error);
      // Don't show alert for auth errors — user may not be logged in
      if ((error as any)?.response?.status !== 401) {
        Alert.alert('Error', 'Failed to load history');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
```

**Step 5: Rewrite viewAsResult for full blob passthrough (lines 112-137)**

Replace with:

```typescript
  const viewAsResult = (item: HistoryItem) => {
    setModalVisible(false);
    // Pass the full stored blob directly — same shape as live response
    navigation.navigate('Results', {
      result: item.full_response,
    });
  };
```

**Step 6: Update renderItem to extract products from full_response**

Update `renderItem` to read from `item.full_response.products` instead of `item.products`:

```typescript
  const renderItem = ({ item }: { item: HistoryItem }) => {
    const products = item.full_response?.products || [];
    const winner_index = item.full_response?.comparison?.winner_index ?? item.full_response?.winner_index ?? 0;
    const winner = products[winner_index];

    return (
      <TouchableOpacity style={styles.historyCard} onPress={() => openDetails(item)}>
        <View style={styles.cardHeader}>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
          <View style={[
            styles.sourceBadge,
            { backgroundColor: item.input_type === 'camera' ? '#5856D6' : '#34C759' }
          ]}>
            <Text style={styles.sourceBadgeText}>{item.input_type || 'text'}</Text>
          </View>
        </View>

        <View style={styles.vsContainer}>
          <View style={styles.productSummary}>
            <Text style={styles.productLabel}>Product 1</Text>
            <Text style={styles.productSummaryName} numberOfLines={1}>
              {products[0]?.brand} {products[0]?.name}
            </Text>
            <Text style={styles.productSummaryPrice}>{formatPrice(products[0])}</Text>
          </View>

          <Text style={styles.vsText}>VS</Text>

          <View style={styles.productSummary}>
            <Text style={styles.productLabel}>Product 2</Text>
            <Text style={styles.productSummaryName} numberOfLines={1}>
              {products[1]?.brand} {products[1]?.name}
            </Text>
            <Text style={styles.productSummaryPrice}>{formatPrice(products[1])}</Text>
          </View>
        </View>

        {winner && (
          <View style={styles.winnerRow}>
            <Text style={styles.winnerEmoji}>🏆</Text>
            <Text style={styles.winnerName} numberOfLines={1}>
              {winner?.brand} {winner?.name}
            </Text>
            <Text style={styles.winnerPrice}>{formatPrice(winner)}</Text>
          </View>
        )}

        <View style={styles.tapHint}>
          <Text style={styles.tapHintText}>Tap to view details →</Text>
        </View>
      </TouchableOpacity>
    );
  };
```

**Step 7: Update modal to use full_response data**

Update `renderModal` — replace references to `selectedItem.products`, `selectedItem.winner_index`, `selectedItem.recommendation`, `selectedItem.key_differences` with:

```typescript
const products = selectedItem.full_response?.products || [];
const comparison = selectedItem.full_response?.comparison || {};
const winner_index = comparison.winner_index ?? 0;
const recommendation = comparison.recommendation || '';
const key_differences = comparison.key_differences || [];
```

Declare these variables right after `{selectedItem && (` and use them throughout the modal.

**Step 8: Add delete handler**

```typescript
  const handleDelete = async (item: HistoryItem) => {
    Alert.alert(
      'Delete Comparison',
      'Are you sure you want to delete this comparison?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteComparison(item.id);
              setHistory((prev) => prev.filter((h) => h.id !== item.id));
              setTotal((prev) => prev - 1);
              setModalVisible(false);
            } catch (error) {
              Alert.alert('Error', 'Failed to delete comparison');
            }
          },
        },
      ]
    );
  };
```

**Step 9: Add delete button to modal actions**

In the modal actions section, add a delete button between "View Full Results" and "Close":

```tsx
<TouchableOpacity
  style={[styles.modalActionButton, { backgroundColor: '#FF3B30' }]}
  onPress={() => handleDelete(selectedItem)}
>
  <Text style={styles.modalActionText}>🗑 Delete</Text>
</TouchableOpacity>
```

**Step 10: Add search bar to the header area**

Add a `TextInput` between the header and FlatList:

```tsx
import { TextInput } from 'react-native';
```

In the return JSX, after the header `<View>` and before `<FlatList>`:

```tsx
<View style={styles.searchContainer}>
  <TextInput
    style={styles.searchInput}
    placeholder="Search comparisons..."
    placeholderTextColor="#999"
    value={searchQuery}
    onChangeText={setSearchQuery}
    onSubmitEditing={() => { setLoading(true); loadHistory(); }}
    returnKeyType="search"
  />
</View>
```

Add styles:
```typescript
searchContainer: {
  paddingHorizontal: 16,
  paddingVertical: 8,
  backgroundColor: '#FFF',
},
searchInput: {
  backgroundColor: '#F0F0F0',
  borderRadius: 8,
  paddingHorizontal: 12,
  paddingVertical: 8,
  fontSize: 14,
  color: '#333',
},
```

**Step 11: Commit**

```bash
git add SmartCompareApp/src/screens/HistoryScreen.tsx
git commit -m "feat(history): full blob passthrough, search, delete, updated UI"
```

### Task 14: Write history unit tests

**Files:**
- Create: `tests/test_history.py`

**Step 1: Write tests**

```python
"""Tests for history save/load/delete pipeline."""
import pytest
from unittest.mock import patch, MagicMock


MOCK_FULL_RESPONSE = {
    "success": True,
    "products": [
        {"brand": "Apple", "name": "iPhone 15", "price": {"amount": 299.0, "currency": "BHD"}},
        {"brand": "Samsung", "name": "Galaxy S24", "price": {"amount": 269.0, "currency": "BHD"}},
    ],
    "comparison": {
        "winner_index": 0,
        "recommendation": "iPhone 15 wins",
        "key_differences": ["Better camera", "Higher price"],
    },
    "metadata": {"query": "iphone 15 vs galaxy s24", "total_cost": 0.01},
}


@pytest.mark.asyncio
async def test_save_comparison_extracts_product_names():
    """save_comparison extracts product_names from full_response."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-123"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = await save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="iphone 15 vs galaxy s24",
            input_type="text",
            user_id="user-123",
        )

    assert result == {"id": "abc-123"}
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["product_names"] == ["Apple iPhone 15", "Samsung Galaxy S24"]
    assert insert_arg["query"] == "iphone 15 vs galaxy s24"
    assert insert_arg["input_type"] == "text"
    assert insert_arg["user_id"] == "user-123"
    assert insert_arg["full_response"] == MOCK_FULL_RESPONSE


@pytest.mark.asyncio
async def test_save_comparison_no_user_id():
    """save_comparison omits user_id when None (anonymous)."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-456"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = await save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="test query",
        )

    insert_arg = mock_table.insert.call_args[0][0]
    assert "user_id" not in insert_arg


@pytest.mark.asyncio
async def test_save_comparison_returns_none_on_error():
    """save_comparison returns None on error (fire-and-forget)."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB down")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = await save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="test",
            user_id="user-123",
        )

    assert result is None


@pytest.mark.asyncio
async def test_save_comparison_handles_empty_products():
    """save_comparison handles response with no products gracefully."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-789"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = await save_comparison(full_response={"success": True}, query="test")

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["product_names"] == []


@pytest.mark.asyncio
async def test_get_user_comparisons_with_search():
    """get_user_comparisons filters by search term."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import get_user_comparisons
        result = await get_user_comparisons("user-123", search="iphone")

    mock_query.ilike.assert_called_once_with("query", "%iphone%")
    assert result == [{"id": "1"}]


@pytest.mark.asyncio
async def test_get_user_comparisons_without_search():
    """get_user_comparisons skips ilike when no search term."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import get_user_comparisons
        result = await get_user_comparisons("user-123")

    mock_query.ilike.assert_not_called()


@pytest.mark.asyncio
async def test_delete_comparison_own():
    """delete_comparison succeeds for own comparison."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "comp-1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = await delete_comparison("comp-1", "user-123")

    assert result is True


@pytest.mark.asyncio
async def test_delete_comparison_not_found():
    """delete_comparison returns False when comparison not found or not owned."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = await delete_comparison("comp-999", "user-123")

    assert result is False


@pytest.mark.asyncio
async def test_delete_comparison_handles_error():
    """delete_comparison returns False on DB error."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB error")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = await delete_comparison("comp-1", "user-123")

    assert result is False
```

**Step 2: Run tests**

Run: `python -m pytest tests/test_history.py -v`
Expected: 10 passed

**Step 3: Commit**

```bash
git add tests/test_history.py
git commit -m "test(history): add 10 unit tests for save/load/delete pipeline"
```

---

## Agent 3: DB Agent

### Task 15: Create SQL migration for comparisons table update

**Files:**
- Create: `migrations/001_update_comparisons.sql`

**Step 1: Write migration**

```sql
-- Migration: Update comparisons table for full JSONB blob storage
-- Idempotent: safe to run multiple times

-- Add new columns (IF NOT EXISTS via DO block)
DO $$
BEGIN
    -- Add full_response column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'full_response'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN full_response JSONB;
    END IF;

    -- Add query column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'query'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN query TEXT;
    END IF;

    -- Add input_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'input_type'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN input_type TEXT DEFAULT 'text';
    END IF;

    -- Add product_names column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'product_names'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN product_names TEXT[];
    END IF;
END $$;

-- Add indexes (IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_comparisons_user_created
    ON comparisons (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comparisons_product_names
    ON comparisons USING GIN (product_names);

CREATE INDEX IF NOT EXISTS idx_comparisons_query_search
    ON comparisons USING GIN (to_tsvector('english', coalesce(query, '')));
```

**Step 2: Commit**

```bash
git add migrations/001_update_comparisons.sql
git commit -m "feat(db): add migration for comparisons table update"
```

### Task 16: Add log_search() function to database_service.py

**Files:**
- Modify: `app/services/database_service.py` (add new section)

**Step 1: Add log_search function**

Add after the comparison functions section:

```python
# ============================================
# Search Logging Functions
# ============================================

async def log_search(
    query: str,
    input_type: str = "text",
    user_id: Optional[str] = None,
    products_found: Optional[List[str]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    cost: float = 0.0,
    duration_ms: int = 0,
) -> None:
    """
    Log a search/comparison request for analytics. Fire-and-forget.

    Args:
        query: The search query
        input_type: "text" or "camera"
        user_id: Authenticated user ID or None
        products_found: List of product names identified
        success: Whether the comparison succeeded
        error_message: Error message if failed
        cost: Total API cost in USD
        duration_ms: Request duration in milliseconds
    """
    try:
        client = get_supabase_client()
        record = {
            "query": query,
            "input_type": input_type,
            "products_found": products_found or [],
            "success": success,
            "cost": cost,
            "duration_ms": duration_ms,
        }
        if user_id:
            record["user_id"] = user_id
        if error_message:
            record["error_message"] = error_message

        client.table("search_logs").insert(record).execute()
    except Exception as e:
        # Never fail the request for logging
        print(f"Error logging search: {e}")
```

**Step 2: Syntax check**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output

**Step 3: Commit**

```bash
git add app/services/database_service.py
git commit -m "feat(db): add log_search() for analytics"
```

### Task 17: Wire log_search into text_routes.py and image_routes.py

**Files:**
- Modify: `app/api/text_routes.py`
- Modify: `app/api/image_routes.py`

**Step 1: Update text_routes.py imports**

Add `log_search` to the existing database_service import:
```python
from app.services.database_service import save_comparison, log_search
```

Also add:
```python
import time
```

**Step 2: Add logging to POST text endpoint**

Wrap the comparison call with timing, and log after:

```python
@router.post("/compare")
async def text_compare(request: TextCompareRequest, user: Optional[Dict] = Depends(get_optional_user)):
    logger.info(f"Text comparison request: {request.query}")

    service = get_comparison_service()
    start_time = time.time()

    result = await service.compare_from_text(
        query=request.query,
        region=request.region,
        include_specs=request.include_specs,
        include_reviews=request.include_reviews,
        include_pros_cons=request.include_pros_cons
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success"):
        # Log failed search
        asyncio.create_task(log_search(
            query=request.query, input_type="text",
            user_id=user.get("id") if user else None,
            success=False, error_message=result.get("error"),
            duration_ms=duration_ms,
        ))
        raise HTTPException(status_code=400, detail=result.get("error", "Comparison failed"))

    # Extract product names for logging
    product_names = [f"{p.get('brand', '')} {p.get('name', '')}".strip()
                     for p in result.get("products", [])]

    user_id = user.get("id") if user else None

    # Fire-and-forget: log search + save history
    asyncio.create_task(log_search(
        query=request.query, input_type="text", user_id=user_id,
        products_found=product_names, success=True,
        cost=result.get("metadata", {}).get("total_cost", 0),
        duration_ms=duration_ms,
    ))
    if user_id:
        asyncio.create_task(save_comparison(
            full_response=result, query=request.query,
            input_type="text", user_id=user_id,
        ))

    return result
```

**Step 3: Apply same pattern to GET text endpoint**

Same pattern as POST — add `start_time`, compute `duration_ms`, log search, save comparison.

**Step 4: Update image_routes.py similarly**

Add imports and log_search call with `input_type="camera"`.

**Step 5: Syntax check both files**

Run: `python -m py_compile app/api/text_routes.py && python -m py_compile app/api/image_routes.py`
Expected: No output

**Step 6: Commit**

```bash
git add app/api/text_routes.py app/api/image_routes.py
git commit -m "feat(db): wire search logging into text and image endpoints"
```

### Task 18: Add upsert_product() for lightweight dedup

**Files:**
- Modify: `app/services/database_service.py`

**Step 1: Add function**

```python
# ============================================
# Product Dedup Functions
# ============================================

async def upsert_product(
    canonical_name: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[str]:
    """
    Upsert a product by exact canonical_name. Returns product ID.
    Updates last_seen_at on existing records.
    """
    try:
        client = get_supabase_client()
        response = client.table("products").upsert(
            {
                "canonical_name": canonical_name,
                "brand": brand,
                "category": category,
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="canonical_name",
        ).execute()
        return response.data[0]["id"] if response.data else None
    except Exception as e:
        print(f"Error upserting product: {e}")
        return None


async def upsert_products_from_comparison(full_response: Dict) -> List[str]:
    """
    Upsert all products from a comparison response. Returns list of product IDs.
    """
    product_ids = []
    for product in full_response.get("products", []):
        name = f"{product.get('brand', '')} {product.get('name', '')}".strip()
        if name:
            pid = await upsert_product(
                canonical_name=name,
                brand=product.get("brand"),
                category=product.get("category"),
            )
            if pid:
                product_ids.append(pid)
    return product_ids
```

**Step 2: Syntax check**

Run: `python -m py_compile app/services/database_service.py`
Expected: No output

**Step 3: Commit**

```bash
git add app/services/database_service.py
git commit -m "feat(db): add upsert_product() for lightweight product dedup"
```

### Task 19: Create SQL migration for search_logs and products tables

**Files:**
- Create: `migrations/002_search_logs_and_products.sql`

**Step 1: Write migration**

```sql
-- Migration: Ensure search_logs and products tables exist with correct schema
-- Idempotent: safe to run multiple times

-- search_logs table
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    query TEXT NOT NULL,
    input_type TEXT DEFAULT 'text',
    products_found JSONB DEFAULT '[]'::jsonb,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    cost DECIMAL(10, 6) DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_logs_user_created
    ON search_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_logs_created
    ON search_logs (created_at DESC);

-- products table (ensure canonical_name unique constraint)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'products' AND constraint_type = 'UNIQUE'
        AND constraint_name = 'products_canonical_name_key'
    ) THEN
        -- Table may already exist from earlier schema; add constraint if missing
        ALTER TABLE products ADD CONSTRAINT products_canonical_name_key UNIQUE (canonical_name);
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        CREATE TABLE products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            canonical_name TEXT UNIQUE NOT NULL,
            brand TEXT,
            category TEXT,
            variants JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
END $$;

CREATE INDEX IF NOT EXISTS idx_products_canonical_name
    ON products (canonical_name);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products (category);
```

**Step 2: Commit**

```bash
git add migrations/002_search_logs_and_products.sql
git commit -m "feat(db): add migration for search_logs and products tables"
```

### Task 20: Write DB unit tests

**Files:**
- Create: `tests/test_db_improvements.py`

**Step 1: Write tests**

```python
"""Tests for database improvements — log_search, upsert_product."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_log_search_success():
    """log_search writes correct fields."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(
            query="iphone vs samsung",
            input_type="text",
            user_id="user-123",
            products_found=["Apple iPhone 15", "Samsung Galaxy S24"],
            success=True,
            cost=0.01,
            duration_ms=5000,
        )

    mock_client.table.assert_called_with("search_logs")
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["query"] == "iphone vs samsung"
    assert insert_arg["user_id"] == "user-123"
    assert insert_arg["products_found"] == ["Apple iPhone 15", "Samsung Galaxy S24"]
    assert insert_arg["success"] is True
    assert insert_arg["cost"] == 0.01
    assert insert_arg["duration_ms"] == 5000


@pytest.mark.asyncio
async def test_log_search_no_user():
    """log_search omits user_id when None."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(query="test", success=True)

    insert_arg = mock_table.insert.call_args[0][0]
    assert "user_id" not in insert_arg


@pytest.mark.asyncio
async def test_log_search_with_error():
    """log_search includes error_message when provided."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(
            query="bad query",
            success=False,
            error_message="Could not parse products",
        )

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["success"] is False
    assert insert_arg["error_message"] == "Could not parse products"


@pytest.mark.asyncio
async def test_log_search_swallows_errors():
    """log_search never raises — fire-and-forget."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB unreachable")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        # Should not raise
        await log_search(query="test", success=True)


@pytest.mark.asyncio
async def test_upsert_product_new():
    """upsert_product creates new product and returns ID."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-123"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        result = await upsert_product(
            canonical_name="Apple iPhone 15",
            brand="Apple",
            category="electronics",
        )

    assert result == "prod-123"
    upsert_arg = mock_table.upsert.call_args[0][0]
    assert upsert_arg["canonical_name"] == "Apple iPhone 15"
    assert upsert_arg["brand"] == "Apple"
    assert upsert_arg["category"] == "electronics"


@pytest.mark.asyncio
async def test_upsert_product_uses_conflict():
    """upsert_product uses on_conflict=canonical_name."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-456"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        await upsert_product(canonical_name="Test Product")

    _, kwargs = mock_table.upsert.call_args
    assert kwargs["on_conflict"] == "canonical_name"


@pytest.mark.asyncio
async def test_upsert_product_handles_error():
    """upsert_product returns None on error."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB error")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        result = await upsert_product(canonical_name="Test")

    assert result is None


@pytest.mark.asyncio
async def test_upsert_products_from_comparison():
    """upsert_products_from_comparison processes all products."""
    mock_response = MagicMock()
    call_count = [0]

    def mock_upsert(*args, **kwargs):
        call_count[0] += 1
        mock = MagicMock()
        mock.execute.return_value = MagicMock(data=[{"id": f"prod-{call_count[0]}"}])
        return mock

    mock_table = MagicMock()
    mock_table.upsert = mock_upsert

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    full_response = {
        "products": [
            {"brand": "Apple", "name": "iPhone 15", "category": "electronics"},
            {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics"},
        ]
    }

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_products_from_comparison
        ids = await upsert_products_from_comparison(full_response)

    assert len(ids) == 2


@pytest.mark.asyncio
async def test_upsert_products_skips_empty_names():
    """upsert_products_from_comparison skips products with empty names."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-1"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    full_response = {
        "products": [
            {"brand": "", "name": "", "category": "unknown"},
            {"brand": "Apple", "name": "iPhone 15"},
        ]
    }

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_products_from_comparison
        ids = await upsert_products_from_comparison(full_response)

    # Only the second product should be upserted
    assert len(ids) == 1
```

**Step 2: Run tests**

Run: `python -m pytest tests/test_db_improvements.py -v`
Expected: 9 passed

**Step 3: Commit**

```bash
git add tests/test_db_improvements.py
git commit -m "test(db): add 9 unit tests for log_search and upsert_product"
```

### Task 21: Clean up dead code in database_service.py

**Files:**
- Modify: `app/services/database_service.py:192-297`

**Step 1: Check if daily_usage and price_cache functions are used anywhere**

Search for:
- `get_daily_usage_db` — check if imported/called anywhere except database_service.py
- `increment_daily_usage_db` — same
- `cache_price_db` — same
- `get_cached_price_db` — same

If unused (likely — Redis is used for both daily usage and price caching), remove the entire "Daily Usage Functions" and "Price Cache Functions" sections (lines 192-297).

**Step 2: Commit**

```bash
git add app/services/database_service.py
git commit -m "chore(db): remove dead daily_usage and price_cache functions"
```

---

## Cross-QA Phase

### Task 22: Auth Agent QAs History Agent's work

**QA Checklist:**
1. Read all files modified by History Agent (database_service.py, text_routes.py, image_routes.py, routes.py, HistoryScreen.tsx, api.ts)
2. Run all history tests: `python -m pytest tests/test_history.py -v`
3. Check: `save_comparison()` is truly fire-and-forget (asyncio.create_task, exception caught)
4. Check: No SQL injection in search param (ilike with user input — should use parameterized queries via Supabase client)
5. Check: Delete endpoint verifies user ownership
6. Check: HistoryScreen correctly reads from `full_response` blob
7. Check: `viewAsResult()` passes blob directly without transformation
8. If issues found → create specific feedback and send back to History Agent

### Task 23: History Agent QAs DB Agent's work

**QA Checklist:**
1. Read all files modified by DB Agent (database_service.py, migrations/, text_routes.py, image_routes.py)
2. Run all DB tests: `python -m pytest tests/test_db_improvements.py -v`
3. Check: Migrations are idempotent (IF NOT EXISTS everywhere)
4. Check: `log_search()` is truly fire-and-forget
5. Check: `upsert_product()` uses correct on_conflict
6. Check: No dead code left in database_service.py
7. If issues found → send back

### Task 24: DB Agent QAs Auth Agent's work

**QA Checklist:**
1. Read all files modified by Auth Agent (api.ts, text_routes.py, image_routes.py, auth_routes.py)
2. Run all auth tests: `python -m pytest tests/test_auth_interceptor.py -v`
3. Check: Axios interceptor doesn't create circular dependency
4. Check: 401 refresh doesn't loop infinitely (auth endpoints excluded)
5. Check: `get_optional_user` never throws (all exceptions caught)
6. Check: Optional auth means anonymous users can still compare products
7. If issues found → send back

---

## Final Verification

### Task 25: Run full test suite

**Run:**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```

Expected: All tests pass (existing 146 + ~26 new = ~172 tests)

### Task 26: Apply SQL migrations

Apply via Supabase MCP tool or dashboard:
1. Run `migrations/001_update_comparisons.sql`
2. Run `migrations/002_search_logs_and_products.sql`

### Task 27: Final commit and summary

```bash
git add -A
git status
# Review all changes
git commit -m "feat: complete history, auth & database improvements

- Auth: axios JWT interceptor + 401 refresh + optional auth on endpoints
- History: full JSONB blob storage, search, delete, updated UI
- DB: search_logs, product dedup, comparisons schema update, dead code cleanup
- Tests: 26 new unit tests (auth: 7, history: 10, db: 9)"
```
