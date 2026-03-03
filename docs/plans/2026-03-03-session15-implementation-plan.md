# Session 15: Account Panel, Social Auth, Bug Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix image upload and history 401 bugs, add account settings screen with name/email/password editing, add native Google + Apple sign-in, fix EAS build, achieve 80% test coverage on new code.

**Architecture:** Backend-mediated social auth — native SDKs get idToken on frontend, POST to our backend, backend calls Supabase `sign_in_with_id_token()` to create/link accounts. Account settings use 3 new RESTful endpoints. Image fix uses `expo-image-manipulator` to guarantee JPEG transcoding.

**Tech Stack:** FastAPI, Supabase Auth (Python client), React Native, Expo SDK 54, `@react-native-google-signin/google-signin`, `expo-apple-authentication`, `expo-image-manipulator`

---

## Team Structure

| Agent | Name | Primary Work | QAs |
|-------|------|-------------|-----|
| 1 | `backend` | Auth endpoints, HEIC detection, social auth backend, tests | Agent 3 (`frontend-auth`) |
| 2 | `frontend-core` | AccountScreen, image fix, history fix, navigation, validation, tests | Agent 1 (`backend`) |
| 3 | `frontend-auth` | Google/Apple sign-in, Login/Register buttons, EAS fix, tests | Agent 2 (`frontend-core`) |

**All agents:** Opus, `bypassPermissions` mode. Circular QA (1→3, 2→1, 3→2). Idle agents write tests.

---

## Agent 1: Backend (`backend`)

### Task 1.1: HEIC Magic Byte Detection Safety Net

**Files:**
- Modify: `app/api/image_routes.py:69-78`
- Test: `tests/test_camera_vision.py`

**Step 1: Write failing test**

Add to `tests/test_camera_vision.py`:

```python
def test_heic_image_rejected_with_clear_error():
    """Backend should detect HEIC magic bytes and return 400, not forward to OpenAI."""
    # HEIC magic bytes: starts with ftyp box
    heic_bytes = b'\x00\x00\x00\x1c' + b'ftyp' + b'heic' + b'\x00' * 20

    from app.api.image_routes import _detect_mime_type
    mime = _detect_mime_type(heic_bytes, "image/jpeg")
    assert mime == "image/heic"


def test_gif_magic_bytes_detected():
    """GIF87a and GIF89a should be detected."""
    from app.api.image_routes import _detect_mime_type
    gif87 = b'GIF87a' + b'\x00' * 20
    gif89 = b'GIF89a' + b'\x00' * 20
    assert _detect_mime_type(gif87, "image/jpeg") == "image/gif"
    assert _detect_mime_type(gif89, "image/jpeg") == "image/gif"


def test_jpeg_magic_bytes_detected():
    """JPEG should be correctly detected from magic bytes."""
    from app.api.image_routes import _detect_mime_type
    jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 20
    assert _detect_mime_type(jpeg_bytes, "image/png") == "image/jpeg"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_camera_vision.py::test_heic_image_rejected_with_clear_error -v
```
Expected: FAIL — `_detect_mime_type` doesn't exist yet.

**Step 3: Extract MIME detection into a function and add HEIC/GIF support**

In `app/api/image_routes.py`, add this function before the endpoint:

```python
# Supported image MIME types for OpenAI Vision
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def _detect_mime_type(content: bytes, fallback: str = "image/jpeg") -> str:
    """Detect image MIME type from magic bytes."""
    if content[:2] == b"\xff\xd8":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:4] == b"RIFF" and len(content) > 12 and content[8:12] == b"WEBP":
        return "image/webp"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    # HEIC/HEIF detection: ftyp box with heic/heix/hevc/mif1 brand
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"mif1"):
            return "image/heic"
    return fallback
```

Then update the image reading loop (replace lines 69-78):

```python
        content_type = _detect_mime_type(content, img.content_type or "image/jpeg")

        if content_type not in SUPPORTED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Image {i+1} has unsupported format ({content_type}). "
                       f"Please use JPEG, PNG, WebP, or GIF."
            )
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_camera_vision.py -v -k "heic or gif or jpeg_magic"
```
Expected: ALL PASS

**Step 5: Commit**

```bash
git add app/api/image_routes.py tests/test_camera_vision.py
git commit -m "fix: add HEIC magic byte detection, reject unsupported image formats"
```

---

### Task 1.2: Backend `update_profile()` Endpoint

**Files:**
- Modify: `app/services/auth_service.py`
- Modify: `app/api/auth_routes.py`
- Test: `tests/test_auth_interceptor.py`

**Step 1: Write failing test**

Add to `tests/test_auth_interceptor.py`:

```python
@pytest.mark.asyncio
async def test_update_profile_endpoint(test_client, mock_supabase):
    """PUT /api/v1/auth/profile should update display name."""
    response = test_client.put(
        "/api/v1/auth/profile",
        json={"display_name": "Test User"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_update_profile_requires_auth(test_client):
    """PUT /api/v1/auth/profile without token should return 401."""
    response = test_client.put(
        "/api/v1/auth/profile",
        json={"display_name": "Test User"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_validates_name(test_client, mock_supabase):
    """Display name must be 2-100 chars."""
    response = test_client.put(
        "/api/v1/auth/profile",
        json={"display_name": "X"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 422
```

**Step 2: Run to verify failure**

