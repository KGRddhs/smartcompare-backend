/**
 * Qaren - Home Screen (Camera-First)
 * Absorbs camera functionality from old CameraScreen.
 * Layout: logo + search bar + category chips + camera viewfinder + capture + mode chips + counter
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
  ScrollView,
  Image,
  TextInput,
  Modal,
} from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
import { Camera, RotateCcw, ImageIcon, X } from 'lucide-react-native';
// Custom mode icons (frontend-visual Task #51) — drop-in replacements for
// Lucide Camera/Link2/Edit3 inside the 3-mode chip rail per design § 5a
// "Mode | 3 | Scan, Link, Type". Lucide imports above stay for the
// camera card body (capture row, gallery, flip-camera) per § 5a's
// "~15 Lucide icons retained (utility)" provision.
import { ScanIcon, LinkIcon, TypeIcon } from '../icons';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { colors, spacing, radii, typography, shadows } from '../theme';
import { RootStackParamList, CapturedImage, IdentifiedProduct } from '../types';
import { healthCheck, streamComparison, parseApiError, identifyFromImages } from '../services/api';
import api from '../services/api';
import { getSavedUser, User } from '../services/authService';
import { isUsageLimitError, getUsageLimitDetail } from '../services/usageService';
import CategorySelector from '../components/CategorySelector';
import { SearchOverlay } from '../components/SearchOverlay';
import { ComparisonCounter } from '../components/ComparisonCounter';
import { BonusCountdownCard } from '../components/BonusCountdownCard';
import { useComparisonCounter } from '../hooks/useComparisonCounter';
import { getReferralStatus } from '../services/referralService';

const RECENT_SEARCHES_KEY = '@qaren_recent_searches';
const MAX_RECENT = 5;
const MIN_IMAGES = 2;
const MAX_IMAGES = 4;

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout?: () => void;
};

/**
 * Phase 3 redesign — 3 equal-weight input modes per design § 4a.
 * - 'scan' renders the live camera card
 * - 'link' renders inline URL inputs in the same card real-estate
 * - 'type' opens the SearchOverlay modal (text search)
 */
type InputMode = 'scan' | 'url' | 'type';

