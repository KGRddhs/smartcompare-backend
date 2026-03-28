# Qaren Frontend Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the SmartCompare React Native app into Qaren — camera-first, bilingual (EN/AR), editorial design, with full RTL support and 3-free-comparison paywall.

**Architecture:** Replace all 9 existing screens with 10 new screens using a shared design system (theme + reusable components). Add i18n via i18next, RTL via I18nManager, bottom tab navigation via @react-navigation/bottom-tabs. Keep existing api.ts and authService.ts services mostly intact — they already work.

**Tech Stack:** React Native 0.81 + Expo 54, TypeScript 5.9, react-native-reanimated 3, expo-image, lucide-react-native, i18next + react-i18next + expo-localization, expo-haptics, @expo-google-fonts/inter + @expo-google-fonts/cairo

**Spec:** `docs/superpowers/specs/2026-03-28-qaren-frontend-redesign-design.md`

---

## File Structure

### New Files to Create
```
SmartCompareApp/src/
  theme/
    index.ts                    — Color tokens, typography, spacing, shadows, radii
    fonts.ts                    — Font loading (Inter + Cairo, 3 weights each)
  i18n/
    index.ts                    — i18next config + init
    en.json                     — English strings (~200 keys)
    ar.json                     — Arabic strings (~200 keys)
  components/
    Button.tsx                  — Primary/secondary/destructive button
    Card.tsx                    — Standard + winner variant
    Chip.tsx                    — Selectable pill + category pill
    SkeletonLoader.tsx          — Shimmer animation component
    ProgressBar.tsx             — Smooth non-linear progress bar
    IconButton.tsx              — RTL-aware directional icon wrapper
    TabBar.tsx                  — Custom bottom tab bar (3 tabs)
    SearchOverlay.tsx           — Full-screen search with recent + trending
    ComparisonCounter.tsx       — "2 of 3 free" pill badge
  screens/
    SplashScreen.tsx            — Logo animation → camera transition
    OnboardingScreen.tsx        — 6-step wizard (language, region, 4 prefs)
    HomeScreen.tsx              — Camera-first + search + categories (REWRITE)
    ResultsScreen.tsx           — Single-scroll comparison (REWRITE)
    HistoryScreen.tsx           — FlatList grouped by date (REWRITE)
    ProfileScreen.tsx           — Settings, language, account (REWRITE of AccountScreen)
    LoginScreen.tsx             — Restyled auth (REWRITE)
    RegisterScreen.tsx          — Restyled auth (REWRITE)
    ForgotPasswordScreen.tsx    — Restyled auth (REWRITE)
    PaywallScreen.tsx           — Bottom sheet subscription placeholder
  hooks/
    useComparisonCounter.ts     — Track 3 free comparisons (AsyncStorage)
    useLanguage.ts              — Language switching + RTL toggle
  utils/
    rtl.ts                      — RTL helper (icon flip, logical props check)
```

### Files to Modify
```
SmartCompareApp/
  App.tsx                       — Bottom tabs, splash flow, new screen names
  app.json                      — Rename to Qaren, add expo-localization plugin
  package.json                  — New dependencies
  src/services/api.ts           — Rename storage keys @smartcompare→@qaren
  src/services/authService.ts   — Rename storage keys @smartcompare→@qaren
  src/types/types.ts            — Add OnboardingData, PaywallState types
  src/components/CategorySelector.tsx — Restyle with theme tokens + i18n
  src/components/FeedbackCard.tsx     — Restyle with theme tokens + i18n
```

### Files to Delete
```
SmartCompareApp/src/screens/CameraScreen.tsx    — Absorbed into HomeScreen
SmartCompareApp/src/screens/AccountScreen.tsx    — Replaced by ProfileScreen
SmartCompareApp/src/screens/PreferencesScreen.tsx — Replaced by OnboardingScreen
```

---

## Phase 1: Foundation (Tasks 1–5)

### Task 1: Install Dependencies

**Files:**
- Modify: `SmartCompareApp/package.json`
- Modify: `SmartCompareApp/app.json`

- [ ] **Step 1: Install new packages**

```bash
cd SmartCompareApp
npx expo install react-native-reanimated expo-image lucide-react-native expo-haptics expo-localization @react-navigation/bottom-tabs react-native-gesture-handler @expo-google-fonts/inter @expo-google-fonts/cairo i18next react-i18next
```

- [ ] **Step 2: Update app.json for Qaren branding**

In `SmartCompareApp/app.json`, change:
```json
{
  "expo": {
    "name": "Qaren",
    "slug": "qaren",
    "plugins": [
      "expo-secure-store",
      "expo-localization",
      ["expo-camera", {
        "cameraPermission": "Qaren needs camera access to photograph products for comparison."
      }],
      ["expo-image-picker", {
        "photosPermission": "Qaren needs photo library access to identify products from your photos."
      }],
      ["@react-native-google-signin/google-signin", {
        "iosUrlScheme": "com.googleusercontent.apps.21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm"
      }],
      "expo-apple-authentication"
    ]
  }
}
```

Also update `ios.bundleIdentifier` to `"com.qaren.app"` and `android.package` to `"com.qaren.app"`.

- [ ] **Step 3: Add reanimated babel plugin**

Check if `babel.config.js` exists. If so, add `'react-native-reanimated/plugin'` as last plugin. If not, create it:

```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: ['react-native-reanimated/plugin'],
  };
};
```

- [ ] **Step 4: Verify install**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Expected: 0 errors (or only pre-existing errors unrelated to new deps).

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/package.json SmartCompareApp/app.json SmartCompareApp/babel.config.js SmartCompareApp/package-lock.json
git commit -m "chore: install Qaren dependencies (reanimated, i18n, expo-image, haptics, fonts)"
```

---

### Task 2: Theme System

**Files:**
- Create: `SmartCompareApp/src/theme/index.ts`
- Create: `SmartCompareApp/src/theme/fonts.ts`

- [ ] **Step 1: Create theme tokens**

Create `SmartCompareApp/src/theme/index.ts`:

```typescript
import { StyleSheet } from 'react-native';

export const colors = {
  bg: {
    primary: '#FFFFFF',
    secondary: '#F8F8FA',
  },
  text: {
    primary: '#1A1A1E',
    secondary: '#6B7280',
    placeholder: '#9CA3AF',
  },
  accent: '#10B981',
  accentLight: '#ECFDF5',
  destructive: '#EF4444',
  warning: '#F59E0B',
  border: {
    light: '#E5E7EB',
    medium: '#D1D5DB',
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
} as const;

export const radii = {
  card: 16,
  button: 12,
  chip: 999,
  input: 12,
} as const;

export const typography = {
  display: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 28 * 1.5,
  },
  title: {
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 20 * 1.5,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 16 * 1.5,
  },
  caption: {
    fontSize: 13,
    fontWeight: '400' as const,
    lineHeight: 13 * 1.5,
  },
  small: {
    fontSize: 11,
    fontWeight: '400' as const,
    lineHeight: 11 * 1.5,
  },
} as const;

// Arabic line-height multiplier (1.7x vs 1.5x for English)
export const arabicLineHeightMultiplier = 1.7 / 1.5;

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
} as const;
```

- [ ] **Step 2: Create font loading module**

Create `SmartCompareApp/src/theme/fonts.ts`:

```typescript
import {
  useFonts as useInterFonts,
  Inter_400Regular,
  Inter_600SemiBold,
  Inter_700Bold,
} from '@expo-google-fonts/inter';
import {
  useFonts as useCairoFonts,
  Cairo_400Regular,
  Cairo_600SemiBold,
  Cairo_700Bold,
} from '@expo-google-fonts/cairo';

export const fontFamily = {
  en: {
    regular: 'Inter_400Regular',
    semiBold: 'Inter_600SemiBold',
    bold: 'Inter_700Bold',
  },
  ar: {
    regular: 'Cairo_400Regular',
    semiBold: 'Cairo_600SemiBold',
    bold: 'Cairo_700Bold',
  },
} as const;

export function useAppFonts(): boolean {
  const [interLoaded] = useInterFonts({
    Inter_400Regular,
    Inter_600SemiBold,
    Inter_700Bold,
  });
  const [cairoLoaded] = useCairoFonts({
    Cairo_400Regular,
    Cairo_600SemiBold,
    Cairo_700Bold,
  });
  return interLoaded && cairoLoaded;
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Expected: No new errors from theme files.

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/theme/
git commit -m "feat: add Qaren design system (colors, typography, spacing, fonts)"
```

---

### Task 3: i18n Setup

**Files:**
- Create: `SmartCompareApp/src/i18n/index.ts`
- Create: `SmartCompareApp/src/i18n/en.json`
- Create: `SmartCompareApp/src/i18n/ar.json`
- Create: `SmartCompareApp/src/hooks/useLanguage.ts`

- [ ] **Step 1: Create i18next config**

Create `SmartCompareApp/src/i18n/index.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import * as Localization from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';
import en from './en.json';
import ar from './ar.json';

const LANGUAGE_KEY = '@qaren_language';

export async function getSavedLanguage(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(LANGUAGE_KEY);
    if (saved) return saved;
  } catch {}
  // Default: detect from device, fallback to English
  const deviceLocale = Localization.getLocales()[0]?.languageCode ?? 'en';
  return deviceLocale === 'ar' ? 'ar' : 'en';
}

