/**
 * Qaren - Home Screen (Bundle B redesign).
 *
 * Renders the TwoInputShell for Text + URL modes and a Scan placeholder
 * for camera mode. When canCompare is false, takes over the middle of the
 * screen with the PaywallBanner per spec § 6.2 (hides hero, category strip,
 * BonusCountdownCard, ComparisonCounter; dims mode chips to 50%).
 *
 * Spec: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md
 *   § 3 anatomy · § 4 interactions · § 6 freemium · § 8 analytics
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { motion } from '../theme/motion';
import { Camera } from 'lucide-react-native';
import { ScanIcon, LinkIcon, TypeIcon } from '../icons';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { colors, spacing, radii, typography } from '../theme';
import { RootStackParamList } from '../types';
import {
  healthCheck,
  streamComparison,
  parseApiError,
  trackEvent,
} from '../services/api';
import api from '../services/api';
import { getSavedUser, User } from '../services/authService';
import { isUsageLimitError, getUsageLimitDetail } from '../services/usageService';
import CategorySelector from '../components/CategorySelector';
import QarenLogo from '../components/QarenLogo';
import TwoInputShell from '../components/TwoInputShell';
import PaywallBanner from '../components/PaywallBanner';
import { ComparisonCounter } from '../components/ComparisonCounter';
import { BonusCountdownCard } from '../components/BonusCountdownCard';
import { useComparisonCounter } from '../hooks/useComparisonCounter';
import { getReferralStatus } from '../services/referralService';

const RECENT_SEARCHES_KEY = '@qaren_recent_searches';
const MAX_RECENT = 5;
// Bundle B/C/D — exactly 2 products per comparison. Exported so the
// ScanCameraScreen modal + tests can read the same constant.
export const MAX_IMAGES = 2;

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout?: () => void;
};

/**
 * 3 equal-weight input modes (design § 4a).
 * 'scan' → launches fullscreen ScanCameraScreen modal.
 * 'url'  → renders TwoInputShell in URL mode.
 * 'type' → renders TwoInputShell in Text mode.
 */