export default function HomeScreen({ navigation, onLogout }: HomeScreenProps) {
  const { t } = useTranslation();
  const [user, setUser] = useState<User | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  // Camera state (absorbed from CameraScreen)
  const [permission, requestPermission] = useCameraPermissions();
  const [capturedImages, setCapturedImages] = useState<CapturedImage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [facing, setFacing] = useState<CameraType>('back');
  const [detectedProduct, setDetectedProduct] = useState<IdentifiedProduct | null>(null);
  const cameraRef = useRef<CameraView>(null);

  // Input states
  const [inputMode, setInputMode] = useState<InputMode>('scan');
  const [selectedCategory, setSelectedCategory] = useState<string>('electronics');
  const [searchOverlayVisible, setSearchOverlayVisible] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState('');
  const [url2Input, setUrl2Input] = useState('');
  const abortRef = useRef<(() => void) | null>(null);

  // Comparison counter
  const { used, total, canCompare, shouldShowPaywall, increment } = useComparisonCounter();

  /**
   * Phase 4 § 4e — invitee bonus countdown surface. Polls
   * /api/v1/referrals/status once on focus; the BonusCountdownCard
   * renders nothing when no active bonus, so this is safe to mount
   * unconditionally. Backend's /referrals/status response shape
   * exposes monthly_bonus_comparisons; per-bonus referrer_name +
   * expires_at metadata may not yet be on the response, so we read
   * them defensively (any-shape) and the card guards on missing
   * data.
   */
  const [bonusInfo, setBonusInfo] = useState<{
    bonusRemaining: number;
    referrerName?: string;
    expiresAt?: Date;
  }>({ bonusRemaining: 0 });

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
          // Fire-and-forget — referral system may be disabled (503) or
          // anonymous user. Either way we just don't show the card.
        }
      })();
      return () => {
        cancelled = true;
      };
    }, [])
  );

  /**
   * Min-display floor (1.2s) for the Home→Results transition per design
   * § 3 ("Even cached responses (~200ms) show loading for 1.2s minimum
   * so the brand moment lands"). Each compare-handler stamps this ref
   * at the start of work; `navigateToResultsWithFloor` uses the elapsed
   * delta to delay navigation if we got back a cached response too fast.
   * For real (non-cache) responses, the floor is already exceeded, so
   * navigation is effectively immediate.
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
      if (remaining === 0) {
        advance();
      } else {
        setTimeout(advance, remaining);
      }
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
      if (stored) setRecentSearches(JSON.parse(stored));
    } catch {}
  };

  const saveRecentSearch = async (query: string) => {
    const updated = [query, ...recentSearches.filter((s) => s !== query)].slice(0, MAX_RECENT);
    setRecentSearches(updated);
    await AsyncStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
  };

  // --- Camera functions (from CameraScreen) ---

  const takePicture = async () => {
    if (cameraRef.current && capturedImages.length < MAX_IMAGES) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          base64: false,
          exif: false,
          imageType: 'jpg',
        });
        if (photo) {
          if (detectedProduct) setDetectedProduct(null);
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
          setCapturedImages((prev) => [
            ...prev,
            { uri: photo.uri, width: photo.width, height: photo.height },
          ]);
        }
      } catch (error) {
        console.error('Error taking picture:', error);
        Alert.alert(t('common.error'), t('home.errors.camera'));
      }
    }
  };

  const pickFromGallery = async () => {
    const remainingSlots = MAX_IMAGES - capturedImages.length;
    if (remainingSlots <= 0) {
      Alert.alert('Maximum Reached', `You can only compare up to ${MAX_IMAGES} products.`);
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      selectionLimit: remainingSlots,
      quality: 0.8,
      exif: false,
    });
    if (!result.canceled && result.assets) {
      if (detectedProduct) setDetectedProduct(null);
      const newImages: CapturedImage[] = result.assets.map((asset) => ({
        uri: asset.uri,
        width: asset.width,
        height: asset.height,
      }));
      setCapturedImages((prev) => [...prev, ...newImages]);
    }
  };

  const removeImage = (index: number) => {
    setDetectedProduct(null);
    setCapturedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const toggleCameraFacing = () => {
    setFacing((current) => (current === 'back' ? 'front' : 'back'));
  };

  const handleIdentifyAndCompare = async () => {
    if (capturedImages.length < MIN_IMAGES) {
      Alert.alert(
        t('home.capture.more_title', { defaultValue: 'One more shot' }),
        t('home.capture.more_body', {
          defaultValue: `Snap ${MIN_IMAGES} products to compare them side-by-side.`,
          n: MIN_IMAGES,
        })
      );
      return;
    }
    if (!canCompare) {
      navigation.navigate('Paywall' as any);
      return;
    }

    setIsProcessing(true);
    setDetectedProduct(null);
    loadingStartedAtRef.current = Date.now();

    try {
      const imageUris = capturedImages.map((img) => img.uri);
      const result = await identifyFromImages(imageUris, 'bahrain');

      if (result.action === 'comparison' && result.success) {
        await increment();
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        navigateToResultsWithFloor(result);
      } else if (result.action === 'need_second_product' && result.success) {
        setDetectedProduct(result.products[0]);
      } else {
        // Per § 4g — confident, never scary. Reframe as "sharper match" not "failed".
        const fallback = t('home.capture.sharper_body', {
          defaultValue: 'Try a clearer angle — sharper match every time.',
        });
        const detail = ('error' in result && result.error) ? result.error : fallback;
        Alert.alert(
          t('home.capture.sharper_title', { defaultValue: 'Sharper match coming up' }),
          detail
        );
      }
    } catch (error: any) {
      if (isUsageLimitError(error)) {
        const detail = getUsageLimitDetail(error);
        navigation.navigate('Paywall' as any, { initialUsage: detail });
      } else if (error.response?.status === 429) {
        Alert.alert('Rate Limited', 'Too many requests. Please wait a moment.');
      } else if (error.message?.includes('Network')) {
        Alert.alert(t('common.error'), t('home.errors.connection'));
      } else {
        Alert.alert(t('common.error'), parseApiError(error).message);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  // --- Text comparison (SSE streaming) ---

  const handleTextCompare = (query: string) => {
    if (!query.trim()) return;
    if (!canCompare) {
      navigation.navigate('Paywall' as any);
      return;
    }

    setSearchOverlayVisible(false);
    saveRecentSearch(query);
    setLoading(true);
    setStatusMessage(t('results.loading.finding'));
    loadingStartedAtRef.current = Date.now();
    let navigated = false;

    const { subscribe, abort } = streamComparison(query.trim(), {
      selected_category: selectedCategory,
    });
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
        if (isUsageLimitError(error)) {
          const detail = getUsageLimitDetail(error);
          navigation.navigate('Paywall' as any, { initialUsage: detail });
          return;
        }
        Alert.alert(t('common.error'), error.message || t('home.errors.comparison'));
      },
    });
  };

  // --- URL comparison ---

  const handleUrlCompare = async () => {
    if (!urlInput.trim() || !url2Input.trim()) {
      Alert.alert('Enter URLs', 'Paste product URLs from Amazon, Noon, etc.');
      return;
    }
    const isValidUrl = (url: string): boolean => {
      try {
        const parsed = new URL(url);
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
      } catch {
        return false;
      }
    };
    if (!isValidUrl(urlInput.trim()) || !isValidUrl(url2Input.trim())) {
      Alert.alert('Invalid URL', 'Please enter valid product URLs (http:// or https://)');
      return;
    }
    if (!canCompare) {
      navigation.navigate('Paywall' as any);
      return;
    }

    setLoading(true);
    loadingStartedAtRef.current = Date.now();
    try {
      const response = await api.post('/api/v1/url/compare', {
        url1: urlInput.trim(),
        url2: url2Input.trim(),
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
      if (isUsageLimitError(error)) {
        const detail = getUsageLimitDetail(error);
        navigation.navigate('Paywall' as any, { initialUsage: detail });
      } else {
        Alert.alert(t('common.error'), parseApiError(error).message);
      }
    } finally {
      setLoading(false);
    }
  };

  // --- Render ---

  const cameraPermissionGranted = permission?.granted;

  // Phase 3 redesign — § 4a. The mode chip rail also handles the 'type'
  // mode by opening the existing SearchOverlay; the chip stays sticky-active
  // while the overlay is up so the visual feedback is consistent.
  const handleModeChange = (mode: InputMode) => {
    setInputMode(mode);
    if (mode === 'type') setSearchOverlayVisible(true);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Compressed brand header + hero per § 4a. */}
      <View style={styles.header}>
        <Text style={styles.logo}>{t('app.name')}</Text>
      </View>

      <Text style={styles.hero}>{t('home.hero')}</Text>

      {/* Category chips */}
      <CategorySelector value={selectedCategory} onChange={setSelectedCategory} />

      {/* Camera viewfinder or permission request — capped at ~40% screen height
          per design § 4a. */}
      <View style={styles.cameraArea} testID="home-camera-card">
        {!cameraPermissionGranted ? (
          <View style={styles.permissionCard}>
            <Camera size={48} color={colors.text.secondary} />
            <Text style={styles.permissionTitle}>{t('home.permission.title')}</Text>
            <Text style={styles.permissionText}>{t('home.permission.body')}</Text>
            <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
              <Text style={styles.permissionButtonText}>
                {t('home.permission.cta')}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.galleryFallback} onPress={pickFromGallery}>
              <Text style={styles.galleryFallbackText}>
                {t('home.permission.gallery_link')}
              </Text>
            </TouchableOpacity>
          </View>
        ) : inputMode === 'scan' ? (
          <View style={styles.cameraContainer}>
            <CameraView ref={cameraRef} style={styles.camera} facing={facing}>
              {/* Overlay instruction */}
              <View style={styles.cameraOverlay}>
                <Text style={styles.cameraOverlayText}>
                  {capturedImages.length === 0
                    ? 'Point at first product'
                    : `Product ${capturedImages.length + 1} of ${MAX_IMAGES}`}
                </Text>
              </View>
            </CameraView>

            {/* Detected product banner */}
            {detectedProduct && (
              <View style={styles.detectedBanner}>
                <Text style={styles.detectedTitle}>
                  {t('home.detected.found', {
                    brand: detectedProduct.brand,
                    name: detectedProduct.name,
                    defaultValue: `Got ${detectedProduct.brand} ${detectedProduct.name}`,
                  })}
                </Text>
                <Text style={styles.detectedSubtitle}>
                  {t('home.detected.add_another', {
                    defaultValue: 'Add a second product to compare them side-by-side.',
                  })}
                </Text>
                <TouchableOpacity
                  style={styles.retakeButton}
                  onPress={() => setDetectedProduct(null)}
                >
                  <Text style={styles.retakeButtonText}>
                    {t('home.detected.cta', { defaultValue: 'Snap another' })}
                  </Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Captured images preview strip */}
            {capturedImages.length > 0 && !detectedProduct && (
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.previewStrip}
                contentContainerStyle={styles.previewStripContent}
              >
                {capturedImages.map((image, index) => (
                  <View key={index} style={styles.previewItem}>
                    <Image source={{ uri: image.uri }} style={styles.previewImage} />
                    <TouchableOpacity
                      style={styles.removeButton}
                      onPress={() => removeImage(index)}
                    >
                      <X size={10} color="#FFF" />
                    </TouchableOpacity>
                  </View>
                ))}
              </ScrollView>
            )}

            {/* Camera controls */}
            {!detectedProduct && (
              <View style={styles.cameraControls}>
                {isProcessing ? (
                  <View style={styles.processingContainer}>
                    <ActivityIndicator size="large" color={colors.accent} />
                    <Text style={styles.processingText}>
                      {t('home.processing', { defaultValue: 'Pulling in product details' })}
                    </Text>
                  </View>
                ) : (
                  <>
                    <View style={styles.captureRow}>
                      {/* Gallery */}
                      <TouchableOpacity style={styles.sideButton} onPress={pickFromGallery}>
                        <ImageIcon size={22} color="#FFF" />
                      </TouchableOpacity>

                      {/* Capture button (emerald ring) */}
                      <TouchableOpacity
                        style={[
                          styles.captureButton,
                          capturedImages.length >= MAX_IMAGES && styles.captureButtonDisabled,
                        ]}
                        onPress={takePicture}
                        disabled={capturedImages.length >= MAX_IMAGES}
                      >
                        <View style={styles.captureButtonInner} />
                      </TouchableOpacity>

                      {/* Flip camera */}
                      <TouchableOpacity style={styles.sideButton} onPress={toggleCameraFacing}>
                        <RotateCcw size={22} color="#FFF" />
                      </TouchableOpacity>
                    </View>

                    {/* Compare button */}
                    {capturedImages.length >= MIN_IMAGES && (
                      <TouchableOpacity
                        style={styles.compareButton}
                        onPress={handleIdentifyAndCompare}
                      >
                        <Text style={styles.compareButtonText}>
                          {t('home.capture.compareCta', { count: capturedImages.length })}
                        </Text>
                      </TouchableOpacity>
                    )}
                  </>
                )}
              </View>
            )}
          </View>
        ) : (
          /* URL input mode */
          <View style={styles.urlContainer}>
            <TextInput
              style={styles.urlInput}
              placeholder={t('home.url.placeholder1', {
                defaultValue: 'First product link (Amazon, Noon, etc.)',
              })}
              placeholderTextColor={colors.text.placeholder}
              value={urlInput}
              onChangeText={setUrlInput}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TextInput
              style={styles.urlInput}
              placeholder={t('home.url.placeholder2', {
                defaultValue: 'Second product link',
              })}
              placeholderTextColor={colors.text.placeholder}
              value={url2Input}
              onChangeText={setUrl2Input}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TouchableOpacity
              style={[styles.urlCompareButton, loading && { opacity: 0.5 }]}
              onPress={handleUrlCompare}
              disabled={!serverOnline || loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFF" size="small" />
              ) : (
                <Text style={styles.urlCompareButtonText}>
                  {t('home.url.cta', { defaultValue: 'Compare links' })}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* 3-mode equal chip rail per design § 4a — Scan / Link / Type.
          Active state via accessibilityState.selected; on-device polish
          adds the small emerald dot under the active chip in Phase 5. */}
      <View style={styles.modeChipRail}>
        <ModeChip
          testID="home-mode-scan"
          label={t('home.mode.scan', { defaultValue: 'Scan' })}
          icon={<ScanIcon size={14} color={inputMode === 'scan' ? colors.cta.onPrimary : colors.text.secondary} />}
          active={inputMode === 'scan'}
          onPress={() => handleModeChange('scan')}
        />
        <ModeChip
          testID="home-mode-link"
          label={t('home.mode.link', { defaultValue: 'Link' })}
          icon={<LinkIcon size={14} color={inputMode === 'url' ? colors.cta.onPrimary : colors.text.secondary} />}
          active={inputMode === 'url'}
          onPress={() => handleModeChange('url')}
        />
        <ModeChip
          testID="home-mode-type"
          label={t('home.mode.type', { defaultValue: 'Type' })}
          icon={<TypeIcon size={14} color={inputMode === 'type' ? colors.cta.onPrimary : colors.text.secondary} />}
          active={inputMode === 'type'}
          onPress={() => handleModeChange('type')}
        />
      </View>

      <View style={styles.bottomBar}>
        {/* Phase 4 § 4e — bonus countdown surface. Mounts above the
            comparison counter when a referral bonus is active; renders
            nothing otherwise (the card guards on bonusRemaining +
            expiresAt internally). Backend exposes per-bonus referrer
            name + expires_at on the /referrals/status response when
            available; falls back to "a friend" + no countdown until
            then. */}
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

      {/* Loading status overlay */}
      {loading && statusMessage ? (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="small" color={colors.accent} />
          <Text style={styles.loadingText}>{statusMessage}</Text>
        </View>
      ) : null}

      {/* Search overlay */}
      <Modal visible={searchOverlayVisible} animationType="slide" statusBarTranslucent>
        <SearchOverlay
          visible={searchOverlayVisible}
          onClose={() => {
            setSearchOverlayVisible(false);
            // If user closed the overlay without searching, fall back to scan
            // so the camera card surface stays useful.
            if (inputMode === 'type') setInputMode('scan');
          }}
          onSubmit={handleTextCompare}
          recentSearches={recentSearches}
        />
      </Modal>
    </SafeAreaView>
  );
}