export async function saveLanguage(lang: string): Promise<void> {
  await AsyncStorage.setItem(LANGUAGE_KEY, lang);
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng: 'en', // overridden at app start by getSavedLanguage()
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
```

- [ ] **Step 2: Create English translation file**

Create `SmartCompareApp/src/i18n/en.json`:

```json
{
  "app.name": "Qaren",
  "app.tagline": "Compare smarter",

  "splash.tagline": "Compare smarter",

  "onboarding.skip": "Skip",
  "onboarding.next": "Next",
  "onboarding.back": "Back",
  "onboarding.complete": "Complete",
  "onboarding.language.title": "Choose your language",
  "onboarding.language.subtitle": "",
  "onboarding.region.title": "Where are you shopping?",
  "onboarding.region.subtitle": "This helps us find local prices",
  "onboarding.region.bahrain": "Bahrain",
  "onboarding.region.saudi_arabia": "Saudi Arabia",
  "onboarding.region.uae": "UAE",
  "onboarding.region.kuwait": "Kuwait",
  "onboarding.region.qatar": "Qatar",
  "onboarding.region.oman": "Oman",
  "onboarding.priorities.title": "What matters most to you?",
  "onboarding.priorities.subtitle": "Pick 1 to 3 priorities",
  "onboarding.priorities.price": "Price",
  "onboarding.priorities.quality": "Quality",
  "onboarding.priorities.brand_reputation": "Brand Reputation",
  "onboarding.priorities.durability": "Durability",
  "onboarding.priorities.latest_features": "Latest Features",
  "onboarding.priorities.ease_of_use": "Ease of Use",
  "onboarding.priorities.eco_friendly": "Eco-Friendly",
  "onboarding.priorities.health_safety": "Health & Safety",
  "onboarding.budget.title": "How do you usually spend?",
  "onboarding.budget.subtitle": "Select your general budget level",
  "onboarding.budget.budget": "Budget",
  "onboarding.budget.budget_desc": "I look for the best deals",
  "onboarding.budget.mid": "Balanced",
  "onboarding.budget.mid_desc": "I balance price and quality",
  "onboarding.budget.premium": "Premium",
  "onboarding.budget.premium_desc": "I go for the best, price is secondary",
  "onboarding.lifestyle.title": "What describes you?",
  "onboarding.lifestyle.subtitle": "Pick any that apply",
  "onboarding.lifestyle.gamer": "Gamer",
  "onboarding.lifestyle.photographer": "Photographer",
  "onboarding.lifestyle.fitness_enthusiast": "Fitness",
  "onboarding.lifestyle.vegan": "Vegan",
  "onboarding.lifestyle.sensitive_skin": "Sensitive Skin",
  "onboarding.lifestyle.parent": "Parent",
  "onboarding.lifestyle.student": "Student",
  "onboarding.lifestyle.professional": "Professional",
  "onboarding.lifestyle.outdoor_adventurer": "Outdoor",
  "onboarding.lifestyle.minimalist": "Minimalist",
  "onboarding.lifestyle.tech_enthusiast": "Tech Enthusiast",
  "onboarding.brand.title": "Your approach to brands?",
  "onboarding.brand.subtitle": "How do you choose products?",
  "onboarding.brand.brand_loyal": "Brand Loyal",
  "onboarding.brand.brand_loyal_desc": "I stick with brands I trust",
  "onboarding.brand.function_first": "Function First",
  "onboarding.brand.function_first_desc": "Whatever works best, brand doesn't matter",
  "onboarding.brand.best_of_both": "Best of Both",
  "onboarding.brand.best_of_both_desc": "Good brands preferred, but function wins if clear",

  "home.search.placeholder": "Search products...",
  "home.categories.electronics": "Electronics",
  "home.categories.grocery": "Grocery",
  "home.categories.supplements": "Supplements",
  "home.categories.makeup": "Makeup",
  "home.categories.skincare": "Skincare",
  "home.categories.haircare": "Haircare",
  "home.categories.fragrances": "Fragrances",
  "home.categories.fashion": "Fashion",
  "home.categories.other": "Other",
  "home.scan": "Scan Product",
  "home.url": "URL",
  "home.freeCounter": "{{used}} of {{total}} free",
  "home.search.recent": "Recent",
  "home.search.trending": "Trending in {{region}}",

  "results.bestPick": "Best Pick",
  "results.verdict": "Verdict",
  "results.price": "Price",
  "results.priceLess": "{{percent}}% less",
  "results.keyDifferences": "Key Differences",
  "results.specs": "Specs",
  "results.specsShowDiff": "Show differences only",
  "results.reviews": "Reviews",
  "results.scores": "Scores",
  "results.feedback.title": "Was this helpful?",
  "results.feedback.accurate": "Accurate",
  "results.feedback.detailed": "Detailed",
  "results.feedback.fast": "Fast",
  "results.feedback.thanks": "Thanks for your feedback!",
  "results.share": "Share",
  "results.save": "Save",
  "results.loading.finding": "Finding products...",
  "results.loading.analyzing": "Analyzing specs...",
  "results.loading.prices": "Checking prices...",
  "results.loading.reviews": "Reading reviews...",
  "results.loading.scores": "Calculating scores...",
  "results.loading.done": "Here's your comparison",

  "history.title": "History",
  "history.search": "Search comparisons...",
  "history.empty.title": "Your first comparison is waiting",
  "history.empty.cta": "Start Comparing",
  "history.today": "Today",
  "history.yesterday": "Yesterday",
  "history.thisWeek": "This Week",
  "history.older": "Older",
  "history.winner": "Winner: {{name}}",
  "history.delete": "Delete",
  "history.recompare": "Compare Again",
  "history.ago": "{{time}} ago",

  "profile.title": "Profile",
  "profile.editProfile": "Edit Profile",
  "profile.settings": "Settings",
  "profile.language": "Language",
  "profile.region": "Region",
  "profile.preferences": "Preferences",
  "profile.notifications": "Notifications",
  "profile.support": "Support",
  "profile.privacy": "Privacy Policy",
  "profile.terms": "Terms of Service",
  "profile.contact": "Contact Us",
  "profile.logout": "Log Out",
  "profile.deleteAccount": "Delete Account",
  "profile.deleteConfirm": "Are you sure? This cannot be undone.",

  "auth.login": "Sign In",
  "auth.register": "Create Account",
  "auth.email": "Email",
  "auth.password": "Password",
  "auth.confirmPassword": "Confirm Password",
  "auth.displayName": "Display Name",
  "auth.forgotPassword": "Forgot Password?",
  "auth.noAccount": "Don't have an account?",
  "auth.hasAccount": "Already have an account?",
  "auth.signUp": "Sign Up",
  "auth.signIn": "Sign In",
  "auth.googleSignIn": "Continue with Google",
  "auth.appleSignIn": "Continue with Apple",
  "auth.resetPassword": "Reset Password",
  "auth.resetSent": "Password reset email sent",
  "auth.resetInstructions": "Enter your email and we'll send you a link to reset your password.",

  "paywall.title": "Unlock unlimited comparisons",
  "paywall.monthly": "Monthly",
  "paywall.yearly": "Yearly",
  "paywall.yearlySave": "-40%",
  "paywall.features.unlimited": "Unlimited comparisons",
  "paywall.features.history": "Full price history",
  "paywall.features.priority": "Priority processing",
  "paywall.features.adFree": "Ad-free experience",
  "paywall.subscribe": "Subscribe Now",
  "paywall.restore": "Restore purchase",
  "paywall.social": "Join smart shoppers across the GCC",

  "common.cancel": "Cancel",
  "common.save": "Save",
  "common.done": "Done",
  "common.error": "Something went wrong",
  "common.retry": "Try Again",
  "common.offline": "You're offline — showing cached results",
  "common.signInRequired": "Sign In Required"
}
```

- [ ] **Step 3: Create Arabic translation file**

Create `SmartCompareApp/src/i18n/ar.json`:

```json
{
  "app.name": "قارن",
  "app.tagline": "قارن بذكاء",

  "splash.tagline": "قارن بذكاء",

  "onboarding.skip": "تخطي",
  "onboarding.next": "التالي",
  "onboarding.back": "رجوع",
  "onboarding.complete": "إكمال",
  "onboarding.language.title": "اختر لغتك",
  "onboarding.language.subtitle": "",
  "onboarding.region.title": "أين تتسوق؟",
  "onboarding.region.subtitle": "يساعدنا هذا في إيجاد الأسعار المحلية",
  "onboarding.region.bahrain": "البحرين",
  "onboarding.region.saudi_arabia": "السعودية",
  "onboarding.region.uae": "الإمارات",
  "onboarding.region.kuwait": "الكويت",
  "onboarding.region.qatar": "قطر",
  "onboarding.region.oman": "عُمان",
  "onboarding.priorities.title": "ما الأهم بالنسبة لك؟",
  "onboarding.priorities.subtitle": "اختر من ١ إلى ٣ أولويات",
  "onboarding.priorities.price": "السعر",
  "onboarding.priorities.quality": "الجودة",
  "onboarding.priorities.brand_reputation": "سمعة العلامة",
  "onboarding.priorities.durability": "المتانة",
  "onboarding.priorities.latest_features": "أحدث المزايا",
  "onboarding.priorities.ease_of_use": "سهولة الاستخدام",
  "onboarding.priorities.eco_friendly": "صديق للبيئة",
  "onboarding.priorities.health_safety": "الصحة والسلامة",
  "onboarding.budget.title": "كيف تنفق عادةً؟",
  "onboarding.budget.subtitle": "اختر مستوى ميزانيتك",
  "onboarding.budget.budget": "اقتصادي",
  "onboarding.budget.budget_desc": "أبحث عن أفضل العروض",
  "onboarding.budget.mid": "متوازن",
  "onboarding.budget.mid_desc": "أوازن بين السعر والجودة",
  "onboarding.budget.premium": "مميز",
  "onboarding.budget.premium_desc": "أختار الأفضل، السعر ثانوي",
  "onboarding.lifestyle.title": "ما الذي يصفك؟",
  "onboarding.lifestyle.subtitle": "اختر ما ينطبق عليك",
  "onboarding.lifestyle.gamer": "لاعب",
  "onboarding.lifestyle.photographer": "مصور",
  "onboarding.lifestyle.fitness_enthusiast": "رياضي",
  "onboarding.lifestyle.vegan": "نباتي",
  "onboarding.lifestyle.sensitive_skin": "بشرة حساسة",
  "onboarding.lifestyle.parent": "والد/ة",
  "onboarding.lifestyle.student": "طالب",
  "onboarding.lifestyle.professional": "محترف",
  "onboarding.lifestyle.outdoor_adventurer": "مغامر",
  "onboarding.lifestyle.minimalist": "بسيط",
  "onboarding.lifestyle.tech_enthusiast": "عاشق التقنية",
  "onboarding.brand.title": "نهجك مع العلامات التجارية؟",
  "onboarding.brand.subtitle": "كيف تختار المنتجات؟",
  "onboarding.brand.brand_loyal": "وفي للعلامة",
  "onboarding.brand.brand_loyal_desc": "ألتزم بالعلامات التي أثق بها",
  "onboarding.brand.function_first": "الوظيفة أولاً",
  "onboarding.brand.function_first_desc": "الأفضل أداءً بغض النظر عن العلامة",
  "onboarding.brand.best_of_both": "الأفضل من الاثنين",
  "onboarding.brand.best_of_both_desc": "علامة جيدة مفضلة، لكن الأداء يفوز إذا كان واضحاً",

  "home.search.placeholder": "ابحث عن منتجات...",
  "home.categories.electronics": "إلكترونيات",
  "home.categories.grocery": "بقالة",
  "home.categories.supplements": "مكملات",
  "home.categories.makeup": "مكياج",
  "home.categories.skincare": "عناية بالبشرة",
  "home.categories.haircare": "عناية بالشعر",
  "home.categories.fragrances": "عطور",
  "home.categories.fashion": "أزياء",
  "home.categories.other": "أخرى",
  "home.scan": "مسح المنتج",
  "home.url": "رابط",
  "home.freeCounter": "{{used}} من {{total}} مجاناً",
  "home.search.recent": "الأخيرة",
  "home.search.trending": "الرائج في {{region}}",

  "results.bestPick": "الأفضل",
  "results.verdict": "الحكم",
  "results.price": "السعر",
  "results.priceLess": "أقل بـ {{percent}}%",
  "results.keyDifferences": "الفروقات الرئيسية",
  "results.specs": "المواصفات",
  "results.specsShowDiff": "عرض الاختلافات فقط",
  "results.reviews": "التقييمات",
  "results.scores": "النتائج",
  "results.feedback.title": "هل كان هذا مفيداً؟",
  "results.feedback.accurate": "دقيق",
  "results.feedback.detailed": "مفصّل",
  "results.feedback.fast": "سريع",
  "results.feedback.thanks": "شكراً على ملاحظاتك!",
  "results.share": "مشاركة",
  "results.save": "حفظ",
  "results.loading.finding": "جاري البحث عن المنتجات...",
  "results.loading.analyzing": "جاري تحليل المواصفات...",
  "results.loading.prices": "جاري فحص الأسعار...",
  "results.loading.reviews": "جاري قراءة التقييمات...",
  "results.loading.scores": "جاري حساب النتائج...",
  "results.loading.done": "هذه مقارنتك",

  "history.title": "السجل",
  "history.search": "البحث في المقارنات...",
  "history.empty.title": "مقارنتك الأولى بانتظارك",
  "history.empty.cta": "ابدأ المقارنة",
  "history.today": "اليوم",
  "history.yesterday": "أمس",
  "history.thisWeek": "هذا الأسبوع",
  "history.older": "أقدم",
  "history.winner": "الفائز: {{name}}",
  "history.delete": "حذف",
  "history.recompare": "قارن مرة أخرى",
  "history.ago": "منذ {{time}}",

  "profile.title": "الملف الشخصي",
  "profile.editProfile": "تعديل الملف",
  "profile.settings": "الإعدادات",
  "profile.language": "اللغة",
  "profile.region": "المنطقة",
  "profile.preferences": "التفضيلات",
  "profile.notifications": "الإشعارات",
  "profile.support": "الدعم",
  "profile.privacy": "سياسة الخصوصية",
  "profile.terms": "شروط الاستخدام",
  "profile.contact": "اتصل بنا",
  "profile.logout": "تسجيل الخروج",
  "profile.deleteAccount": "حذف الحساب",
  "profile.deleteConfirm": "هل أنت متأكد؟ لا يمكن التراجع عن هذا.",

  "auth.login": "تسجيل الدخول",
  "auth.register": "إنشاء حساب",
  "auth.email": "البريد الإلكتروني",
  "auth.password": "كلمة المرور",
  "auth.confirmPassword": "تأكيد كلمة المرور",
  "auth.displayName": "الاسم",
  "auth.forgotPassword": "نسيت كلمة المرور؟",
  "auth.noAccount": "ليس لديك حساب؟",
  "auth.hasAccount": "لديك حساب بالفعل؟",
  "auth.signUp": "تسجيل",
  "auth.signIn": "دخول",
  "auth.googleSignIn": "المتابعة مع Google",
  "auth.appleSignIn": "المتابعة مع Apple",
  "auth.resetPassword": "إعادة تعيين كلمة المرور",
  "auth.resetSent": "تم إرسال رابط إعادة التعيين",
  "auth.resetInstructions": "أدخل بريدك الإلكتروني وسنرسل لك رابطاً لإعادة تعيين كلمة المرور.",

  "paywall.title": "افتح المقارنات غير المحدودة",
  "paywall.monthly": "شهري",
  "paywall.yearly": "سنوي",
  "paywall.yearlySave": "-٤٠%",
  "paywall.features.unlimited": "مقارنات غير محدودة",
  "paywall.features.history": "سجل أسعار كامل",
  "paywall.features.priority": "معالجة ذات أولوية",
  "paywall.features.adFree": "بدون إعلانات",
  "paywall.subscribe": "اشترك الآن",
  "paywall.restore": "استعادة الاشتراك",
  "paywall.social": "انضم إلى المتسوقين الأذكياء في الخليج",

  "common.cancel": "إلغاء",
  "common.save": "حفظ",
  "common.done": "تم",
  "common.error": "حدث خطأ ما",
  "common.retry": "حاول مرة أخرى",
  "common.offline": "أنت غير متصل — عرض النتائج المحفوظة",
  "common.signInRequired": "يجب تسجيل الدخول"
}
```

- [ ] **Step 4: Create language switching hook**

Create `SmartCompareApp/src/hooks/useLanguage.ts`:

```typescript
import { useCallback } from 'react';
import { I18nManager } from 'react-native';
import { useTranslation } from 'react-i18next';
import * as Updates from 'expo-updates';
import { saveLanguage } from '../i18n';

export function useLanguage() {
  const { i18n } = useTranslation();
  const isRTL = i18n.language === 'ar';

  const switchLanguage = useCallback(async (lang: 'en' | 'ar') => {
    if (lang === i18n.language) return;

    await saveLanguage(lang);
    await i18n.changeLanguage(lang);

    const shouldBeRTL = lang === 'ar';
    if (I18nManager.isRTL !== shouldBeRTL) {
      I18nManager.allowRTL(true);
      I18nManager.forceRTL(shouldBeRTL);
      // App restart required for RTL to take effect
      try {
        await Updates.reloadAsync();
      } catch {
        // In dev, Updates.reloadAsync may not work — user must restart manually
      }
    }
  }, [i18n]);

  return { language: i18n.language as 'en' | 'ar', isRTL, switchLanguage };
}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add SmartCompareApp/src/i18n/ SmartCompareApp/src/hooks/useLanguage.ts
git commit -m "feat: add i18n system (i18next, EN+AR translations, RTL language hook)"
```

---

### Task 4: Rename Storage Keys & Update Types

**Files:**
- Modify: `SmartCompareApp/src/services/authService.ts`
- Modify: `SmartCompareApp/src/services/api.ts`
- Modify: `SmartCompareApp/src/types/types.ts`

- [ ] **Step 1: Rename storage keys in authService.ts**

In `SmartCompareApp/src/services/authService.ts`, find and replace all occurrences:
```
@smartcompare_user    → @qaren_user
@smartcompare_token   → @qaren_token
@smartcompare_refresh_token → @qaren_refresh_token
```

These are the `USER_STORAGE_KEY`, `TOKEN_STORAGE_KEY`, and `REFRESH_TOKEN_KEY` constants near the top of the file.

- [ ] **Step 2: Check api.ts for any smartcompare references**

Search `SmartCompareApp/src/services/api.ts` for `smartcompare` and rename any storage key references to `@qaren_*`.

- [ ] **Step 3: Add new types**

In `SmartCompareApp/src/types/types.ts`, add at the bottom before any closing export:

```typescript
// Onboarding types
export interface OnboardingData {
  language: 'en' | 'ar';
  region: 'bahrain' | 'saudi_arabia' | 'uae' | 'kuwait' | 'qatar' | 'oman';
  priorities: string[];
  budget: 'budget' | 'mid' | 'premium';
  lifestyle: string[];
  brand_attitude: 'brand_loyal' | 'function_first' | 'best_of_both';
}

// Navigation types update
export type MainTabParamList = {
  HomeTab: undefined;
  HistoryTab: undefined;
  ProfileTab: undefined;
};
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/services/ SmartCompareApp/src/types/
git commit -m "refactor: rename storage keys smartcompare→qaren, add onboarding types"
```

---

### Task 5: RTL Utility + Design System Components

**Files:**
- Create: `SmartCompareApp/src/utils/rtl.ts`
- Create: `SmartCompareApp/src/components/Button.tsx`
- Create: `SmartCompareApp/src/components/Card.tsx`
- Create: `SmartCompareApp/src/components/Chip.tsx`
- Create: `SmartCompareApp/src/components/SkeletonLoader.tsx`
- Create: `SmartCompareApp/src/components/ProgressBar.tsx`
- Create: `SmartCompareApp/src/components/IconButton.tsx`
- Create: `SmartCompareApp/src/components/ComparisonCounter.tsx`

- [ ] **Step 1: Create RTL utility**

Create `SmartCompareApp/src/utils/rtl.ts`:

```typescript
import { I18nManager } from 'react-native';

/**
 * Returns scaleX transform for icons that should flip in RTL.
 * Only use for directional icons: arrows, chevrons, send, share.
 * Do NOT use for: search, camera, star, heart, trash, settings, check.
 */
export function rtlFlip(): { transform: { scaleX: number }[] } {
  return { transform: [{ scaleX: I18nManager.isRTL ? -1 : 1 }] };
}

/** Returns 'rtl' or 'ltr' for writingDirection style prop. */
export function writingDirection(): 'rtl' | 'ltr' {
  return I18nManager.isRTL ? 'rtl' : 'ltr';
}
```

- [ ] **Step 2: Create Button component**

Create `SmartCompareApp/src/components/Button.tsx`:

```typescript
import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, spacing, radii, typography } from '../theme';