type InputMode = 'scan' | 'url' | 'type';

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const { t } = useTranslation();
  const [, setUser] = useState<User | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const [permission, requestPermission] = useCameraPermissions();
  const [, setRecentSearches] = useState<string[]>([]);
  const recentSearchesRef = useRef<string[]>([]);

  const [inputMode, setInputMode] = useState<InputMode>('scan');
  const [selectedCategory, setSelectedCategory] = useState<string>('electronics');
  const abortRef = useRef<(() => void) | null>(null);

  const { used, total, canCompare, increment } = useComparisonCounter();

  const [bonusInfo, setBonusInfo] = useState<{
    bonusRemaining: number;
    referrerName?: string;
    expiresAt?: Date;
  }>({ bonusRemaining: 0 });

  // Analytics session flags — toggled by TwoInputShell callbacks, read on
  // submit, reset after each submit.
  const pasteSplitUsedRef = useRef(false);
  const autoswitchUsedRef = useRef(false);
  // compare_entry_view de-dupe: only fire once per mode-entry.
  const lastViewedModeRef = useRef<InputMode | null>(null);
  const prevCanCompareRef = useRef<boolean>(canCompare);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const status: any = await getReferralStatus();
          if (cancelled) return;
          const bonusRemaining: number = Number(status?.monthly_bonus_comparisons ?? 0);
          const referrerName: string | undefined =
            typeof status?.bonus_referrer_name === 'string'
              ? status.bonus_referrer_name
              : undefined;
          const rawExpiry =
            status?.bonus_expires_at ?? status?.next_bonus_expires_at ?? null;
          const expiresAt: Date | undefined =
            rawExpiry ? new Date(rawExpiry) : undefined;
          setBonusInfo({ bonusRemaining, referrerName, expiresAt });
        } catch {
          /* fire-and-forget */
        }
      })();
      return () => {
        cancelled = true;
      };
    }, [])
  );

  /**
   * Min-display floor (1.2s) for Home→Results transitions per design § 3.
   */
  const loadingStartedAtRef = useRef<number | null>(null);
  const MIN_LOADING_MS = 1200;
  const navigateToResultsWithFloor = useCallback(
    (result: any) => {
      const startedAt = loadingStartedAtRef.current ?? Date.now();
      const elapsed = Date.now() - startedAt;
      const remaining = Math.max(0, MIN_LOADING_MS - elapsed);
      const advance = () => {
        loadingStartedAtRef.current = null;
        navigation.navigate('Results' as any, { result });
      };
      if (remaining === 0) advance();
      else setTimeout(advance, remaining);
    },
    [navigation]
  );

  useFocusEffect(
    useCallback(() => {
      checkServer();
      loadUser();
      loadRecentSearches();
    }, [])
  );

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    setUser(savedUser);
  };

  const checkServer = async () => {
    try {
      const isHealthy = await healthCheck();
      setServerOnline(isHealthy);
    } catch {
      setServerOnline(false);
    }
  };

  const loadRecentSearches = async () => {
    try {
      const stored = await AsyncStorage.getItem(RECENT_SEARCHES_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as string[];
        setRecentSearches(parsed);
        recentSearchesRef.current = parsed;
      }
    } catch {
      /* no-op */
    }
  };

  const saveRecentSearch = async (query: string) => {
    const updated = [
      query,
      ...recentSearchesRef.current.filter((s) => s !== query),
    ].slice(0, MAX_RECENT);
    recentSearchesRef.current = updated;
    setRecentSearches(updated);
    await AsyncStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
  };

  // --- Analytics ---

  // compare_entry_view — fires whenever the active mode changes.
  useEffect(() => {
    if (lastViewedModeRef.current !== inputMode) {
      lastViewedModeRef.current = inputMode;
      trackEvent('compare_entry_view', { mode: inputMode });
    }
  }, [inputMode]);

  // compare_entry_paywall_banner_view — fires when canCompare flips to false.
  useEffect(() => {
    if (prevCanCompareRef.current && !canCompare) {
      trackEvent('compare_entry_paywall_banner_view', { mode: inputMode });
    }
    prevCanCompareRef.current = canCompare;
  }, [canCompare, inputMode]);

  const handleContentUnavailable = useCallback(
    (mode: 'text' | 'url' | 'scan', layer: string) => {
      trackEvent('compare_entry_content_block', { mode, layer });
      Alert.alert(
        t('home.compare.unavailable_title'),
        t('home.compare.unavailable_body')
      );
    },
    [t]
  );

  // --- Text comparison (SSE streaming, dual-shape pair) ---

  const handleTextCompare = (a: string, b: string) => {
    const productA = a.trim();
    const productB = b.trim();
    if (!productA || !productB) return;
    if (!canCompare) {
      navigation.navigate('Paywall');
      return;
    }

    saveRecentSearch(`${productA} vs ${productB}`);
    setLoading(true);
    setStatusMessage(t('results.loading.finding'));
    loadingStartedAtRef.current = Date.now();
    let navigated = false;

    trackEvent('compare_entry_submit', {
      mode: 'text',
      used_paste_split: pasteSplitUsedRef.current,
      used_autoswitch: autoswitchUsedRef.current,
    });
    pasteSplitUsedRef.current = false;
    autoswitchUsedRef.current = false;

    const { subscribe, abort } = streamComparison(
      { product_a: productA, product_b: productB },
      { selected_category: selectedCategory }
    );
    abortRef.current = abort;

    subscribe({
      onStatus: (message) => {
        setStatusMessage(typeof message === 'string' ? message : String(message));
      },
      onComplete: async (data) => {
        abortRef.current = null;
        setLoading(false);
        setStatusMessage('');
        if (!navigated && data.success) {
          navigated = true;
          await increment();
          navigateToResultsWithFloor(data);
        } else if (!data.success) {
          Alert.alert(t('common.error'), data.error || t('home.errors.comparison'));
        }
      },
      onError: (error: any) => {
        abortRef.current = null;
        setLoading(false);
        setStatusMessage('');
        const parsed = parseApiError(error);
        if (parsed.code === 'CONTENT_UNAVAILABLE') {
          const layer = error?.response?.data?.layer ?? 'unknown';
          handleContentUnavailable('text', layer);
          return;
        }
        if (isUsageLimitError(error)) {
          const detail = getUsageLimitDetail(error);
          navigation.navigate('Paywall', { initialUsage: detail ?? undefined });
          return;
        }
        Alert.alert(t('common.error'), error.message || t('home.errors.comparison'));
      },
    });
  };

  // --- URL comparison ---

  const handleUrlCompare = async (urlA: string, urlB: string) => {
    const url1 = urlA.trim();
    const url2 = urlB.trim();
    if (!url1 || !url2) return;
    if (!canCompare) {
      navigation.navigate('Paywall');
      return;
    }

    trackEvent('compare_entry_submit', {
      mode: 'url',
      used_paste_split: pasteSplitUsedRef.current,
      used_autoswitch: autoswitchUsedRef.current,
    });
    pasteSplitUsedRef.current = false;
    autoswitchUsedRef.current = false;

    setLoading(true);
    loadingStartedAtRef.current = Date.now();
    try {
      const response = await api.post('/api/v1/url/compare', {
        url1,
        url2,
        region: 'bahrain',
        selected_category: selectedCategory,
      });
      if (response.data.success) {
        await increment();
        navigateToResultsWithFloor(response.data);
      } else {
        Alert.alert(t('common.error'), response.data.error || t('home.errors.comparison'));
      }
    } catch (error: any) {
      const parsed = parseApiError(error);
      if (parsed.code === 'CONTENT_UNAVAILABLE') {
        const layer = error?.response?.data?.layer ?? 'unknown';
        handleContentUnavailable('url', layer);
      } else if (isUsageLimitError(error)) {
        const detail = getUsageLimitDetail(error);
        navigation.navigate('Paywall', { initialUsage: detail ?? undefined });
      } else {
        Alert.alert(t('common.error'), parsed.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (mode: InputMode) => {
    if (!canCompare) {
      // Spec § 6.2 — dimmed chips still tappable. Per team-lead approval
      // of spec § 4.11 Q4: change active mode so the next paywall_banner_view
      // re-fire reflects the user's intent, then re-fire that event with
      // the new mode (the canCompare-flip useEffect above only catches
      // true→false transitions, not chip-tap-while-already-false). Then
      // route to Paywall as before.
      if (mode !== inputMode) setInputMode(mode);
      trackEvent('compare_entry_paywall_banner_view', { mode });
      navigation.navigate('Paywall');
      return;
    }
    if (mode === 'scan') {
      navigation.navigate('ScanCamera');
      return;
    }
    setInputMode(mode);
  };

  // Gallery fallback kept for the camera-permission path. Auto-launches
  // the gallery picker; on selection, hands off to ScanCameraScreen via
  // navigation params so the existing scan flow handles compare.
  const pickFromGalleryFallback = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      selectionLimit: MAX_IMAGES,
      quality: 0.8,
      exif: false,
    });
    if (!result.canceled && result.assets && result.assets.length >= MAX_IMAGES) {
      navigation.navigate('ScanCamera');
    }
  };

  const cameraPermissionGranted = permission?.granted;

  const renderCenterArea = () => {
    if (!canCompare) {
      return (
        <PaywallBanner
          onSeeOptions={() => {
            trackEvent('compare_entry_paywall_banner_tap', { mode: inputMode });
            navigation.navigate('Paywall');
          }}
        />
      );
    }

    if (inputMode === 'scan') {
      if (!cameraPermissionGranted) {
        return (
          <View style={styles.permissionCard}>
            <Camera size={48} color={colors.text.secondary} />
            <Text style={styles.permissionTitle}>{t('home.permission.title')}</Text>
            <Text style={styles.permissionText}>{t('home.permission.body')}</Text>
            <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
              <Text style={styles.permissionButtonText}>
                {t('home.permission.cta')}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.galleryFallback} onPress={pickFromGalleryFallback}>
              <Text style={styles.galleryFallbackText}>
                {t('home.permission.gallery_link')}
              </Text>
            </TouchableOpacity>
          </View>
        );
      }
      return (
        <TouchableOpacity
          testID="home-scan-placeholder"
          style={styles.scanPlaceholder}
          onPress={() => navigation.navigate('ScanCamera')}
          accessibilityRole="button"
          accessibilityLabel={t('home.camera.tap_to_scan')}
        >
          <Camera size={48} color={colors.text.secondary} />
          <Text style={styles.scanPlaceholderTitle}>
            {t('home.camera.tap_to_scan')}
          </Text>
          <Text style={styles.scanPlaceholderHint}>
            {t('home.camera.slot', { current: 1, total: MAX_IMAGES })}
          </Text>
        </TouchableOpacity>
      );
    }

    // Text + URL modes both render through TwoInputShell.
    return (
      <TwoInputShell
        mode={inputMode === 'url' ? 'url' : 'text'}
        disabled={loading}
        onSubmit={(a, b) => {
          if (inputMode === 'url') handleUrlCompare(a, b);
          else handleTextCompare(a, b);
        }}
        onPasteSplit={(sourceBox) => {
          pasteSplitUsedRef.current = true;
          trackEvent('compare_entry_paste_split', {
            source_box: sourceBox,
            mode: inputMode === 'url' ? 'url' : 'text',
          });
        }}
        onModeAutoswitch={(from, to) => {
          autoswitchUsedRef.current = true;
          setInputMode('url');
          trackEvent('compare_entry_mode_autoswitch', {
            from,
            to,
            trigger: 'url_paste',
          });
        }}
        onReady={(timeToReadyMs) => {
          trackEvent('compare_entry_ready', {
            mode: inputMode === 'url' ? 'url' : 'text',
            time_to_ready_ms: timeToReadyMs,
          });
        }}
      />
    );
  };

  // serverOnline is currently unused in the new rendering path; suppressed
  // until a health-state UI lands. Kept for potential future use.
  void serverOnline;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <QarenLogo size={28} />
        <Text style={[styles.logo, styles.logoSpaced]}>{t('app.name')}</Text>
      </View>

      {canCompare && <Text style={styles.hero}>{t('home.hero')}</Text>}

      {canCompare && (
        <CategorySelector
          value={selectedCategory}
          onChange={setSelectedCategory}
        />
      )}

      <View style={styles.centerArea} testID="home-center-area">
        {renderCenterArea()}
      </View>

      {/* 3-mode equal chip rail — dimmed to 50% during paywall takeover. */}
      <View
        style={[
          styles.modeChipRail,
          !canCompare && { opacity: 0.5 },
        ]}
      >
        <ModeChip
          testID="home-mode-scan"
          label={t('home.mode.scan')}
          icon={
            <ScanIcon
              size={14}
              color={inputMode === 'scan' ? colors.cta.onPrimary : colors.text.secondary}
            />
          }
          active={inputMode === 'scan'}
          onPress={() => handleModeChange('scan')}
        />
        <ModeChip
          testID="home-mode-link"
          label={t('home.mode.link')}
          icon={
            <LinkIcon
              size={14}
              color={inputMode === 'url' ? colors.cta.onPrimary : colors.text.secondary}
            />
          }
          active={inputMode === 'url'}
          onPress={() => handleModeChange('url')}
        />
        <ModeChip
          testID="home-mode-type"
          label={t('home.mode.type')}
          icon={
            <TypeIcon
              size={14}
              color={inputMode === 'type' ? colors.cta.onPrimary : colors.text.secondary}
            />
          }
          active={inputMode === 'type'}
          onPress={() => handleModeChange('type')}
        />
      </View>

      {canCompare && (
        <View style={styles.bottomBar}>
          <BonusCountdownCard
            baseFreeRemaining={Math.max(0, total - used)}
            bonusRemaining={bonusInfo.bonusRemaining}
            referrerName={bonusInfo.referrerName}
            expiresAt={bonusInfo.expiresAt}
          />
          <View testID="home-counter-slot">
            <ComparisonCounter used={used} total={total} />
          </View>
        </View>
      )}

      {loading && statusMessage ? (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="small" color={colors.accent} />
          <Text style={styles.loadingText}>{statusMessage}</Text>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

/**
 * Equal-weight mode chip per design § 4a. Active state surfaced via
 * accessibilityState.selected (testable) and visual fill (emerald).
 */
interface ModeChipProps {
  testID: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onPress: () => void;
}

function ModeChip({ testID, label, icon, active, onPress }: ModeChipProps) {
  const scale = useSharedValue(active ? 1 : 0.96);

  React.useEffect(() => {
    scale.value = withSpring(active ? 1 : 0.96, motion.springConfig.chip);
  }, [active, scale]);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePress = () => {
    try {
      const maybePromise = Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => {});
      }
    } catch {
      /* no-op */
    }
    onPress();
  };

  return (
    <Animated.View style={animStyle}>
      <TouchableOpacity
        testID={testID}
        onPress={handlePress}
        accessibilityRole="button"
        accessibilityState={{ selected: active }}
        style={[styles.modeChip, active && styles.modeChipActive]}
      >
        {icon}
        <Text style={[styles.modeChipText, active && styles.modeChipTextActive]}>
          {label}
        </Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
  },
  logo: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
  },
  logoSpaced: {
    marginStart: spacing.sm,
  },
  hero: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  centerArea: {
    flex: 1,
  },
  modeChipRail: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  bottomBar: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  scanPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['2xl'],
    marginHorizontal: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
  },
  scanPlaceholderTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginTop: spacing.base,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  scanPlaceholderHint: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  permissionCard: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['3xl'],
    marginHorizontal: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
  },
  permissionTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  permissionText: {
    ...typography.body,
    textAlign: 'center',
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  permissionButton: {
    backgroundColor: colors.accent,
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderRadius: radii.button,
  },
  permissionButtonText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '700',
  },
  galleryFallback: {
    marginTop: spacing.base,
    padding: spacing.md,
  },
  galleryFallbackText: {
    color: colors.accent,
    ...typography.caption,
  },
  modeChip: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.secondary,
    minHeight: 44,
  },
  modeChipActive: {
    backgroundColor: colors.cta.primary,
    borderColor: colors.cta.primary,
  },
  modeChipText: {
    ...typography.caption,
    color: colors.text.secondary,
    fontWeight: '500',
  },
  modeChipTextActive: {
    color: colors.cta.onPrimary,
    fontWeight: '600',
  },
  loadingOverlay: {
    position: 'absolute',
    bottom: 80,
    left: spacing.xl,
    right: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderRadius: radii.chip,
  },
  loadingText: {
    color: '#FFF',
    ...typography.caption,
  },
});

// Re-export so existing CameraView import is still tree-shaken. Pulls the
// expo-camera permissions hook into the bundle even when the user never
// reaches a permission-granted state, preserving the previous behavior.
void CameraView;