/**
 * Equal-weight mode chip per design § 4a. Active state surfaced via
 * accessibilityState.selected (testable) and visual fill (emerald). The
 * small active-state dot below the chip lands in Phase 5 polish.
 */
interface ModeChipProps {
  testID: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onPress: () => void;
}

function ModeChip({ testID, label, icon, active, onPress }: ModeChipProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      style={[styles.modeChip, active && styles.modeChipActive]}
    >
      {icon}
      <Text style={[styles.modeChipText, active && styles.modeChipTextActive]}>
        {label}
      </Text>
    </TouchableOpacity>
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
  /** Compressed hero per design § 4a — "Compare anything." 16pt body weight. */
  hero: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  /** 3-mode chip rail — equal weight, sits below the camera card. */
  modeChipRail: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },

  // Camera area
  cameraArea: {
    flex: 1,
    marginHorizontal: spacing.base,
    borderRadius: radii.card,
    overflow: 'hidden',
    backgroundColor: '#000',
  },
  cameraContainer: {
    flex: 1,
  },
  camera: {
    flex: 1,
  },
  cameraOverlay: {
    position: 'absolute',
    top: spacing.lg,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  cameraOverlayText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '600',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.sm,
    borderRadius: radii.chip,
  },

  // Detected product banner
  detectedBanner: {
    backgroundColor: '#1C1C1E',
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.xl,
    alignItems: 'center',
  },
  detectedTitle: {
    color: colors.accent,
    ...typography.body,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  detectedSubtitle: {
    color: '#AAA',
    ...typography.caption,
    textAlign: 'center',
    marginBottom: spacing.base,
  },
  retakeButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radii.button,
  },
  retakeButtonText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '600',
  },

  // Preview strip
  previewStrip: {
    maxHeight: 80,
    backgroundColor: 'rgba(0,0,0,0.8)',
  },
  previewStripContent: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  previewItem: {
    position: 'relative',
  },
  previewImage: {
    width: 56,
    height: 56,
    borderRadius: spacing.sm,
    borderWidth: 2,
    borderColor: '#FFF',
  },
  removeButton: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: colors.destructive,
    width: 18,
    height: 18,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Camera controls
  cameraControls: {
    backgroundColor: '#000',
    paddingVertical: spacing.base,
    paddingHorizontal: spacing.lg,
  },
  captureRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  captureButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: spacing.xl,
  },
  captureButtonDisabled: {
    opacity: 0.3,
  },
  captureButtonInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#FFF',
  },
  sideButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
  },
  compareButtonText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '700',
  },
  processingContainer: {
    alignItems: 'center',
    paddingVertical: spacing.lg,
  },
  processingText: {
    color: '#FFF',
    ...typography.body,
    marginTop: spacing.md,
  },

  // URL mode
  urlContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.md,
  },
  urlInput: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    padding: spacing.base,
    ...typography.body,
    color: colors.text.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  urlCompareButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
  },
  urlCompareButtonText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '600',
  },

  // Permission card
  permissionCard: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['3xl'],
    backgroundColor: colors.bg.secondary,
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

  // Bottom bar — now just hosts the freemium counter; mode chips moved
  // above the camera card per § 4a redesign.
  bottomBar: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  modeChip: {
    /* Equal-weight chips per § 4a — flex:1 so all three sit on a single
       line and split the available width evenly. */
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

  // Loading overlay
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