type ButtonVariant = 'primary' | 'secondary' | 'destructive';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  style,
}: ButtonProps) {
  const buttonStyle = [
    styles.base,
    styles[variant],
    disabled && styles.disabled,
    style,
  ];

  const textStyle: TextStyle[] = [
    styles.text,
    variant === 'secondary' && styles.textSecondary,
    variant === 'destructive' && styles.textDestructive,
  ];

  return (
    <TouchableOpacity
      style={buttonStyle}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'primary' ? '#FFFFFF' : colors.accent}
        />
      ) : (
        <Text style={textStyle}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  primary: {
    backgroundColor: colors.accent,
  },
  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.border.medium,
  },
  destructive: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.destructive,
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    ...typography.body,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  textSecondary: {
    color: colors.text.primary,
  },
  textDestructive: {
    color: colors.destructive,
  },
});
```

- [ ] **Step 3: Create Card component**

Create `SmartCompareApp/src/components/Card.tsx`:

```typescript
import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, radii, shadows } from '../theme';

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'winner';
  style?: ViewStyle;
}

export function Card({ children, variant = 'default', style }: CardProps) {
  return (
    <View
      style={[
        styles.base,
        variant === 'winner' && styles.winner,
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
    ...shadows.card,
  },
  winner: {
    borderColor: colors.accent,
    borderWidth: 2,
    backgroundColor: colors.accentLight,
  },
});
```

- [ ] **Step 4: Create Chip component**

Create `SmartCompareApp/src/components/Chip.tsx`:

```typescript
import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors, spacing, radii, typography } from '../theme';

interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  disabled?: boolean;
}

export function Chip({ label, selected = false, onPress, disabled = false }: ChipProps) {
  return (
    <TouchableOpacity
      style={[styles.chip, selected && styles.chipSelected]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
    >
      <Text style={[styles.text, selected && styles.textSelected]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.base,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  chipSelected: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  text: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  textSelected: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
});
```

- [ ] **Step 5: Create SkeletonLoader component**

Create `SmartCompareApp/src/components/SkeletonLoader.tsx`:

```typescript
import React, { useEffect } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors, radii } from '../theme';

interface SkeletonLoaderProps {
  width: number | string;
  height: number;
  borderRadius?: number;
  style?: ViewStyle;
}

export function SkeletonLoader({
  width,
  height,
  borderRadius = radii.card,
  style,
}: SkeletonLoaderProps) {
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(
      withTiming(0.7, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
      -1,
      true
    );
  }, [opacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  return (
    <Animated.View
      style={[
        {
          width: width as number,
          height,
          borderRadius,
          backgroundColor: colors.border.light,
        },
        animatedStyle,
        style,
      ]}
    />
  );
}
```

- [ ] **Step 6: Create ProgressBar component**

Create `SmartCompareApp/src/components/ProgressBar.tsx`:

```typescript
import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing } from '../theme';

interface ProgressBarProps {
  progress: number; // 0-1
}

export function ProgressBar({ progress }: ProgressBarProps) {
  const animatedWidth = useSharedValue(0);

  useEffect(() => {
    animatedWidth.value = withTiming(progress, {
      duration: 600,
      easing: Easing.out(Easing.cubic),
    });
  }, [progress, animatedWidth]);

  const fillStyle = useAnimatedStyle(() => ({
    width: `${animatedWidth.value * 100}%`,
  }));

  return (
    <View style={styles.track}>
      <Animated.View style={[styles.fill, fillStyle]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: 4,
    backgroundColor: colors.border.light,
    borderRadius: 2,
    overflow: 'hidden',
  },
  fill: {
    height: 4,
    backgroundColor: colors.accent,
    borderRadius: 2,
  },
});
```

- [ ] **Step 7: Create IconButton component**

Create `SmartCompareApp/src/components/IconButton.tsx`:

```typescript
import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing } from '../theme';
import { rtlFlip } from '../utils/rtl';

interface IconButtonProps {
  icon: React.ReactNode;
  onPress: () => void;
  directional?: boolean; // true = flip in RTL (arrows, chevrons)
  style?: ViewStyle;
}

export function IconButton({
  icon,
  onPress,
  directional = false,
  style,
}: IconButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, directional && rtlFlip(), style]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      {icon}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    padding: spacing.sm,
    borderRadius: 999,
  },
});
```

- [ ] **Step 8: Create ComparisonCounter component**

Create `SmartCompareApp/src/components/ComparisonCounter.tsx`:

```typescript
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';

interface ComparisonCounterProps {
  used: number;
  total: number;
}

export function ComparisonCounter({ used, total }: ComparisonCounterProps) {
  const { t } = useTranslation();
  if (used === 0) return null;

  const isWarning = used >= total - 1; // Last free or exhausted

  return (
    <View style={[styles.pill, isWarning && styles.pillWarning]}>
      <Text style={[styles.text, isWarning && styles.textWarning]}>
        {t('home.freeCounter', { used, total })}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignSelf: 'flex-start',
  },
  pillWarning: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  text: {
    ...typography.small,
    color: colors.text.secondary,
  },
  textWarning: {
    color: colors.accent,
    fontWeight: '600',
  },
});
```

- [ ] **Step 9: Create comparison counter hook**

Create `SmartCompareApp/src/hooks/useComparisonCounter.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const COUNTER_KEY = '@qaren_free_comparisons_used';
const FREE_LIMIT = 3;