```bash
python -m pytest tests/test_auth_interceptor.py::test_update_profile_endpoint -v
```
Expected: FAIL — 404 or 405 (endpoint doesn't exist)

**Step 3: Implement**

In `app/api/auth_routes.py`, add request model:

```python
class UpdateProfileRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
```

Add endpoint:

```python
@router.put("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user display name."""
    result = await update_user_profile(current_user["id"], body.display_name)
    return result
```

In `app/services/auth_service.py`, add:

```python
async def update_user_profile(user_id: str, display_name: str) -> dict:
    """Update display name in users table."""
    try:
        client = get_admin_client()
        response = client.table("users").update({
            "display_name": display_name
        }).eq("id", user_id).execute()
        return {"success": True, "message": "Profile updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_auth_interceptor.py -v -k "update_profile"
```
Expected: ALL PASS

**Step 5: Commit**

```bash
git add app/api/auth_routes.py app/services/auth_service.py tests/test_auth_interceptor.py
git commit -m "feat: add PUT /auth/profile endpoint for display name update"
```

---

### Task 1.3: Backend `update_email()` Endpoint

**Files:**
- Modify: `app/services/auth_service.py`
- Modify: `app/api/auth_routes.py`
- Test: `tests/test_auth_interceptor.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_update_email_endpoint(test_client, mock_supabase):
    """PUT /api/v1/auth/email should trigger email update."""
    response = test_client.put(
        "/api/v1/auth/email",
        json={"new_email": "newemail@example.com"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_update_email_validates_format(test_client, mock_supabase):
    """Invalid email format should return 422."""
    response = test_client.put(
        "/api/v1/auth/email",
        json={"new_email": "not-an-email"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 422
```

**Step 2: Verify failure, Step 3: Implement**

Request model:

```python
class UpdateEmailRequest(BaseModel):
    new_email: EmailStr
```

Endpoint:

```python
@router.put("/email")
async def update_email(
    body: UpdateEmailRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user email. Supabase sends a verification email to the new address."""
    result = await update_user_email(current_user["id"], str(body.new_email))
    return result
```

Service function:

```python
async def update_user_email(user_id: str, new_email: str) -> dict:
    """Update email via Supabase Admin API (sends verification to new email)."""
    try:
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"email": new_email})
        return {"success": True, "message": "Verification email sent to new address"}
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            return {"success": False, "error": "Email already in use"}
        return {"success": False, "error": error_msg}
```

**Step 4: Run tests, Step 5: Commit**

```bash
git add app/api/auth_routes.py app/services/auth_service.py tests/test_auth_interceptor.py
git commit -m "feat: add PUT /auth/email endpoint with Supabase verification"
```

---

### Task 1.4: Backend `change_password()` Endpoint

**Files:**
- Modify: `app/services/auth_service.py`
- Modify: `app/api/auth_routes.py`
- Test: `tests/test_auth_interceptor.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_change_password_endpoint(test_client, mock_supabase):
    """PUT /api/v1/auth/password should change password."""
    response = test_client.put(
        "/api/v1/auth/password",
        json={"current_password": "oldpass123", "new_password": "newpass123"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_change_password_min_length(test_client, mock_supabase):
    """New password must be at least 6 chars."""
    response = test_client.put(
        "/api/v1/auth/password",
        json={"current_password": "oldpass123", "new_password": "12345"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 422
```

**Step 2: Verify failure, Step 3: Implement**

Request model:

```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
```

Endpoint:

```python
@router.put("/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change password. Requires current password for verification."""
    result = await change_user_password(
        current_user["id"], current_user["email"],
        body.current_password, body.new_password
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

Service function:

```python
async def change_user_password(user_id: str, email: str, current_password: str, new_password: str) -> dict:
    """Verify current password then update to new password."""
    try:
        # Verify current password by attempting login
        auth_client = get_auth_client()
        auth_client.auth.sign_in_with_password({"email": email, "password": current_password})

        # Update password via admin API
        admin = get_admin_client()
        admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        return {"success": True, "message": "Password changed successfully"}
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return {"success": False, "error": "Current password is incorrect"}
        return {"success": False, "error": error_msg}
```

**Step 4: Run tests, Step 5: Commit**

```bash
git add app/api/auth_routes.py app/services/auth_service.py tests/test_auth_interceptor.py
git commit -m "feat: add PUT /auth/password endpoint with current password verification"
```

---

### Task 1.5: Backend Social Auth Endpoint

**Files:**
- Modify: `app/services/auth_service.py`
- Modify: `app/api/auth_routes.py`
- Test: `tests/test_auth_interceptor.py`

**Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_social_login_google(test_client, mock_supabase):
    """POST /api/v1/auth/social-login with Google token should return session."""
    response = test_client.post(
        "/api/v1/auth/social-login",
        json={"provider": "google", "id_token": "mock-google-id-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "session" in data


@pytest.mark.asyncio
async def test_social_login_apple(test_client, mock_supabase):
    """POST /api/v1/auth/social-login with Apple token should return session."""
    response = test_client.post(
        "/api/v1/auth/social-login",
        json={"provider": "apple", "id_token": "mock-apple-identity-token"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_social_login_invalid_provider(test_client):
    """Only google and apple are valid providers."""
    response = test_client.post(
        "/api/v1/auth/social-login",
        json={"provider": "facebook", "id_token": "token"}
    )
    assert response.status_code == 422
```

**Step 2: Verify failure, Step 3: Implement**

Request model:

```python
class SocialLoginRequest(BaseModel):
    provider: Literal["google", "apple"]
    id_token: str
    nonce: Optional[str] = None  # Apple Sign-In uses nonce
```

Endpoint:

```python
@router.post("/social-login")
async def social_login(body: SocialLoginRequest):
    """Authenticate via Google or Apple ID token. Creates account if new."""
    result = await sign_in_with_social(body.provider, body.id_token, body.nonce)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result
```

Service function:

```python
async def sign_in_with_social(provider: str, id_token: str, nonce: str = None) -> dict:
    """Sign in with social provider via Supabase's signInWithIdToken."""
    try:
        auth_client = get_auth_client()

        credentials = {"provider": provider, "token": id_token}
        if nonce:
            credentials["nonce"] = nonce

        response = auth_client.auth.sign_in_with_id_token(credentials)

        if not response.user:
            return {"success": False, "error": "Authentication failed"}

        # Ensure user exists in our users table
        admin = get_admin_client()
        existing = admin.table("users").select("id").eq("id", response.user.id).execute()
        if not existing.data:
            admin.table("users").insert({
                "id": response.user.id,
                "email": response.user.email,
                "auth_provider": provider,
                "subscription_tier": "free",
            }).execute()

        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_at": response.session.expires_at if response.session else None,
            },
            "message": f"Signed in with {provider}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 4: Run tests, Step 5: Commit**

```bash
git add app/api/auth_routes.py app/services/auth_service.py tests/test_auth_interceptor.py
git commit -m "feat: add POST /auth/social-login for Google and Apple sign-in"
```

---

### Task 1.6: QA Agent 3's Frontend Auth Work

Read and test Agent 3's social auth implementation:
- Verify `signInWithGoogle()` and `signInWithApple()` call the correct backend endpoint
- Verify Login/Register screens show social buttons correctly
- Verify EAS build fix has all required plugins
- Run `npx tsc --noEmit` in SmartCompareApp to check for type errors
- Run all tests: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- If issues found, send work back with specific feedback

---

## Agent 2: Frontend Core (`frontend-core`)

### Task 2.1: Fix Image Transcoding with `expo-image-manipulator`

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts:185-241`
- Test: manual verification (image manipulator is runtime-only)

**Step 1: Install dependency**

```bash
cd SmartCompareApp && npx expo install expo-image-manipulator
```

**Step 2: Update `identifyFromImages()` in `api.ts`**

Add import at top of `api.ts`:

```typescript
import * as ImageManipulator from 'expo-image-manipulator';
```

Replace the `identifyFromImages` function (lines 185-241):

```typescript
export async function identifyFromImages(
  imageUris: string[],
  region: string = 'bahrain'
): Promise<ImageIdentifyResult> {
  console.log('=== IDENTIFY FROM IMAGES ===');
  console.log(`${imageUris.length} image(s), region=${region}`);

  const formData = new FormData();

  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];

    // Transcode every image to JPEG — guarantees format regardless of source (HEIC, PNG, etc.)
    const manipulated = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: 1024 } }],
      { format: ImageManipulator.SaveFormat.JPEG, compress: 0.8 }
    );

    formData.append('images', {
      uri: manipulated.uri,
      type: 'image/jpeg',
      name: `product_${i + 1}.jpg`,
    } as any);
  }

  // Attach auth token if available (fetch doesn't use axios interceptor)
  const token = await getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/image/identify?region=${encodeURIComponent(region)}`,
    {
      method: 'POST',
      body: formData,
      headers,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Identify response error:', response.status, errorText);
    throw new Error(`Server error ${response.status}: ${errorText}`);
  }

  const data: ImageIdentifyResult = await response.json();
  console.log('Identify response action:', (data as any).action);
  return data;
}
```

Note: `getToken` is imported from `authService.ts` — check it's already imported, add if not:

```typescript
import { getToken } from './authService';
```

**Step 3: Verify syntax**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

**Step 4: Commit**

```bash
git add SmartCompareApp/src/services/api.ts SmartCompareApp/package.json SmartCompareApp/package-lock.json
git commit -m "fix: transcode images to JPEG via expo-image-manipulator before upload"
```

---

### Task 2.2: Fix HistoryScreen 401 Handling

**Files:**
- Modify: `SmartCompareApp/src/screens/HistoryScreen.tsx`

**Step 1: Update `loadHistory` to show sign-in prompt on 401**

Find the `loadHistory` function and update the error handling:

```typescript
const [authError, setAuthError] = useState(false);

