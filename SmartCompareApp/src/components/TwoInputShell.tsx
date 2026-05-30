/**
 * TwoInputShell — shared two-box shell for Text and URL compare modes.
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md
 *   § 3 (anatomy) · § 4 (interactions) · § 7 (RTL/i18n) · § 8 (analytics)
 *
 * Renders numeral circles ① / ②, a hairline that connects them, an emerald
 * "vs" pill on its midpoint, both text/url boxes, the optional inline
 * caption row, and a full-width black Compare CTA. Owns per-mode state
 * (text-mode pair and url-mode pair are independent, preserved across
 * switches), validation timing (blur only), paste-detection wiring, the
 * 3-part "ready" celebration, and the 250ms-deferred auto-focus.
 *
 * Build Principle #4: nothing scary — no shake, no red borders, no error
 * copy. Invalid state stays neutral; the disabled CTA does the work.
 *
 * ─── Contract for tests (Reviewer 1 notes for Test agent) ──────────────
 *
 * Props (TwoInputShellProps):
 *   mode             — 'text' | 'url'. Drives placeholder set, validation
 *                      predicate (validateText vs validateUrl), keyboard
 *                      type, Box B returnKeyType ('search' for text, 'go'
 *                      for url), and which slot in `_twoInputCache` is
 *                      rendered. Flipping mode preserves the other mode's
 *                      pair via the module-scoped cache (spec § 3.3).
 *   onSubmit(a, b)   — required. Fires when CTA tapped AND both boxes are
 *                      blur-valid AND !disabled. Receives trimmed strings.
 *                      Order matches Box A then Box B (RTL does NOT swap
 *                      argument order — only visual edges flip).
 *   onPasteSplit(box)— optional. Fires AFTER auto-split (§ 4.1.1)
 *                      successfully populates both boxes. `box` is the
 *                      source box ('a' or 'b') the user pasted into.
 *                      Caller fires `compare_entry_paste_split` analytics.
 *   onModeAutoswitch — optional. Fires AFTER URL paste in TEXT mode
 *      (from, to)      triggers mode-switch (§ 4.1.2). `from` is always
 *                      'text', `to` is always 'url'. Caller is
 *                      responsible for advancing the active mode on
 *                      HomeScreen + firing compare_entry_mode_autoswitch
 *                      analytics. The destination URL is already seeded
 *                      into _twoInputCache.url.a before this fires.
 *   onReady(deltaMs) — optional. Fires EXACTLY ONCE per ready-transition
 *                      (both circles flip to emerald). `deltaMs` measured
 *                      from `mountAtRef` (re-set on every mode flip).
 *                      Re-renders with bothValid===true do NOT re-fire.
 *                      Reverse direction (valid → invalid) does NOT fire.
 *                      Caller fires compare_entry_ready analytics.
 *   initialA / initialB — optional. Pre-seed boxes (used by the
 *                      auto-mode-switch handoff). When provided, win over
 *                      the module cache for that mode's seed. Read once
 *                      at mount of the given mode, not on every render.
 *   disabled         — optional. Locks all inputs + suppresses onSubmit
 *                      AND dims CTA opacity to 0.5 via animated style.
 *                      Boxes set editable={!disabled}.
 *   testID           — optional. Default 'two-input-shell'. Children
 *                      derive testIDs as `${testID}-a/-b`, `${testID}-vs-pill`,
 *                      `${testID}-cta`, `${testID}-caption-paste-split`,
 *                      `${testID}-caption-mode-switch`, `${testID}-a-circle`,
 *                      `${testID}-b-circle`, `${testID}-a-input`, etc.
 *
 * Validation timing (spec § 4.2):
 *   - Predicate runs on onBlur ONLY. Editing flips validA/validB back to
 *     false on the next keystroke (so a previously-valid box that is
 *     edited re-validates on next blur).
 *   - validateText: trimmed.length ∈ [2, 80] AND no control chars
 *     (U+0000..U+001F, U+007F).
 *   - validateUrl:  trimmed.length ∈ [1, 2048] AND new URL(trimmed) parses
 *     AND protocol ∈ {http:, https:}. Returns false on parse failure
 *     (no thrown exception escapes).
 *
 * Paste-detection (spec § 4.1) — strict priority order in onBoxChange:
 *   1. URL-paste-in-Text-mode → mode-switch (§ 4.1.2) — checked FIRST.
 *      Conditions: mode==='text' AND length-jump>=10 AND
 *      looksLikeUrl(trimmed) AND _twoInputCache.url is NOT occupied
 *      (both url.a + url.b length 0). On match: seed url.a, restore origin
 *      box to its pre-paste value via persistA/persistB, showCaption, fire
 *      onModeAutoswitch.
 *   2. Comparison-shape paste → auto-split (§ 4.1.1).
 *      Conditions: length-jump>=10 AND looksLikeTwoProducts(next) AND
 *      sibling box trim-length 0. On match: setBoxA(left), setBoxB(right),
 *      showCaption('paste_split'), fire onPasteSplit(box), focus Box B.
 *   3. Otherwise → raw paste / typing.
 *
 *   Edge cases protected:
 *   - Sibling has content → fall back to raw paste (don't clobber).
 *   - URL paste but URL mode already occupied → fall through to step 2 or
 *     raw paste (don't overwrite link state).
 *   - Length jump < 10 → never treated as paste (typing heuristic).
 *
 * Celebration (spec § 4.3) — fires when bothValid flips false→true:
 *   1. circleAScale + circleBScale spring 1.0→1.12→1.0 via
 *      withSequence(withSpring, withSpring) using motion.springConfig.chip
 *      (shared with ModeChip per Q1 default — cross-mode visual
 *      consistency).
 *   2. ctaOpacity withTiming 0.5→1.0 over 200ms; ctaGlow withTiming
 *      0→12 over 240ms (drives shadowRadius + shadowOpacity).
 *   3. fireSuccessHaptic() → Haptics.notificationAsync(
 *      Haptics.NotificationFeedbackType.Success). Wrapped in the SAME
 *      try/catch + maybePromise.catch pattern as ModeChip — test mocks
 *      that return undefined must not crash.
 *   4. onReady(Date.now() - mountAtRef.current) fired.
 *
 *   Reverse direction (true→false): only ctaOpacity → 0.5 + ctaGlow → 0
 *   over 300ms. NO haptic, NO un-celebrate animation on circles (the
 *   per-box emerald fill handles that via the circleValid style swap).
 *
 *   Negative assertions Test agent should grep in THIS file:
 *   - `shake|wobble|jitter|withSequence.*-` → MUST be zero hits.
 *   - `useNativeDriver:\s*false` → MUST be zero hits.
 *   - The comment on line ~14 mentioning "no shake" is documentary only;
 *     scope grep to JSX/animation code or use word-boundary patterns to
 *     exclude doc comments if false-positives surface.
 *
 * RTL (spec § 7.1):
 *   - I18nManager.isRTL toggles styles.hairlineLTR/RTL and
 *     styles.vsPillWrapLTR/RTL → numeral edges + hairline edge swap.
 *   - Row flexDirection becomes 'row-reverse' when isRTL → numeral circle
 *     sits on the right of the box in AR.
 *   - Box textInput uses textAlign: 'auto' (RN auto-detects script).
 *   - AR locale (i18n.language startsWith 'ar') triggers
 *     arabicLineHeightMultiplier on input + caption (1.7/1.5).
 *   - "vs" pill text textTransform: 'none' in AR (the eyebrow typography
 *     defaults to uppercase which would mangle "مقابل").
 *
 * Focus + keyboard flow (spec § 4.4):
 *   - First mount of each mode (tracked via firstMountedModesRef Set)
 *     auto-focuses Box A after 250ms (FOCUS_DELAY_MS) so the
 *     mode-chip spring + box hairline animation settle first.
 *   - Box A returnKeyType="next" → focuses Box B.
 *   - Box B returnKeyType "search" (text) / "go" (url) → submit if both
 *     valid, else Keyboard.dismiss() (silent — no error UX per Q3).
 *   - Tap outside boxes (Pressable wrapper) → Keyboard.dismiss().
 *   - ⊗ clear button visible only when focused && value.length>0; tap
 *     empties the box but does not change focus.
 *
 * Module-scoped cache (_twoInputCache):
 *   - Survives component remount when caller toggles `mode` prop.
 *   - text + url slots are independent.
 *   - Reset between tests via __resetTwoInputCacheForTests() (named
 *     export). Call this in jest beforeEach() to avoid cross-test
 *     state bleed.
 *
 * Theme tokens consumed (so Test agent doesn't need to read theme/index.ts):
 *   - colors.accent / accentDark / accentLight / border.light / border.medium
 *   - colors.cta.primary / cta.onPrimary / bg.primary / text.primary
 *   - radii.card (boxes) / radii.button (CTA) / radii.chip (vs pill)
 *   - typography.eyebrow (vs pill) / typography.body (input) /
 *     typography.bodyEmphasis (CTA label) / typography.caption (captions)
 *   - motion.springConfig.chip (celebration)
 *   - spacing.xs/sm/md/base/lg/xl/2xl
 *
 * What this component does NOT own (and tests should NOT assert):
 *   - Mode-chip state on HomeScreen (caller owns inputMode).
 *   - Analytics events (caller fires; component fires callbacks only).
 *   - canCompare branching → handled by HomeScreen rendering
 *     PaywallBanner in this component's slot when false.
 *   - Min-display-floor 1.2s timing on Home→Results — HomeScreen owns it
 *     via loadingStartedAtRef.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  I18nManager,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { Check, X as XIcon } from 'lucide-react-native';
import {
  arabicLineHeightMultiplier,
  colors,
  radii,
  spacing,
  typography,
} from '../theme';
import { motion } from '../theme/motion';
import {
  looksLikeTwoProducts,
  splitComparisonShape,
} from '../utils/parseComparisonShape';
import { looksLikeUrl } from '../utils/urlPasteDetect';

export type TwoInputMode = 'text' | 'url';

export interface TwoInputShellProps {
  mode: TwoInputMode;
  onSubmit: (a: string, b: string) => void;
  onPasteSplit?: (sourceBox: 'a' | 'b') => void;
  onModeAutoswitch?: (from: 'text', to: 'url') => void;
  onReady?: (timeToReadyMs: number) => void;
  /**
   * Fires after every keystroke / paste with the current (a, b) pair.
   * Lets external surfaces (e.g. HomeScreen's Compare CTA) gate on the
   * pair without owning the input state.
   */
  onChange?: (a: string, b: string) => void;
  initialA?: string;
  initialB?: string;
  disabled?: boolean;
  testID?: string;
}