export function useComparisonCounter() {
  const [used, setUsed] = useState(0);

  useEffect(() => {
    AsyncStorage.getItem(COUNTER_KEY).then((val) => {
      if (val) setUsed(parseInt(val, 10));
    });
  }, []);

  const increment = useCallback(async () => {
    const newCount = used + 1;
    setUsed(newCount);
    await AsyncStorage.setItem(COUNTER_KEY, String(newCount));
    return newCount;
  }, [used]);

  const canCompare = used < FREE_LIMIT;
  const shouldShowPaywall = used >= FREE_LIMIT;

  return { used, total: FREE_LIMIT, canCompare, shouldShowPaywall, increment };
}
```

- [ ] **Step 10: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 11: Commit**

```bash
git add SmartCompareApp/src/utils/ SmartCompareApp/src/components/Button.tsx SmartCompareApp/src/components/Card.tsx SmartCompareApp/src/components/Chip.tsx SmartCompareApp/src/components/SkeletonLoader.tsx SmartCompareApp/src/components/ProgressBar.tsx SmartCompareApp/src/components/IconButton.tsx SmartCompareApp/src/components/ComparisonCounter.tsx SmartCompareApp/src/hooks/useComparisonCounter.ts
git commit -m "feat: add Qaren design system components (Button, Card, Chip, Skeleton, Progress, Counter)"
```

---

## Phase 2: Screens (Tasks 6–15)

### Task 6: SplashScreen

**Files:**
- Create: `SmartCompareApp/src/screens/SplashScreen.tsx`

- [ ] **Step 1: Create SplashScreen**

Create `SmartCompareApp/src/screens/SplashScreen.tsx`:

```typescript
import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  withSequence,
  Easing,
  runOnJS,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { colors, typography, spacing } from '../theme';

interface SplashScreenProps {
  onFinish: () => void;
}

export default function SplashScreen({ onFinish }: SplashScreenProps) {
  const { t } = useTranslation();
  const logoOpacity = useSharedValue(0);
  const logoScale = useSharedValue(0.8);
  const taglineOpacity = useSharedValue(0);

  useEffect(() => {
    // Logo fades in + scales up
    logoOpacity.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });
    logoScale.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.ease) });

    // Tagline fades in after 200ms
    taglineOpacity.value = withDelay(200, withTiming(1, { duration: 400 }));

    // After 1.5s total, trigger onFinish
    const timer = setTimeout(onFinish, 1500);
    return () => clearTimeout(timer);
  }, [logoOpacity, logoScale, taglineOpacity, onFinish]);

  const logoStyle = useAnimatedStyle(() => ({
    opacity: logoOpacity.value,
    transform: [{ scale: logoScale.value }],
  }));

  const taglineStyle = useAnimatedStyle(() => ({
    opacity: taglineOpacity.value,
  }));

  return (
    <View style={styles.container}>
      <Animated.Text style={[styles.logo, logoStyle]}>قارن</Animated.Text>
      <Animated.Text style={[styles.tagline, taglineStyle]}>
        {t('splash.tagline')}
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    fontSize: 48,
    fontWeight: '700',
    color: colors.text.primary,
  },
  tagline: {
    ...typography.body,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },
});
```

- [ ] **Step 2: Commit**

```bash
git add SmartCompareApp/src/screens/SplashScreen.tsx
git commit -m "feat: add SplashScreen with logo animation"
```

---

### Task 7: OnboardingScreen

**Files:**
- Create: `SmartCompareApp/src/screens/OnboardingScreen.tsx`

- [ ] **Step 1: Create OnboardingScreen**

Create `SmartCompareApp/src/screens/OnboardingScreen.tsx`. This is a large file (~350 lines) — the 6-step wizard. Key structure:

```typescript
import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ProgressBar } from '../components/ProgressBar';
import { useLanguage } from '../hooks/useLanguage';
import { savePreferences } from '../services/api';
import { RootStackParamList, OnboardingData } from '../types';

const TOTAL_STEPS = 6;

const REGIONS = [
  { value: 'bahrain', flag: '🇧🇭' },
  { value: 'saudi_arabia', flag: '🇸🇦' },
  { value: 'uae', flag: '🇦🇪' },
  { value: 'kuwait', flag: '🇰🇼' },
  { value: 'qatar', flag: '🇶🇦' },
  { value: 'oman', flag: '🇴🇲' },
] as const;

const PRIORITY_OPTIONS = [
  'price', 'quality', 'brand_reputation', 'durability',
  'latest_features', 'ease_of_use', 'eco_friendly', 'health_safety',
] as const;

const BUDGET_OPTIONS = ['budget', 'mid', 'premium'] as const;

const LIFESTYLE_OPTIONS = [
  'gamer', 'photographer', 'fitness_enthusiast', 'vegan', 'sensitive_skin',
  'parent', 'student', 'professional', 'outdoor_adventurer', 'minimalist', 'tech_enthusiast',
] as const;

const BRAND_OPTIONS = ['brand_loyal', 'function_first', 'best_of_both'] as const;

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Onboarding'>;
  onComplete?: () => void;
};