const loadHistory = async () => {
  try {
    setAuthError(false);
    const data = await getComparisonHistory(50, 0, searchQuery || undefined);
    setHistory(data.comparisons || []);
    setTotal(data.total || 0);
  } catch (error) {
    const status = (error as any)?.response?.status;
    if (status === 401) {
      setAuthError(true);
      setHistory([]);
    } else {
      console.error('Error loading history:', error);
      Alert.alert('Error', 'Failed to load history');
    }
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
};
```

Add a sign-in prompt in the render (where the empty state / list is shown):

```typescript
{authError && (
  <View style={styles.authPrompt}>
    <Text style={styles.authPromptTitle}>Sign In Required</Text>
    <Text style={styles.authPromptText}>
      Sign in to view your comparison history.
    </Text>
    <TouchableOpacity
      style={styles.signInButton}
      onPress={() => navigation.navigate('Login')}
    >
      <Text style={styles.signInButtonText}>Sign In</Text>
    </TouchableOpacity>
  </View>
)}
```

**Step 2: Add styles for the auth prompt**

```typescript
authPrompt: {
  flex: 1,
  justifyContent: 'center',
  alignItems: 'center',
  padding: 24,
},
authPromptTitle: {
  fontSize: 20,
  fontWeight: '600',
  color: '#333',
  marginBottom: 8,
},
authPromptText: {
  fontSize: 16,
  color: '#666',
  textAlign: 'center',
  marginBottom: 24,
},
signInButton: {
  backgroundColor: '#007AFF',
  paddingHorizontal: 32,
  paddingVertical: 12,
  borderRadius: 8,
},
signInButtonText: {
  color: '#FFF',
  fontSize: 16,
  fontWeight: '600',
},
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/HistoryScreen.tsx
git commit -m "fix: show sign-in prompt on history 401 instead of crashing"
```

---

### Task 2.3: Add Navigation Types and AccountScreen Route

**Files:**
- Modify: `SmartCompareApp/src/types/types.ts`
- Modify: `SmartCompareApp/App.tsx`

**Step 1: Add Account to navigation types**

In `types.ts`, find the main stack param list (look for `Home`, `Camera`, `Results`, `History`) and add:

```typescript
Account: undefined;
```

**Step 2: Register AccountScreen in App.tsx**

Import AccountScreen (after it's created in Task 2.4):

```typescript
import AccountScreen from './src/screens/AccountScreen';
```

Add to the MainNavigator stack (after History screen):

```typescript
<RootStack.Screen name="Account" component={AccountScreen} options={{ title: 'Account Settings' }} />
```

**Step 3: Add settings icon to HomeScreen**

In `SmartCompareApp/src/screens/HomeScreen.tsx`, find the header section (the `profileButton` area) and replace it with a settings gear icon:

```typescript
<TouchableOpacity
  style={styles.profileButton}
  onPress={() => navigation.navigate('Account')}
>
  <Text style={styles.profileEmoji}>⚙️</Text>
</TouchableOpacity>
```

**Step 4: Commit**

```bash
git add SmartCompareApp/src/types/types.ts SmartCompareApp/App.tsx SmartCompareApp/src/screens/HomeScreen.tsx
git commit -m "feat: add Account screen navigation route and settings icon"
```

---

### Task 2.4: Create AccountScreen

**Files:**
- Create: `SmartCompareApp/src/screens/AccountScreen.tsx`
- Modify: `SmartCompareApp/src/services/api.ts` (add API functions)

**Step 1: Add API functions to `api.ts`**

```typescript
export async function updateProfile(displayName: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/profile', { display_name: displayName });
  return response.data;
}

export async function updateEmail(newEmail: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/email', { new_email: newEmail });
  return response.data;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/password', { current_password: currentPassword, new_password: newPassword });
  return response.data;
}
```

**Step 2: Create AccountScreen**

Create `SmartCompareApp/src/screens/AccountScreen.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  Alert, ActivityIndicator, Modal, SafeAreaView, Platform,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { updateProfile, updateEmail, changePassword } from '../services/api';
import { getSavedUser, logout } from '../services/authService';

type Props = {
  navigation: NativeStackNavigationProp<any>;
};

export default function AccountScreen({ navigation }: Props) {
  const [user, setUser] = useState<any>(null);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [nameLoading, setNameLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [nameError, setNameError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [nameSuccess, setNameSuccess] = useState('');
  const [emailSuccess, setEmailSuccess] = useState('');

  // Password modal state
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    if (savedUser) {
      setUser(savedUser);
      setDisplayName(savedUser.display_name || savedUser.email?.split('@')[0] || '');
      setEmail(savedUser.email || '');
    }
  };

  // --- Validation helpers ---
  const validateName = (name: string): string | null => {
    const trimmed = name.trim();
    if (trimmed.length < 2) return 'Name must be at least 2 characters';
    if (trimmed.length > 100) return 'Name must be 100 characters or less';
    return null;
  };

  const validateEmail = (email: string): string | null => {
    const trimmed = email.trim();
    if (!trimmed) return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) return 'Invalid email format';
    return null;
  };

  const validatePassword = (password: string): string | null => {
    if (password.length < 6) return 'Password must be at least 6 characters';
    return null;
  };

  // --- Handlers ---
  const handleUpdateName = async () => {
    const error = validateName(displayName);
    if (error) { setNameError(error); return; }
    setNameError('');
    setNameSuccess('');
    setNameLoading(true);
    try {
      const result = await updateProfile(displayName.trim());
      if (result.success) {
        setNameSuccess('Name updated');
        setTimeout(() => setNameSuccess(''), 3000);
      } else {
        setNameError(result.error || 'Update failed');
      }
    } catch (err: any) {
      setNameError(err.message || 'An error occurred');
    } finally {
      setNameLoading(false);
    }
  };

  const handleUpdateEmail = async () => {
    const error = validateEmail(email);
    if (error) { setEmailError(error); return; }
    setEmailError('');
    setEmailSuccess('');
    setEmailLoading(true);
    try {
      const result = await updateEmail(email.trim());
      if (result.success) {
        setEmailSuccess('Verification email sent');
        setTimeout(() => setEmailSuccess(''), 5000);
      } else {
        setEmailError(result.error || 'Update failed');
      }
    } catch (err: any) {
      setEmailError(err.message || 'An error occurred');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword) { setPasswordError('Current password is required'); return; }
    const pwError = validatePassword(newPassword);
    if (pwError) { setPasswordError(pwError); return; }
    if (newPassword !== confirmPassword) { setPasswordError('Passwords do not match'); return; }
    setPasswordError('');
    setPasswordLoading(true);
    try {
      const result = await changePassword(currentPassword, newPassword);
      if (result.success) {
        Alert.alert('Success', 'Password changed successfully');
        setPasswordModalVisible(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setPasswordError(result.error || 'Password change failed');
      }
    } catch (err: any) {
      setPasswordError(err.message || 'An error occurred');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleLogout = async () => {
    Alert.alert('Log Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
          navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
        },
      },
    ]);
  };

  // --- Render ---
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(displayName || email || '?')[0].toUpperCase()}
            </Text>
          </View>
          <Text style={styles.headerEmail}>{email}</Text>
        </View>

        {/* Display Name */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Display Name</Text>
          <View style={styles.fieldRow}>
            <TextInput
              style={styles.input}
              value={displayName}
              onChangeText={(text) => { setDisplayName(text); setNameError(''); setNameSuccess(''); }}
              placeholder="Your name"
              maxLength={100}
            />
            <TouchableOpacity style={styles.saveButton} onPress={handleUpdateName} disabled={nameLoading}>
              {nameLoading ? <ActivityIndicator size="small" color="#FFF" /> : <Text style={styles.saveButtonText}>Save</Text>}
            </TouchableOpacity>
          </View>
          {nameError ? <Text style={styles.errorText}>{nameError}</Text> : null}
          {nameSuccess ? <Text style={styles.successText}>{nameSuccess}</Text> : null}
        </View>

        {/* Email */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Email</Text>
          <View style={styles.fieldRow}>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={(text) => { setEmail(text); setEmailError(''); setEmailSuccess(''); }}
              placeholder="your@email.com"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <TouchableOpacity style={styles.saveButton} onPress={handleUpdateEmail} disabled={emailLoading}>
              {emailLoading ? <ActivityIndicator size="small" color="#FFF" /> : <Text style={styles.saveButtonText}>Save</Text>}
            </TouchableOpacity>
          </View>
          {emailError ? <Text style={styles.errorText}>{emailError}</Text> : null}
          {emailSuccess ? <Text style={styles.successText}>{emailSuccess}</Text> : null}
        </View>

        {/* Security */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Security</Text>
          <TouchableOpacity style={styles.menuItem} onPress={() => setPasswordModalVisible(true)}>
            <Text style={styles.menuItemText}>Change Password</Text>
            <Text style={styles.menuItemArrow}>›</Text>
          </TouchableOpacity>
        </View>

        {/* Connected Accounts — placeholder for Agent 3 to populate */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Connected Accounts</Text>
          <Text style={styles.placeholderText}>Social login options will appear here.</Text>
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Password Change Modal */}
      <Modal visible={passwordModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Change Password</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Current password"
              secureTextEntry
              value={currentPassword}
              onChangeText={(t) => { setCurrentPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="New password (min 6 chars)"
              secureTextEntry
              value={newPassword}
              onChangeText={(t) => { setNewPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="Confirm new password"
              secureTextEntry
              value={confirmPassword}
              onChangeText={(t) => { setConfirmPassword(t); setPasswordError(''); }}
            />
            {passwordError ? <Text style={styles.errorText}>{passwordError}</Text> : null}
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancel}
                onPress={() => {
                  setPasswordModalVisible(false);
                  setPasswordError('');
                  setCurrentPassword('');
                  setNewPassword('');
                  setConfirmPassword('');
                }}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalSave, passwordLoading && { opacity: 0.6 }]}
                onPress={handleChangePassword}
                disabled={passwordLoading}
              >
                {passwordLoading ? (
                  <ActivityIndicator size="small" color="#FFF" />
                ) : (
                  <Text style={styles.modalSaveText}>Change Password</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  scrollContent: { padding: 16 },
  profileHeader: { alignItems: 'center', marginBottom: 24, marginTop: 8 },
  avatar: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#007AFF', justifyContent: 'center', alignItems: 'center', marginBottom: 8 },
  avatarText: { fontSize: 28, fontWeight: '700', color: '#FFF' },
  headerEmail: { fontSize: 14, color: '#888' },
  section: { backgroundColor: '#FFF', borderRadius: 12, padding: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 13, fontWeight: '600', color: '#888', textTransform: 'uppercase', marginBottom: 12 },
  fieldRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  input: { flex: 1, borderWidth: 1, borderColor: '#DDD', borderRadius: 8, paddingHorizontal: 12, paddingVertical: Platform.OS === 'ios' ? 12 : 8, fontSize: 16 },
  saveButton: { backgroundColor: '#007AFF', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8 },
  saveButtonText: { color: '#FFF', fontWeight: '600', fontSize: 14 },
  errorText: { color: '#FF3B30', fontSize: 13, marginTop: 6 },
  successText: { color: '#34C759', fontSize: 13, marginTop: 6 },
  menuItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  menuItemText: { fontSize: 16, color: '#333' },
  menuItemArrow: { fontSize: 20, color: '#CCC' },
  placeholderText: { fontSize: 14, color: '#AAA', fontStyle: 'italic' },
  logoutButton: { backgroundColor: '#FFF', borderRadius: 12, padding: 16, alignItems: 'center', marginTop: 8, marginBottom: 32 },
  logoutButtonText: { color: '#FF3B30', fontSize: 16, fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 24 },
  modalContent: { backgroundColor: '#FFF', borderRadius: 16, padding: 24 },
  modalTitle: { fontSize: 20, fontWeight: '700', marginBottom: 20, textAlign: 'center' },
  modalInput: { borderWidth: 1, borderColor: '#DDD', borderRadius: 8, paddingHorizontal: 12, paddingVertical: Platform.OS === 'ios' ? 12 : 8, fontSize: 16, marginBottom: 12 },
  modalButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  modalCancel: { paddingVertical: 12, paddingHorizontal: 20 },
  modalCancelText: { color: '#007AFF', fontSize: 16 },
  modalSave: { backgroundColor: '#007AFF', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8 },
  modalSaveText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
});
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/AccountScreen.tsx SmartCompareApp/src/services/api.ts
git commit -m "feat: add AccountScreen with name/email editing and password change modal"
```

---

### Task 2.5: Input Validation on Login and Register Screens

**Files:**
- Modify: `SmartCompareApp/src/screens/LoginScreen.tsx`
- Modify: `SmartCompareApp/src/screens/RegisterScreen.tsx`

**Step 1: Add validation to LoginScreen**

Before the `handleLogin` function, add inline validation that shows errors below inputs:

```typescript
const [emailError, setEmailError] = useState('');
const [passwordError, setPasswordError] = useState('');

const handleLogin = async () => {
  let hasError = false;
  const trimmedEmail = email.trim();

  if (!trimmedEmail) {
    setEmailError('Email is required');
    hasError = true;
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
    setEmailError('Invalid email format');
    hasError = true;
  } else {
    setEmailError('');
  }

  if (!password) {
    setPasswordError('Password is required');
    hasError = true;
  } else if (password.length < 6) {
    setPasswordError('Password must be at least 6 characters');
    hasError = true;
  } else {
    setPasswordError('');
  }

  if (hasError) return;

  // ... existing login logic
};
```

Add error text below each input:

```typescript
{emailError ? <Text style={styles.fieldError}>{emailError}</Text> : null}
```

**Step 2: Same pattern for RegisterScreen**

Add validation for email, password, and confirm password. Password fields must match.

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/LoginScreen.tsx SmartCompareApp/src/screens/RegisterScreen.tsx
git commit -m "feat: add inline input validation to Login and Register screens"
```

---

### Task 2.6: QA Agent 1's Backend Work

Read and test Agent 1's backend endpoints:
- Verify all 3 new auth endpoints (profile, email, password) return correct responses
- Verify HEIC detection rejects bad formats with clear error
- Verify social-login endpoint works with mock tokens
- Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- Run: `python -m py_compile app/api/auth_routes.py && python -m py_compile app/services/auth_service.py`
- If issues found, send work back with specific feedback

---

## Agent 3: Frontend Auth (`frontend-auth`)

### Task 3.1: Fix EAS Build — `app.json` Plugins

**Files:**
- Modify: `SmartCompareApp/app.json`

**Step 1: Read current `app.json`**

Current plugins section only has `"expo-secure-store"`.

**Step 2: Update plugins array**

```json
"plugins": [
  "expo-secure-store",
  [
    "expo-camera",
    {
      "cameraPermission": "SmartCompare needs camera access to photograph products for comparison."
    }
  ],
  [
    "expo-image-picker",
    {
      "photosPermission": "SmartCompare needs photo library access to identify products from your photos."
    }
  ],
  "expo-image-manipulator"
]
```

Also ensure `app.json` has iOS bundle identifier and Android package name:

```json
"ios": {
  "bundleIdentifier": "com.smartcompare.app",
  "supportsTablet": true
},
"android": {
  "package": "com.smartcompare.app",
  "adaptiveIcon": {
    "foregroundImage": "./assets/adaptive-icon.png",
    "backgroundColor": "#ffffff"
  }
}
```

**Step 3: Commit**

```bash
git add SmartCompareApp/app.json
git commit -m "fix: add missing expo-camera and expo-image-picker plugins to app.json"
```

---

### Task 3.2: Install and Configure Google Sign-In

**Files:**
- Install: `@react-native-google-signin/google-signin`
- Modify: `SmartCompareApp/app.json`
- Modify: `SmartCompareApp/src/services/authService.ts`

**Step 1: Install**

```bash
cd SmartCompareApp && npm install @react-native-google-signin/google-signin
```

**Step 2: Add to `app.json` plugins**

```json
"plugins": [
  ...existing plugins...,
  [
    "@react-native-google-signin/google-signin",
    {
      "iosUrlScheme": "com.googleusercontent.apps.YOUR_IOS_CLIENT_ID"
    }
  ]
]
```

Note: The `iosUrlScheme` placeholder will need to be replaced with the real Google client ID once created in Google Cloud Console. For now, use a placeholder and document it.

**Step 3: Add `signInWithGoogle()` to authService.ts**

```typescript
import { GoogleSignin } from '@react-native-google-signin/google-signin';

// Configure Google Sign-In (call once at app startup)
export function configureGoogleSignIn() {
  GoogleSignin.configure({
    webClientId: 'YOUR_GOOGLE_WEB_CLIENT_ID', // Replace with real client ID
    offlineAccess: true,
  });
}

export async function signInWithGoogle(): Promise<AuthResult> {
  try {
    await GoogleSignin.hasPlayServices();
    const signInResult = await GoogleSignin.signIn();
    const idToken = signInResult.data?.idToken;

    if (!idToken) {
      return { success: false, error: 'Failed to get Google ID token' };
    }

    // Send to our backend, which handles Supabase signInWithIdToken
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/social-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'google', id_token: idToken }),
    });

    const data = await response.json();

    if (data.success && data.session?.access_token) {
      await saveToken(data.session.access_token);
      await saveRefreshToken(data.session.refresh_token);
      if (data.user) await saveUser(data.user);
    }

    return data;
  } catch (error: any) {
    if (error.code === 'SIGN_IN_CANCELLED') {
      return { success: false, error: 'Sign-in cancelled' };
    }
    return { success: false, error: error.message || 'Google sign-in failed' };
  }
}
```

Note: Need to import/export `API_BASE_URL` or use the api instance. Check how `api.ts` exports it and use the same constant. Also ensure `saveToken`, `saveRefreshToken`, `saveUser` are accessible.

**Step 4: Call `configureGoogleSignIn()` in App.tsx**

Add to the top of `App.tsx` (outside component, or in useEffect):

```typescript
import { configureGoogleSignIn } from './src/services/authService';
configureGoogleSignIn();
```

**Step 5: Commit**

```bash
git add SmartCompareApp/src/services/authService.ts SmartCompareApp/app.json SmartCompareApp/App.tsx SmartCompareApp/package.json SmartCompareApp/package-lock.json
git commit -m "feat: install and configure native Google Sign-In SDK"
```

---

### Task 3.3: Install and Configure Apple Sign-In

**Files:**
- Install: `expo-apple-authentication`
- Modify: `SmartCompareApp/app.json`
- Modify: `SmartCompareApp/src/services/authService.ts`

**Step 1: Install**

```bash
cd SmartCompareApp && npx expo install expo-apple-authentication
```

**Step 2: Update `app.json`**

Add to iOS config:

```json
"ios": {
  "bundleIdentifier": "com.smartcompare.app",
  "supportsTablet": true,
  "usesAppleSignIn": true
}
```

Add to plugins:

```json
"expo-apple-authentication"
```

**Step 3: Add `signInWithApple()` to authService.ts**

```typescript
import * as AppleAuthentication from 'expo-apple-authentication';
import * as Crypto from 'expo-crypto';

export async function signInWithApple(): Promise<AuthResult> {
  try {
    // Generate nonce for security
    const rawNonce = Math.random().toString(36).substring(2, 15);
    const hashedNonce = await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      rawNonce
    );

    const credential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
      nonce: hashedNonce,
    });

    const idToken = credential.identityToken;
    if (!idToken) {
      return { success: false, error: 'Failed to get Apple identity token' };
    }

    // Send to our backend
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/social-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'apple',
        id_token: idToken,
        nonce: rawNonce,
      }),
    });

    const data = await response.json();

    if (data.success && data.session?.access_token) {
      await saveToken(data.session.access_token);
      await saveRefreshToken(data.session.refresh_token);
      if (data.user) await saveUser(data.user);
    }

    return data;
  } catch (error: any) {
    if (error.code === 'ERR_REQUEST_CANCELED') {
      return { success: false, error: 'Sign-in cancelled' };
    }
    return { success: false, error: error.message || 'Apple sign-in failed' };
  }
}

export async function isAppleSignInAvailable(): Promise<boolean> {
  return await AppleAuthentication.isAvailableAsync();
}
```

**Step 4: Install expo-crypto for nonce hashing**

```bash
cd SmartCompareApp && npx expo install expo-crypto
```

**Step 5: Commit**

```bash
git add SmartCompareApp/src/services/authService.ts SmartCompareApp/app.json SmartCompareApp/package.json SmartCompareApp/package-lock.json
git commit -m "feat: install and configure native Apple Sign-In with nonce support"
```

---

### Task 3.4: Add Social Sign-In Buttons to LoginScreen

**Files:**
- Modify: `SmartCompareApp/src/screens/LoginScreen.tsx`

**Step 1: Add social buttons after "Forgot Password?" link**

```typescript
import { signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';
import { Platform } from 'react-native';

// Inside component, add state:
const [socialLoading, setSocialLoading] = useState('');
const [showApple, setShowApple] = useState(false);

// Check Apple availability on mount:
useEffect(() => {
  if (Platform.OS === 'ios') {
    isAppleSignInAvailable().then(setShowApple);
  }
}, []);

// Handlers:
const handleGoogleSignIn = async () => {
  setSocialLoading('google');
  setError('');
  try {
    const result = await signInWithGoogle();
    if (result.success) {
      onLoginSuccess();
    } else {
      setError(result.error || 'Google sign-in failed');
    }
  } catch (err: any) {
    setError(err.message || 'Google sign-in failed');
  } finally {
    setSocialLoading('');
  }
};

const handleAppleSignIn = async () => {
  setSocialLoading('apple');
  setError('');
  try {
    const result = await signInWithApple();
    if (result.success) {
      onLoginSuccess();
    } else {
      setError(result.error || 'Apple sign-in failed');
    }
  } catch (err: any) {
    setError(err.message || 'Apple sign-in failed');
  } finally {
    setSocialLoading('');
  }
};
```

Add JSX after "Forgot Password?" and before the login button:

```typescript
{/* Social Sign-In */}
<View style={styles.dividerRow}>
  <View style={styles.dividerLine} />
  <Text style={styles.dividerText}>or</Text>
  <View style={styles.dividerLine} />
</View>

<TouchableOpacity
  style={styles.socialButton}
  onPress={handleGoogleSignIn}
  disabled={!!socialLoading}
>
  {socialLoading === 'google' ? (
    <ActivityIndicator size="small" color="#333" />
  ) : (
    <Text style={styles.socialButtonText}>Continue with Google</Text>
  )}
</TouchableOpacity>

{showApple && (
  <TouchableOpacity
    style={[styles.socialButton, styles.appleSocialButton]}
    onPress={handleAppleSignIn}
    disabled={!!socialLoading}
  >
    {socialLoading === 'apple' ? (
      <ActivityIndicator size="small" color="#FFF" />
    ) : (
      <Text style={[styles.socialButtonText, styles.appleSocialText]}>Continue with Apple</Text>
    )}
  </TouchableOpacity>
)}
```

Add styles:

```typescript
dividerRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 16 },
dividerLine: { flex: 1, height: 1, backgroundColor: '#DDD' },
dividerText: { marginHorizontal: 12, color: '#888', fontSize: 14 },
socialButton: { borderWidth: 1, borderColor: '#DDD', borderRadius: 8, paddingVertical: 12, alignItems: 'center', marginBottom: 10, backgroundColor: '#FFF' },
socialButtonText: { fontSize: 16, fontWeight: '500', color: '#333' },
appleSocialButton: { backgroundColor: '#000', borderColor: '#000' },
appleSocialText: { color: '#FFF' },
```

**Step 2: Commit**

```bash
git add SmartCompareApp/src/screens/LoginScreen.tsx
git commit -m "feat: add Google and Apple sign-in buttons to LoginScreen"
```

---

### Task 3.5: Add Social Sign-In Buttons to RegisterScreen

**Files:**
- Modify: `SmartCompareApp/src/screens/RegisterScreen.tsx`

Same pattern as Task 3.4 — add social buttons between the "Create Account" button and the benefits section. Reuse the same handlers and styles.

**Step 1: Commit**

```bash
git add SmartCompareApp/src/screens/RegisterScreen.tsx
git commit -m "feat: add Google and Apple sign-in buttons to RegisterScreen"
```

---

### Task 3.6: Add Connected Accounts to AccountScreen

**Files:**
- Modify: `SmartCompareApp/src/screens/AccountScreen.tsx`

**Step 1: Replace the "Connected Accounts" placeholder section**

Agent 2 left a placeholder. Replace it with:

```typescript
import { signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';

// Add state:
const [showApple, setShowApple] = useState(false);
const [socialLoading, setSocialLoading] = useState('');

useEffect(() => {
  if (Platform.OS === 'ios') {
    isAppleSignInAvailable().then(setShowApple);
  }
}, []);

// In the Connected Accounts section:
<View style={styles.section}>
  <Text style={styles.sectionTitle}>Connected Accounts</Text>
  <TouchableOpacity
    style={styles.socialConnectButton}
    onPress={async () => {
      setSocialLoading('google');
      const result = await signInWithGoogle();
      setSocialLoading('');
      if (result.success) {
        Alert.alert('Success', 'Google account connected');
      } else if (result.error !== 'Sign-in cancelled') {
        Alert.alert('Error', result.error || 'Failed to connect Google');
      }
    }}
    disabled={!!socialLoading}
  >
    <Text style={styles.socialConnectText}>
      {socialLoading === 'google' ? 'Connecting...' : 'Connect Google'}
    </Text>
  </TouchableOpacity>

  {showApple && (
    <TouchableOpacity
      style={[styles.socialConnectButton, { marginTop: 8 }]}
      onPress={async () => {
        setSocialLoading('apple');
        const result = await signInWithApple();
        setSocialLoading('');
        if (result.success) {
          Alert.alert('Success', 'Apple ID connected');
        } else if (result.error !== 'Sign-in cancelled') {
          Alert.alert('Error', result.error || 'Failed to connect Apple');
        }
      }}
      disabled={!!socialLoading}
    >
      <Text style={styles.socialConnectText}>
        {socialLoading === 'apple' ? 'Connecting...' : 'Connect Apple ID'}
      </Text>
    </TouchableOpacity>
  )}
</View>
```

Add style:

```typescript
socialConnectButton: { borderWidth: 1, borderColor: '#DDD', borderRadius: 8, paddingVertical: 12, alignItems: 'center', backgroundColor: '#FAFAFA' },
socialConnectText: { fontSize: 15, color: '#333', fontWeight: '500' },
```

**Step 2: Commit**

```bash
git add SmartCompareApp/src/screens/AccountScreen.tsx
git commit -m "feat: add Google and Apple connect buttons to AccountScreen"
```

---

### Task 3.7: QA Agent 2's Frontend Core Work

Read and test Agent 2's work:
- Verify `identifyFromImages()` properly transcodes images with `expo-image-manipulator`
- Verify HistoryScreen shows sign-in prompt on 401 (not crash)
- Verify AccountScreen renders all sections, validation works, password modal opens/closes
- Verify navigation: HomeScreen gear icon → AccountScreen → back
- Run: `cd SmartCompareApp && npx tsc --noEmit`
- If issues found, send work back with specific feedback

---

## Post-QA: Final Verification

After all 3 agents complete QA and all issues are resolved:

1. **Run full test suite:**
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```

2. **TypeScript check:**
```bash
cd SmartCompareApp && npx tsc --noEmit
```

3. **Syntax check backend:**
```bash
python -m py_compile app/api/auth_routes.py && python -m py_compile app/services/auth_service.py && python -m py_compile app/api/image_routes.py
```

4. **Final commit and push (leader only):**
```bash
git push origin main
```

---

## Configuration Checklist (Manual — After Code Deploy)

These require manual setup in external dashboards and are NOT part of the coding tasks:

- [ ] **Google Cloud Console:** Create OAuth 2.0 client IDs (Web + iOS + Android)
- [ ] **Supabase Dashboard:** Enable Google provider, paste client ID + secret
- [ ] **Replace placeholders:** `YOUR_GOOGLE_WEB_CLIENT_ID` in authService.ts, `iosUrlScheme` in app.json
- [ ] **Apple Developer (deferred):** Enable Sign in with Apple, configure Service ID
- [ ] **Supabase Dashboard (deferred):** Enable Apple provider when Apple Dev subscription is active
- [ ] **Supabase `users` table:** Add `display_name TEXT` and `auth_provider TEXT DEFAULT 'email'` columns if not present
- [ ] **EAS Build:** Run `eas build --profile development --platform ios` to verify build succeeds