type CaptionKind = 'paste_split' | 'mode_switch' | null;

const CONTROL_CHARS = /[\u0000-\u001F\u007F]/;
const TEXT_MIN = 2;
const TEXT_MAX = 80;
const URL_MAX = 2048;
const PASTE_JUMP_THRESHOLD = 10;
const CAPTION_DURATION_MS = 2500;
const FOCUS_DELAY_MS = 250;

// Module-scoped per-mode cache so switching modes preserves both pairs
// (spec § 3.3). Test helper below clears it between scenarios.
let _twoInputCache: {
  text: { a: string; b: string };
  url: { a: string; b: string };
} = { text: { a: '', b: '' }, url: { a: '', b: '' } };

export function __resetTwoInputCacheForTests() {
  _twoInputCache = { text: { a: '', b: '' }, url: { a: '', b: '' } };
}

function validateText(raw: string): boolean {
  const trimmed = raw.trim();
  return (
    trimmed.length >= TEXT_MIN &&
    trimmed.length <= TEXT_MAX &&
    !CONTROL_CHARS.test(trimmed)
  );
}

function validateUrl(raw: string): boolean {
  const trimmed = raw.trim();
  if (trimmed.length === 0 || trimmed.length > URL_MAX) return false;
  try {
    const u = new URL(trimmed);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function fireSuccessHaptic() {
  try {
    const maybePromise = Haptics.notificationAsync(
      Haptics.NotificationFeedbackType.Success
    );
    if (maybePromise && typeof maybePromise.catch === 'function') {
      maybePromise.catch(() => {});
    }
  } catch {
    /* haptic engine threw synchronously — silently no-op */
  }
}

function TwoInputShell({
  mode,
  onSubmit,
  onPasteSplit,
  onModeAutoswitch,
  onReady,
  onChange,
  initialA,
  initialB,
  disabled = false,
  testID = 'two-input-shell',
}: TwoInputShellProps) {
  const { t, i18n } = useTranslation();
  const isRTL = I18nManager.isRTL;
  const isAR = i18n.language?.startsWith('ar');
  const cacheRef = useRef(_twoInputCache);
  const initialPair = useMemo(() => {
    const seeded = cacheRef.current[mode];
    return {
      a: initialA ?? seeded.a,
      b: initialB ?? seeded.b,
    };
    // Only re-seed if mode flips. initialA/B are read-once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const [boxA, setBoxAState] = useState(initialPair.a);
  const [boxB, setBoxBState] = useState(initialPair.b);
  const [validA, setValidA] = useState<boolean>(false);
  const [validB, setValidB] = useState<boolean>(false);
  const [caption, setCaption] = useState<CaptionKind>(null);

  const boxARef = useRef<TextInput>(null);
  const boxBRef = useRef<TextInput>(null);
  const mountAtRef = useRef<number>(Date.now());
  const firstMountedModesRef = useRef<Set<TwoInputMode>>(new Set());
  const prevBothValidRef = useRef<boolean>(false);
  const captionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Animated values for celebration. SharedValues live on the UI thread.
  const circleAScale = useSharedValue(1);
  const circleBScale = useSharedValue(1);
  const ctaOpacity = useSharedValue(0.5);
  const ctaGlow = useSharedValue(0);

  const validate = useCallback(
    (s: string) => (mode === 'url' ? validateUrl(s) : validateText(s)),
    [mode]
  );

  // Persist to module cache on every write so the sibling mode's state
  // survives a mode flip.
  const persistA = useCallback(
    (next: string) => {
      cacheRef.current[mode].a = next;
      setBoxAState(next);
      // Reset validity flag while editing (spec § 4.2 — no keystroke validation)
      if (validA) setValidA(false);
    },
    [mode, validA]
  );
  const persistB = useCallback(
    (next: string) => {
      cacheRef.current[mode].b = next;
      setBoxBState(next);
      if (validB) setValidB(false);
    },
    [mode, validB]
  );

  // Re-seed boxes when mode prop flips (preserve other mode's state).
  useEffect(() => {
    const seeded = cacheRef.current[mode];
    setBoxAState(initialA ?? seeded.a);
    setBoxBState(initialB ?? seeded.b);
    setValidA(validate(initialA ?? seeded.a));
    setValidB(validate(initialB ?? seeded.b));
    mountAtRef.current = Date.now();
    // Auto-focus Box A only on FIRST mount per mode (spec § 4.4).
    if (!firstMountedModesRef.current.has(mode)) {
      firstMountedModesRef.current.add(mode);
      const timeout = setTimeout(() => boxARef.current?.focus(), FOCUS_DELAY_MS);
      return () => clearTimeout(timeout);
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    return () => {
      if (captionTimerRef.current) clearTimeout(captionTimerRef.current);
    };
  }, []);

  // S3 — surface the live (a, b) pair to external gate consumers (the
  // HomeScreen Compare CTA reads this to enable/disable). Fire-and-forget
  // on every box change. Safe under mode flips because boxA/boxB are
  // re-seeded by the mode useEffect above.
  useEffect(() => {
    onChange?.(boxA, boxB);
  }, [boxA, boxB, onChange]);

  const showCaption = useCallback((kind: Exclude<CaptionKind, null>) => {
    setCaption(kind);
    if (captionTimerRef.current) clearTimeout(captionTimerRef.current);
    captionTimerRef.current = setTimeout(() => {
      setCaption(null);
      captionTimerRef.current = null;
    }, CAPTION_DURATION_MS);
  }, []);

  // Paste / typing handler shared by both boxes.
  const handleBoxChange = useCallback(
    (box: 'a' | 'b', next: string, prev: string) => {
      const jumped = next.length - prev.length >= PASTE_JUMP_THRESHOLD;
      // `trimmed` is reserved for the cache seed below (where leading/
      // trailing whitespace would corrupt the saved URL). The predicate
      // check itself MUST use the raw `next` per spec § 4.1.2 — anchored
      // ^https?://[^\s]+$ rejects whitespace-prefixed pastes so the
      // auto-mode-switch stays conservative (OQ-FE caller-side).
      const trimmed = next.trim();

      // § 4.1.2 — URL paste in TEXT mode → mode-switch (priority over split).
      if (mode === 'text' && jumped && looksLikeUrl(next)) {
        const urlCache = cacheRef.current.url;
        const linkOccupied = urlCache.a.length > 0 || urlCache.b.length > 0;
        if (!linkOccupied) {
          cacheRef.current.url.a = trimmed;
          // restore origin to pre-paste value so Text mode is unchanged.
          if (box === 'a') persistA(prev);
          else persistB(prev);
          showCaption('mode_switch');
          onModeAutoswitch?.('text', 'url');
          return;
        }
        // else fall through to raw paste below.
      }

      // § 4.1.1 — comparison-shape paste → auto-split (sibling must be empty).
      if (jumped && looksLikeTwoProducts(next)) {
        const sibling = box === 'a' ? boxB : boxA;
        if (sibling.trim().length === 0) {
          const split = splitComparisonShape(next);
          if (split) {
            const [left, right] = split;
            persistA(left);
            persistB(right);
            showCaption('paste_split');
            onPasteSplit?.(box);
            // cursor at end of Box B per spec § 4.1.1.
            setTimeout(() => boxBRef.current?.focus(), 0);
            return;
          }
        }
      }

      // raw paste / typing.
      if (box === 'a') persistA(next);
      else persistB(next);
    },
    [boxA, boxB, mode, onModeAutoswitch, onPasteSplit, persistA, persistB, showCaption]
  );

  // Blur → re-run validator (spec § 4.2 single check point).
  const blurA = useCallback(() => setValidA(validate(boxA)), [boxA, validate]);
  const blurB = useCallback(() => setValidB(validate(boxB)), [boxB, validate]);

  const bothValid = validA && validB;
  const canSubmit = bothValid && !disabled;

  // Celebration / reverse direction (spec § 4.3).
  useEffect(() => {
    if (bothValid && !prevBothValidRef.current) {
      const spring = motion.springConfig.chip;
      circleAScale.value = withSequence(
        withSpring(1.12, spring),
        withSpring(1.0, spring)
      );
      circleBScale.value = withSequence(
        withSpring(1.12, spring),
        withSpring(1.0, spring)
      );
      ctaOpacity.value = withTiming(1.0, { duration: 200 });
      ctaGlow.value = withTiming(12, { duration: 240 });
      fireSuccessHaptic();
      onReady?.(Date.now() - mountAtRef.current);
    } else if (!bothValid && prevBothValidRef.current) {
      ctaOpacity.value = withTiming(0.5, { duration: 300 });
      ctaGlow.value = withTiming(0, { duration: 300 });
      // circles un-fill silently — no haptic.
    }
    prevBothValidRef.current = bothValid;
  }, [bothValid, circleAScale, circleBScale, ctaGlow, ctaOpacity, onReady]);

  const circleAStyle = useAnimatedStyle(() => ({
    transform: [{ scale: circleAScale.value }],
  }));
  const circleBStyle = useAnimatedStyle(() => ({
    transform: [{ scale: circleBScale.value }],
  }));
  const ctaAnimStyle = useAnimatedStyle(() => ({
    opacity: ctaOpacity.value,
    shadowColor: colors.accent,
    shadowOpacity: ctaGlow.value > 0 ? 0.45 : 0,
    shadowRadius: ctaGlow.value,
    shadowOffset: { width: 0, height: 0 },
  }));

  const placeholders =
    mode === 'url'
      ? {
          a: t('home.compare.box_a_url'),
          b: t('home.compare.box_b_url'),
        }
      : {
          a: t('home.compare.box_a_text'),
          b: t('home.compare.box_b_text'),
        };

  const returnKeyB: 'search' | 'go' = mode === 'url' ? 'go' : 'search';

  const submit = () => {
    if (!canSubmit) {
      Keyboard.dismiss();
      return;
    }
    onSubmit(boxA.trim(), boxB.trim());
  };

  const handleBoxBSubmit = () => {
    if (canSubmit) submit();
    else Keyboard.dismiss();
  };

  const dismissKeyboard = () => Keyboard.dismiss();

  // RTL: numerals + clear button + hairline anchor on the right side.
  const numeralA = '1';
  const numeralB = '2';

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.kav}
    >
      <Pressable onPress={dismissKeyboard} accessible={false}>
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.scrollContent}
        >
          <View style={styles.shell} testID={testID}>
            {/* Connecting hairline — runs vertically between circles. */}
            <View
              pointerEvents="none"
              style={[
                styles.hairline,
                isRTL ? styles.hairlineRTL : styles.hairlineLTR,
              ]}
            />

            {/* Vs pill — sits on the hairline midpoint. */}
            <View
              pointerEvents="none"
              style={[
                styles.vsPillWrap,
                isRTL ? styles.vsPillWrapRTL : styles.vsPillWrapLTR,
              ]}
            >
              <View style={styles.vsPill} testID={`${testID}-vs-pill`}>
                <Text
                  style={[
                    styles.vsPillText,
                    isAR && { textTransform: 'none' as const },
                  ]}
                >
                  {t('home.compare.vs_pill')}
                </Text>
              </View>
            </View>

            {/* Box A row */}
            <Row
              isRTL={isRTL}
              isAR={isAR}
              numeral={numeralA}
              valid={validA}
              circleStyle={circleAStyle}
              testIDPrefix={`${testID}-a`}
              inputRef={boxARef}
              value={boxA}
              placeholder={placeholders.a}
              onChange={(text) => handleBoxChange('a', text, boxA)}
              onBlur={blurA}
              onSubmitEditing={() => boxBRef.current?.focus()}
              returnKeyType="next"
              keyboardType={mode === 'url' ? 'url' : 'default'}
              maxLength={mode === 'url' ? URL_MAX : TEXT_MAX}
              editable={!disabled}
              accessibilityLabelValid={t('home.compare.a11y_box_a_valid')}
              onClear={() => persistA('')}
            />

            {/* Caption row below Box A — mode-switch caption appears here. */}
            {caption === 'mode_switch' && (
              <Text
                testID={`${testID}-caption-mode-switch`}
                style={[styles.caption, isAR && styles.captionAR]}
              >
                {t('home.compare.mode_switch_caption')}
              </Text>
            )}

            {/* Spacer gives the hairline + pill room to render between rows. */}
            <View style={styles.rowGap} />

            {/* Box B row */}
            <Row
              isRTL={isRTL}
              isAR={isAR}
              numeral={numeralB}
              valid={validB}
              circleStyle={circleBStyle}
              testIDPrefix={`${testID}-b`}
              inputRef={boxBRef}
              value={boxB}
              placeholder={placeholders.b}
              onChange={(text) => handleBoxChange('b', text, boxB)}
              onBlur={blurB}
              onSubmitEditing={handleBoxBSubmit}
              returnKeyType={returnKeyB}
              keyboardType={mode === 'url' ? 'url' : 'default'}
              maxLength={mode === 'url' ? URL_MAX : TEXT_MAX}
              editable={!disabled}
              accessibilityLabelValid={t('home.compare.a11y_box_b_valid')}
              onClear={() => persistB('')}
            />

            {/* Caption row below Box B — split caption appears here. */}
            {caption === 'paste_split' && (
              <Text
                testID={`${testID}-caption-paste-split`}
                style={[styles.caption, isAR && styles.captionAR]}
              >
                {t('home.compare.paste_split_caption')}
              </Text>
            )}

            {/* Compare CTA */}
            <Animated.View style={[styles.ctaWrap, ctaAnimStyle]}>
              <TouchableOpacity
                testID={`${testID}-cta`}
                style={styles.cta}
                onPress={submit}
                disabled={!canSubmit}
                accessibilityRole="button"
                accessibilityState={{ disabled: !canSubmit }}
                accessibilityLabel={
                  bothValid ? t('home.compare.a11y_ready') : t('home.compare.cta')
                }
              >
                <Text style={styles.ctaText}>{t('home.compare.cta')}</Text>
              </TouchableOpacity>
            </Animated.View>
          </View>
        </ScrollView>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

interface RowProps {
  isRTL: boolean;
  isAR: boolean;
  numeral: string;
  valid: boolean;
  circleStyle: ReturnType<typeof useAnimatedStyle>;
  testIDPrefix: string;
  inputRef: React.RefObject<TextInput | null>;
  value: string;
  placeholder: string;
  onChange: (text: string) => void;
  onBlur: () => void;
  onSubmitEditing: () => void;
  returnKeyType: 'next' | 'search' | 'go';
  keyboardType: 'default' | 'url';
  maxLength: number;
  editable: boolean;
  accessibilityLabelValid: string;
  onClear: () => void;
}

function Row({
  isRTL,
  isAR,
  numeral,
  valid,
  circleStyle,
  testIDPrefix,
  inputRef,
  value,
  placeholder,
  onChange,
  onBlur,
  onSubmitEditing,
  returnKeyType,
  keyboardType,
  maxLength,
  editable,
  accessibilityLabelValid,
  onClear,
}: RowProps) {
  const [focused, setFocused] = useState(false);
  const showClear = focused && value.length > 0;
  const rowDirection = isRTL ? 'row-reverse' : 'row';

  return (
    <View style={[styles.row, { flexDirection: rowDirection as 'row' }]}>
      <Animated.View
        testID={`${testIDPrefix}-circle`}
        accessibilityLabel={valid ? accessibilityLabelValid : undefined}
        style={[
          styles.circle,
          valid && styles.circleValid,
          circleStyle,
        ]}
      >
        {valid ? (
          <Check size={14} color={colors.bg.primary} strokeWidth={3} />
        ) : (
          <Text style={styles.numeral}>{numeral}</Text>
        )}
      </Animated.View>
      <View
        style={[
          styles.box,
          focused && styles.boxFocused,
        ]}
      >
        <TextInput
          testID={`${testIDPrefix}-input`}
          ref={inputRef}
          value={value}
          placeholder={placeholder}
          placeholderTextColor={colors.text.placeholder}
          onChangeText={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => {
            setFocused(false);
            onBlur();
          }}
          onSubmitEditing={onSubmitEditing}
          returnKeyType={returnKeyType}
          keyboardType={keyboardType}
          maxLength={maxLength}
          editable={editable}
          autoCorrect={false}
          autoCapitalize={keyboardType === 'url' ? 'none' : 'sentences'}
          style={[
            styles.input,
            isAR && {
              lineHeight: typography.body.lineHeight * arabicLineHeightMultiplier,
            },
          ]}
        />
        {showClear && (
          <TouchableOpacity
            testID={`${testIDPrefix}-clear`}
            onPress={onClear}
            accessibilityRole="button"
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            style={styles.clearBtn}
          >
            <XIcon size={16} color={colors.text.placeholder} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const CIRCLE_SIZE = 24;
const BOX_HEIGHT = 48;
const VS_PILL_HEIGHT = 24;
const HAIRLINE_EDGE = spacing.lg + CIRCLE_SIZE / 2; // x-position of numeral center

const styles = StyleSheet.create({
  kav: {
    width: '100%',
  },
  scrollContent: {
    flexGrow: 1,
  },
  shell: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    position: 'relative',
  },
  hairline: {
    position: 'absolute',
    top: BOX_HEIGHT + spacing.sm,
    bottom: BOX_HEIGHT + spacing.md,
    width: 1,
    backgroundColor: colors.border.light,
  },
  hairlineLTR: {
    left: HAIRLINE_EDGE,
  },
  hairlineRTL: {
    right: HAIRLINE_EDGE,
  },
  vsPillWrap: {
    position: 'absolute',
    top: BOX_HEIGHT + spacing.md + 4,
    height: VS_PILL_HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vsPillWrapLTR: {
    left: HAIRLINE_EDGE - 18,
  },
  vsPillWrapRTL: {
    right: HAIRLINE_EDGE - 18,
  },
  vsPill: {
    height: VS_PILL_HEIGHT,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.accentLight,
    borderRadius: radii.chip,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vsPillText: {
    ...typography.eyebrow,
    color: colors.accentDark,
  },
  row: {
    alignItems: 'center',
    gap: spacing.sm,
  },
  rowGap: {
    height: spacing['2xl'],
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circleValid: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  numeral: {
    ...typography.small,
    fontWeight: '600',
    color: colors.text.secondary,
  },
  box: {
    flex: 1,
    height: BOX_HEIGHT,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.primary,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.base,
  },
  boxFocused: {
    borderWidth: 2,
    borderColor: colors.text.primary,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.text.primary,
    textAlign: 'auto',
    paddingVertical: 0,
  },
  clearBtn: {
    marginStart: spacing.sm,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  caption: {
    ...typography.caption,
    color: colors.accentDark,
    marginTop: spacing.xs,
    marginStart: CIRCLE_SIZE + spacing.sm,
  },
  captionAR: {
    lineHeight: typography.caption.lineHeight * arabicLineHeightMultiplier,
  },
  ctaWrap: {
    marginTop: spacing.lg,
  },
  cta: {
    height: BOX_HEIGHT,
    borderRadius: radii.button,
    backgroundColor: colors.cta.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: {
    ...typography.bodyEmphasis,
    color: colors.cta.onPrimary,
  },
});

export default TwoInputShell;