export default function OnboardingScreen({ navigation, onComplete }: Props) {
  const { t } = useTranslation();
  const { language, switchLanguage } = useLanguage();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  // Onboarding data
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'ar'>(language);
  const [region, setRegion] = useState<string>('');
  const [priorities, setPriorities] = useState<string[]>([]);
  const [budget, setBudget] = useState<string>('');
  const [lifestyle, setLifestyle] = useState<string[]>([]);
  const [brandAttitude, setBrandAttitude] = useState<string>('');

  const progress = (step + 1) / TOTAL_STEPS;

  const isStepValid = (): boolean => {
    switch (step) {
      case 0: return true; // language always has a default
      case 1: return region !== '';
      case 2: return priorities.length >= 1 && priorities.length <= 3;
      case 3: return budget !== '';
      case 4: return true; // lifestyle is optional
      case 5: return brandAttitude !== '';
      default: return false;
    }
  };

  const toggleChip = (
    value: string,
    selected: string[],
    setter: (v: string[]) => void,
    maxCount?: number,
  ) => {
    if (selected.includes(value)) {
      setter(selected.filter((v) => v !== value));
    } else if (!maxCount || selected.length < maxCount) {
      setter([...selected, value]);
    }
  };

  const handleNext = async () => {
    if (step === 0 && selectedLanguage !== language) {
      // Language changed — this will restart the app
      await switchLanguage(selectedLanguage);
      return;
    }
    if (step < TOTAL_STEPS - 1) {
      setStep(step + 1);
    } else {
      // Complete onboarding
      setSaving(true);
      try {
        await savePreferences({
          priorities,
          budget: budget as any,
          lifestyle,
          brand_attitude: brandAttitude as any,
        });
        if (onComplete) onComplete();
      } catch (err: any) {
        // Silently fail — preferences can be set later
        if (onComplete) onComplete();
      } finally {
        setSaving(false);
      }
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.language.title')}</Text>
            <View style={styles.optionList}>
              {(['en', 'ar'] as const).map((lang) => (
                <TouchableOpacity
                  key={lang}
                  style={[styles.radioCard, selectedLanguage === lang && styles.radioCardActive]}
                  onPress={() => setSelectedLanguage(lang)}
                >
                  <Text style={[styles.radioLabel, selectedLanguage === lang && styles.radioLabelActive]}>
                    {lang === 'en' ? 'English' : 'العربية'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 1:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.region.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.region.subtitle')}</Text>
            <View style={styles.optionList}>
              {REGIONS.map((r) => (
                <TouchableOpacity
                  key={r.value}
                  style={[styles.radioCard, region === r.value && styles.radioCardActive]}
                  onPress={() => setRegion(r.value)}
                >
                  <Text style={styles.radioFlag}>{r.flag}</Text>
                  <Text style={[styles.radioLabel, region === r.value && styles.radioLabelActive]}>
                    {t(`onboarding.region.${r.value}`)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 2:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.priorities.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.priorities.subtitle')}</Text>
            <View style={styles.chipGrid}>
              {PRIORITY_OPTIONS.map((opt) => (
                <Chip
                  key={opt}
                  label={t(`onboarding.priorities.${opt}`)}
                  selected={priorities.includes(opt)}
                  onPress={() => toggleChip(opt, priorities, setPriorities, 3)}
                />
              ))}
            </View>
          </View>
        );
      case 3:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.budget.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.budget.subtitle')}</Text>
            <View style={styles.optionList}>
              {BUDGET_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[styles.radioCard, budget === opt && styles.radioCardActive]}
                  onPress={() => setBudget(opt)}
                >
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, budget === opt && styles.radioLabelActive]}>
                      {t(`onboarding.budget.${opt}`)}
                    </Text>
                    <Text style={styles.radioDesc}>{t(`onboarding.budget.${opt}_desc`)}</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 4:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.lifestyle.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.lifestyle.subtitle')}</Text>
            <View style={styles.chipGrid}>
              {LIFESTYLE_OPTIONS.map((opt) => (
                <Chip
                  key={opt}
                  label={t(`onboarding.lifestyle.${opt}`)}
                  selected={lifestyle.includes(opt)}
                  onPress={() => toggleChip(opt, lifestyle, setLifestyle)}
                />
              ))}
            </View>
          </View>
        );
      case 5:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.brand.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.brand.subtitle')}</Text>
            <View style={styles.optionList}>
              {BRAND_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[styles.radioCard, brandAttitude === opt && styles.radioCardActive]}
                  onPress={() => setBrandAttitude(opt)}
                >
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, brandAttitude === opt && styles.radioLabelActive]}>
                      {t(`onboarding.brand.${opt}`)}
                    </Text>
                    <Text style={styles.radioDesc}>{t(`onboarding.brand.${opt}_desc`)}</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      default:
        return null;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <ProgressBar progress={progress} />
      </View>
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {renderStep()}
      </ScrollView>
      <View style={styles.footer}>
        {step > 0 ? (
          <TouchableOpacity onPress={handleBack}>
            <Text style={styles.backText}>{t('onboarding.back')}</Text>
          </TouchableOpacity>
        ) : (
          <View />
        )}
        <Button
          title={step === TOTAL_STEPS - 1 ? t('onboarding.complete') : t('onboarding.next')}
          onPress={handleNext}
          disabled={!isStepValid()}
          loading={saving}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.base },
  content: { flex: 1 },
  contentInner: { padding: spacing.lg, paddingTop: spacing['2xl'] },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.base,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
  },
  title: { ...typography.display, color: colors.text.primary, marginBottom: spacing.sm },
  subtitle: { ...typography.body, color: colors.text.secondary, marginBottom: spacing.xl },
  chipGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  optionList: { gap: spacing.md },
  radioCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  radioCardActive: { borderColor: colors.accent, backgroundColor: colors.accentLight },
  radioFlag: { fontSize: 24, marginEnd: spacing.md },
  radioContent: { flex: 1 },
  radioLabel: { ...typography.body, fontWeight: '600', color: colors.text.primary },
  radioLabelActive: { color: colors.accent },
  radioDesc: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
  backText: { ...typography.body, color: colors.accent, fontWeight: '500' },
});
```

- [ ] **Step 2: Commit**

```bash
git add SmartCompareApp/src/screens/OnboardingScreen.tsx
git commit -m "feat: add OnboardingScreen (6-step wizard with i18n)"
```

---

### Task 8: Auth Screens (Login, Register, ForgotPassword)

**Files:**
- Rewrite: `SmartCompareApp/src/screens/LoginScreen.tsx`
- Rewrite: `SmartCompareApp/src/screens/RegisterScreen.tsx`
- Rewrite: `SmartCompareApp/src/screens/ForgotPasswordScreen.tsx`

These screens keep their existing logic (authService calls, validation, social login) but get restyled with theme tokens and i18n strings. The agent implementing this task should:

- [ ] **Step 1: Rewrite LoginScreen.tsx**

Keep all existing auth logic (email/password validation, `login()` call, `signInWithGoogle()`, `signInWithApple()`, error handling). Replace:
- All hardcoded strings with `t('auth.*')` calls
- All color values with `colors.*` theme tokens
- All font sizes with `typography.*`
- All spacing with `spacing.*`
- All border radius with `radii.*`
- Primary button: use `<Button variant="primary">` component
- Social login buttons: use `<Button variant="secondary">`
- Replace `#007AFF` with `colors.accent` everywhere
- Use `marginStart`/`marginEnd` instead of `marginLeft`/`marginRight`

- [ ] **Step 2: Rewrite RegisterScreen.tsx**

Same approach as LoginScreen. Keep validation logic (10+ chars, 1 upper, 1 lower, 1 digit), `register()` call, social auth. Restyle with theme + i18n.

- [ ] **Step 3: Rewrite ForgotPasswordScreen.tsx**

Keep `resetPassword()` call and success state. Restyle with theme + i18n.

- [ ] **Step 4: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/screens/LoginScreen.tsx SmartCompareApp/src/screens/RegisterScreen.tsx SmartCompareApp/src/screens/ForgotPasswordScreen.tsx
git commit -m "feat: restyle auth screens with Qaren design system + i18n"
```

---

### Task 9: HomeScreen (Camera-First)

**Files:**
- Rewrite: `SmartCompareApp/src/screens/HomeScreen.tsx`
- Create: `SmartCompareApp/src/components/SearchOverlay.tsx`
- Restyle: `SmartCompareApp/src/components/CategorySelector.tsx`

This is the biggest screen change. The camera code from the old CameraScreen.tsx must be absorbed into HomeScreen. The agent should:

- [ ] **Step 1: Read existing CameraScreen.tsx and HomeScreen.tsx**

Read both files completely to understand the camera capture logic (expo-camera, permissions, multi-product capture, JPEG transcoding, identifyFromImages API call) and the current home screen logic (category selection, text input, URL input, SSE streaming trigger).

- [ ] **Step 2: Create SearchOverlay component**

Create `SmartCompareApp/src/components/SearchOverlay.tsx` — a full-screen overlay that slides up when search bar is tapped. Contains:
- Back button + search input (auto-focus)
- Recent comparisons section (from AsyncStorage or history API)
- Trending section (hardcoded for now, can be API-driven later)
- On submit: navigate to comparison flow

```typescript
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  FlatList,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { ArrowLeft, Search } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';
import { rtlFlip } from '../utils/rtl';

interface SearchOverlayProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (query: string) => void;
  recentSearches: string[];
}

export function SearchOverlay({ visible, onClose, onSubmit, recentSearches }: SearchOverlayProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
    }
  }, [visible]);

  if (!visible) return null;

  const handleSubmit = () => {
    const trimmed = query.trim();
    if (trimmed) onSubmit(trimmed);
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.inner}
      >
        <View style={styles.searchRow}>
          <TouchableOpacity onPress={onClose} style={rtlFlip()}>
            <ArrowLeft size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <View style={styles.inputWrapper}>
            <Search size={18} color={colors.text.placeholder} />
            <TextInput
              ref={inputRef}
              style={styles.input}
              placeholder={t('home.search.placeholder')}
              placeholderTextColor={colors.text.placeholder}
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={handleSubmit}
              returnKeyType="search"
              autoCorrect={false}
            />
          </View>
        </View>

        {recentSearches.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t('home.search.recent')}</Text>
            {recentSearches.slice(0, 5).map((search, i) => (
              <TouchableOpacity
                key={i}
                style={styles.searchItem}
                onPress={() => onSubmit(search)}
              >
                <Text style={styles.searchItemText}>{search}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  inner: { flex: 1 },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  inputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.text.primary,
    paddingVertical: spacing.md,
    textAlign: 'auto',
  },
  section: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg },
  sectionTitle: { ...typography.caption, color: colors.text.secondary, fontWeight: '600', marginBottom: spacing.sm },
  searchItem: { paddingVertical: spacing.md },
  searchItemText: { ...typography.body, color: colors.text.primary },
});
```

- [ ] **Step 3: Restyle CategorySelector with theme + i18n**

Rewrite `SmartCompareApp/src/components/CategorySelector.tsx` to use theme tokens and i18n strings. Replace hardcoded colors/spacing. Use `t('home.categories.*')` for labels.

- [ ] **Step 4: Rewrite HomeScreen.tsx**

The new HomeScreen combines:
- Camera viewfinder from CameraScreen (expo-camera, permissions, capture)
- Category chips (CategorySelector)
- Search bar (tapping opens SearchOverlay)
- Comparison counter pill
- Input modes: "Scan Product" (camera capture) and "URL" (text input for URL)
- SSE streaming trigger on capture or search submit

Key integration points:
- Camera: `CameraView` from expo-camera with capture → `identifyFromImages()` API call → navigate to Results
- Search: submit → `streamComparison()` or `compareText()` → navigate to Results
- Counter: `useComparisonCounter()` — check `canCompare` before allowing comparison

- [ ] **Step 5: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add SmartCompareApp/src/screens/HomeScreen.tsx SmartCompareApp/src/components/SearchOverlay.tsx SmartCompareApp/src/components/CategorySelector.tsx
git commit -m "feat: camera-first HomeScreen with search overlay and comparison counter"
```

---

### Task 10: ResultsScreen (Single Scroll)

**Files:**
- Rewrite: `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Restyle: `SmartCompareApp/src/components/FeedbackCard.tsx`

The current ResultsScreen is 1,533 lines with 3 tabs. The new version is a single scroll. The agent should:

- [ ] **Step 1: Read existing ResultsScreen.tsx completely**

Understand all data rendering: product cards, specs table, reviews, scoring, feedback, event tracking, share functionality. All this logic stays — only the layout changes from tabs to single scroll.

- [ ] **Step 2: Restyle FeedbackCard with theme + i18n**

Replace hardcoded strings and styles in FeedbackCard.tsx with theme tokens and `t()` calls.

- [ ] **Step 3: Rewrite ResultsScreen.tsx as single scroll**

Structure (top to bottom in one ScrollView):
1. **Header**: Back button + query title + share icon
2. **Product cards**: Two side-by-side `<Card>` components with image, name, price, rating. Winner card uses `variant="winner"` with "Best Pick" badge.
3. **Verdict section**: One-line AI verdict text
4. **Price comparison**: Both prices, retailer attribution, "X% less" emerald badge on cheaper product
5. **Key differences**: Icon + label per dimension showing winner
6. **Specs accordion**: Collapsible sections by category, winner dots, "Show differences only" toggle
7. **Reviews**: Quote cards with source attribution and star ratings
8. **Score breakdown**: Horizontal bar chart for 6 scoring dimensions
9. **Feedback**: `<FeedbackCard>`
10. **Actions**: Share + Save buttons

Keep all existing:
- SSE streaming handling (skeleton → progressive reveal)
- Event tracking (`trackEvents()`)
- Share functionality (`createShareLink()`)
- Navigation back behavior

Add new:
- Skeleton loading sequence with `<SkeletonLoader>` and `<ProgressBar>`
- Winner reveal animation (emerald border + haptic via `expo-haptics`)
- Loading status messages from `t('results.loading.*')`

- [ ] **Step 4: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx SmartCompareApp/src/components/FeedbackCard.tsx
git commit -m "feat: single-scroll ResultsScreen with skeleton loading and winner reveal"
```

---

### Task 11: HistoryScreen

**Files:**
- Rewrite: `SmartCompareApp/src/screens/HistoryScreen.tsx`

- [ ] **Step 1: Read existing HistoryScreen.tsx**

Understand: pagination, search, delete, re-compare, 401 handling, modal. All logic stays.

- [ ] **Step 2: Rewrite HistoryScreen.tsx**

Changes:
- Replace ScrollView + .map with FlatList (virtualized)
- Group items by date (Today, Yesterday, This Week, Older) using section headers
- Staggered fade-in entrance animation via `Animated.FlatList` with `entering` prop from reanimated
- Empty state with illustration + CTA button
- Restyle with theme tokens + i18n strings
- Use `marginStart`/`marginEnd` throughout

- [ ] **Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/HistoryScreen.tsx
git commit -m "feat: restyle HistoryScreen with FlatList, date grouping, staggered animation"
```

---

### Task 12: ProfileScreen

**Files:**
- Create: `SmartCompareApp/src/screens/ProfileScreen.tsx`
- Delete: `SmartCompareApp/src/screens/AccountScreen.tsx`

- [ ] **Step 1: Read existing AccountScreen.tsx**

Understand: profile display, edit name, change password, change email, preferences link, delete account, logout. All logic stays.

- [ ] **Step 2: Create ProfileScreen.tsx**

New layout in grouped cards (see wireframe in spec). Include:
- Account card: name, email, edit link
- Settings card: language toggle (calls `useLanguage().switchLanguage()`), region picker, preferences link, notifications toggle
- Support card: Privacy Policy, Terms of Service, Contact Us (links to legal routes)
- Danger card: Log Out, Delete Account (red text, confirmation alert)

Use all theme tokens, i18n strings, `marginStart`/`marginEnd`.

- [ ] **Step 3: Delete old AccountScreen**

```bash
rm SmartCompareApp/src/screens/AccountScreen.tsx
```

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/ProfileScreen.tsx
git rm SmartCompareApp/src/screens/AccountScreen.tsx
git commit -m "feat: add ProfileScreen, delete old AccountScreen"
```

---

### Task 13: PaywallScreen

**Files:**
- Create: `SmartCompareApp/src/screens/PaywallScreen.tsx`

- [ ] **Step 1: Create PaywallScreen**

Bottom sheet overlay with frosted glass effect. This is a placeholder — no actual subscription logic.

```typescript
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Modal } from 'react-native';
import { BlurView } from 'expo-blur'; // Already available via Expo
import { useTranslation } from 'react-i18next';
import { Check } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { Button } from '../components/Button';

interface PaywallScreenProps {
  visible: boolean;
  onDismiss: () => void;
}

export default function PaywallScreen({ visible, onDismiss }: PaywallScreenProps) {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<'monthly' | 'yearly'>('yearly');

  const features = [
    t('paywall.features.unlimited'),
    t('paywall.features.history'),
    t('paywall.features.priority'),
    t('paywall.features.adFree'),
  ];

  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <TouchableOpacity style={styles.backdrop} onPress={onDismiss} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <Text style={styles.title}>{t('paywall.title')}</Text>

          <View style={styles.planRow}>
            <TouchableOpacity
              style={[styles.planCard, plan === 'monthly' && styles.planCardActive]}
              onPress={() => setPlan('monthly')}
            >
              <Text style={styles.planLabel}>{t('paywall.monthly')}</Text>
              <Text style={styles.planPrice}>$4.99</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.planCard, plan === 'yearly' && styles.planCardActive]}
              onPress={() => setPlan('yearly')}
            >
              <View style={styles.saveBadge}>
                <Text style={styles.saveBadgeText}>{t('paywall.yearlySave')}</Text>
              </View>
              <Text style={styles.planLabel}>{t('paywall.yearly')}</Text>
              <Text style={styles.planPrice}>$2.99/mo</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.features}>
            {features.map((f, i) => (
              <View key={i} style={styles.featureRow}>
                <Check size={18} color={colors.accent} />
                <Text style={styles.featureText}>{f}</Text>
              </View>
            ))}
          </View>

          <Button title={t('paywall.subscribe')} onPress={() => {/* TODO: actual subscription */}} />

          <TouchableOpacity style={styles.restoreButton}>
            <Text style={styles.restoreText}>{t('paywall.restore')}</Text>
          </TouchableOpacity>

          <Text style={styles.social}>{t('paywall.social')}</Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { flex: 1 },
  sheet: {
    backgroundColor: colors.bg.primary,
    borderTopStartRadius: spacing.xl,
    borderTopEndRadius: spacing.xl,
    padding: spacing.lg,
    paddingBottom: spacing['3xl'],
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: spacing.lg,
  },
  title: { ...typography.title, color: colors.text.primary, textAlign: 'center', marginBottom: spacing.xl },
  planRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.xl },
  planCard: {
    flex: 1,
    padding: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
  },
  planCardActive: { borderColor: colors.accent, borderWidth: 2, backgroundColor: colors.accentLight },
  planLabel: { ...typography.caption, color: colors.text.secondary, marginBottom: spacing.xs },
  planPrice: { ...typography.title, color: colors.text.primary },
  saveBadge: {
    position: 'absolute',
    top: -10,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.chip,
  },
  saveBadgeText: { ...typography.small, color: '#FFFFFF', fontWeight: '700' },
  features: { marginBottom: spacing.xl },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginBottom: spacing.md },
  featureText: { ...typography.body, color: colors.text.primary },
  restoreButton: { alignSelf: 'center', marginTop: spacing.base },
  restoreText: { ...typography.caption, color: colors.text.secondary, textDecorationLine: 'underline' },
  social: { ...typography.caption, color: colors.text.secondary, textAlign: 'center', marginTop: spacing.base },
});
```

- [ ] **Step 2: Install expo-blur if needed**

```bash
cd SmartCompareApp && npx expo install expo-blur
```

- [ ] **Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/PaywallScreen.tsx SmartCompareApp/package.json
git commit -m "feat: add PaywallScreen placeholder (bottom sheet with plan cards)"
```

---

### Task 14: App.tsx Navigation Rewrite

**Files:**
- Rewrite: `SmartCompareApp/App.tsx`
- Delete: `SmartCompareApp/src/screens/CameraScreen.tsx`
- Delete: `SmartCompareApp/src/screens/PreferencesScreen.tsx`

- [ ] **Step 1: Read existing App.tsx**

Understand the auth flow: loading → auth check → preferences gate → main navigator.

- [ ] **Step 2: Rewrite App.tsx**

New structure:
- Font loading via `useAppFonts()` from `theme/fonts.ts`
- i18n initialization: call `getSavedLanguage()` → `i18n.changeLanguage()` + `I18nManager.forceRTL()` on startup
- Splash state: show `<SplashScreen>` during loading (fonts + auth check)
- Auth flow: same as before (isAuthenticated check)
- Onboarding flow: show `<OnboardingScreen>` if `needsPreferences` (replaces PreferencesScreen)
- Main navigator: **Bottom tabs** (not stack) with 3 tabs:
  - Home tab → HomeScreen (camera-first)
  - History tab → HistoryScreen
  - Profile tab → ProfileScreen
- Results and Paywall are presented as modal/stack screens on top of tabs
- Auth screens (Login, Register, ForgotPassword) stay as stack navigator

```typescript
import React, { useState, useEffect, useCallback } from 'react';
import { I18nManager } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Home, Clock, User } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { useAppFonts } from './src/theme/fonts';
import { colors, typography } from './src/theme';
import { getSavedLanguage } from './src/i18n';
import './src/i18n'; // Initialize i18next

// Screens
import SplashScreen from './src/screens/SplashScreen';
import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import HomeScreen from './src/screens/HomeScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import ProfileScreen from './src/screens/ProfileScreen';

// Auth
import { verifyAuth, initializeAuth, clearSession } from './src/services/authService';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
const AuthStack = createNativeStackNavigator();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
      <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    </AuthStack.Navigator>
  );
}

function MainTabs() {
  const { t } = useTranslation();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.text.placeholder,
        tabBarStyle: {
          borderTopColor: colors.border.light,
          backgroundColor: colors.bg.primary,
        },
        tabBarLabelStyle: { ...typography.small, fontWeight: '500' },
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeScreen}
        options={{
          tabBarLabel: t('app.name'),
          tabBarIcon: ({ color, size }) => <Home size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="HistoryTab"
        component={HistoryScreen}
        options={{
          tabBarLabel: t('history.title'),
          tabBarIcon: ({ color, size }) => <Clock size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="ProfileTab"
        component={ProfileScreen}
        options={{
          tabBarLabel: t('profile.title'),
          tabBarIcon: ({ color, size }) => <User size={size} color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  const fontsLoaded = useAppFonts();
  const [showSplash, setShowSplash] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsPreferences, setNeedsPreferences] = useState(false);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    async function init() {
      // Set language + RTL before rendering
      const lang = await getSavedLanguage();
      const { default: i18n } = await import('./src/i18n');
      await i18n.changeLanguage(lang);
      const shouldBeRTL = lang === 'ar';
      if (I18nManager.isRTL !== shouldBeRTL) {
        I18nManager.allowRTL(true);
        I18nManager.forceRTL(shouldBeRTL);
      }

      // Auth check
      try {
        const authUser = await initializeAuth();
        if (authUser) {
          setUser(authUser);
          setIsAuthenticated(true);
          setNeedsPreferences(!authUser.preferences_completed);
        }
      } catch {}
      setIsLoading(false);
    }
    init();
  }, []);

  const handleSplashFinish = useCallback(() => {
    setShowSplash(false);
  }, []);

  const handleLogout = useCallback(async () => {
    await clearSession();
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  const handlePreferencesComplete = useCallback(() => {
    setNeedsPreferences(false);
  }, []);

  if (!fontsLoaded || isLoading || showSplash) {
    return <SplashScreen onFinish={handleSplashFinish} />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!isAuthenticated ? (
          <Stack.Screen name="Auth" component={AuthNavigator} />
        ) : needsPreferences ? (
          <Stack.Screen name="Onboarding">
            {(props) => (
              <OnboardingScreen {...props} onComplete={handlePreferencesComplete} />
            )}
          </Stack.Screen>
        ) : (
          <>
            <Stack.Screen name="Main" component={MainTabs} />
            <Stack.Screen
              name="Results"
              component={ResultsScreen}
              options={{ presentation: 'modal' }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

Note: The agent must adapt this to match the existing navigation type definitions and ensure all screen params are properly typed.

- [ ] **Step 3: Delete old screens**

```bash
rm SmartCompareApp/src/screens/CameraScreen.tsx
rm SmartCompareApp/src/screens/PreferencesScreen.tsx
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/App.tsx
git rm SmartCompareApp/src/screens/CameraScreen.tsx SmartCompareApp/src/screens/PreferencesScreen.tsx
git commit -m "feat: rewrite App.tsx with bottom tabs, splash flow, delete old screens"
```

---

### Task 15: Integration Testing & Bug Fixes

**Files:**
- All screen files may need fixes

This is the "make it work end-to-end" task. The agent should:

- [ ] **Step 1: Run TypeScript check**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Fix all type errors.

- [ ] **Step 2: Start Expo dev server**

```bash
cd SmartCompareApp && npx expo start
```

- [ ] **Step 3: Test each flow on device/simulator**

Test and fix:
1. Splash → Onboarding flow (6 steps complete)
2. Login → Home (camera permissions, viewfinder loads)
3. Text search → Results (SSE streaming, skeleton, reveal)
4. Camera capture → identify → Results
5. History (items load, search works, delete works)
6. Profile (language switch triggers restart, region change, logout)
7. Comparison counter (counts up, shows pill, paywall triggers at 3)
8. Back navigation from all screens

- [ ] **Step 4: Fix RTL issues**

Switch to Arabic, verify:
- All text is right-aligned
- Directional icons (arrows, chevrons) are flipped
- Non-directional icons (search, camera, star) are NOT flipped
- Numbers display correctly
- No text overflow from longer Arabic strings
- Camera viewfinder does NOT flip

- [ ] **Step 5: Commit all fixes**

```bash
git add -A SmartCompareApp/
git commit -m "fix: integration fixes for all screens and RTL support"
```

---

## Phase 3: Polish (Tasks 16–17)

### Task 16: Animations & Micro-interactions

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx` (loading sequence)
- Modify: `SmartCompareApp/src/screens/HistoryScreen.tsx` (staggered entrance)

- [ ] **Step 1: Add comparison loading sequence to ResultsScreen**

In ResultsScreen, implement the progressive skeleton → real content transition:
- Show skeleton with shimmer when waiting for SSE events
- Status messages cycle through: finding → analyzing → prices → reviews → scores → done
- Progress bar at top advances with each SSE event
- When data arrives, skeleton sections fade out and real content fades in (staggered, top to bottom)
- Winner reveal: when verdict section scrolls into view, winner card gets emerald border animation + `Haptics.impactAsync(ImpactFeedbackStyle.Medium)`

Use `react-native-reanimated` `FadeIn` and `FadeOut` layout animations.

- [ ] **Step 2: Add staggered list entrance to HistoryScreen**

Use `Animated.FlatList` with `itemLayoutAnimation` from reanimated, or manually apply `FadeInDown.delay(index * 50)` to each list item via `entering` prop.

- [ ] **Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx SmartCompareApp/src/screens/HistoryScreen.tsx
git commit -m "feat: add loading sequence, winner reveal haptic, staggered list animations"
```

---

### Task 17: Final QA & Cleanup

- [ ] **Step 1: Run TypeScript check**

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 2: Search for any remaining hardcoded strings**

Search all `.tsx` files for English strings that should be i18n keys. Look for patterns like `"Error"`, `"Loading"`, `"Cancel"`, `"Save"` that aren't wrapped in `t()`.

- [ ] **Step 3: Search for banned RTL properties**

Search for `marginLeft`, `marginRight`, `paddingLeft`, `paddingRight`, `textAlign: 'left'`, `textAlign: 'right'` in all `.tsx` files. Replace with logical equivalents.

- [ ] **Step 4: Search for old @smartcompare references**

Search for `smartcompare` (case-insensitive) across all files. Should only appear in comments/docs, not in active code.

- [ ] **Step 5: Verify no stale imports**

Check that no file imports from deleted screens (CameraScreen, AccountScreen, PreferencesScreen).

- [ ] **Step 6: Final commit**

```bash
git add -A SmartCompareApp/
git commit -m "chore: final QA cleanup — i18n audit, RTL audit, stale import removal"
```

---

## Done Criteria

All must pass before implementation is considered complete:

- [ ] All 10 screens render without crashes in EN and AR
- [ ] RTL mirroring works on all directional elements
- [ ] Camera-first home screen works (permissions, capture, identify)
- [ ] SSE streaming comparison with skeleton → reveal animation works
- [ ] 3 free comparison counter tracks, displays, and triggers paywall
- [ ] All navigation flows work (splash → onboarding → auth → home → results → history → profile)
- [ ] No hardcoded English strings (all via i18n)
- [ ] No banned RTL properties (marginLeft/Right, paddingLeft/Right)
- [ ] No stale @smartcompare_ references in active code
- [ ] `npx tsc --noEmit` passes with 0 errors
- [ ] Zero console errors/warnings in both languages

---

## Agent Team Assignment (for TeamCreate execution)

This plan is designed for a 4-agent Opus team as specified in the design doc:

| Agent | Tasks | Non-overlapping Files |
|-------|-------|----------------------|
| **Backend** | 1 (deps), 2 (theme), 3 (i18n), 4 (storage+types) | `theme/`, `i18n/`, `hooks/`, `utils/`, `services/`, `types/` |
| **Frontend** | 5 (components), 6-13 (screens), 14 (App.tsx) | `components/`, `screens/`, `App.tsx` |
| **Test** | Write tests for each completed task | `__tests__/` |
| **QA** | 15 (integration), 16 (animations), 17 (final QA) | Reviews all files |

**Dependency order:** Tasks 1→2→3→4 must complete before 5. Task 5 must complete before 6-13. Task 14 requires all screens. Tasks 15-17 require everything.

**Parallel opportunities:** Tasks 6-13 (individual screens) can be done in parallel once Task 5 is complete. Backend agent (1-4) and Test agent (writing test shells) can work simultaneously from the start.
