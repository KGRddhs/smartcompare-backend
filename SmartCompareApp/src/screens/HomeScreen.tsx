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
import { Camera, Search, Link2, RotateCcw, ImageIcon, X } from 'lucide-react-native';
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
import { useComparisonCounter } from '../hooks/useComparisonCounter';

const RECENT_SEARCHES_KEY = '@qaren_recent_searches';
const MAX_RECENT = 5;
const MIN_IMAGES = 2;
const MAX_IMAGES = 4;

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout?: () => void;
};

type InputMode = 'scan' | 'url';

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
      Alert.alert('Need More Products', `Please capture at least ${MIN_IMAGES} products to compare.`);
      return;
    }
    if (!canCompare) {
      navigation.navigate('Paywall' as any);
      return;
    }

    setIsProcessing(true);
    setDetectedProduct(null);

    try {
      const imageUris = capturedImages.map((img) => img.uri);
      const result = await identifyFromImages(imageUris, 'bahrain');

      if (result.action === 'comparison' && result.success) {
        await increment();
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        navigation.navigate('Results', { result });
      } else if (result.action === 'need_second_product' && result.success) {
        setDetectedProduct(result.products[0]);
      } else {
        const errorMsg =
          ('error' in result && result.error) ||
          'Could not identify products. Try clearer photos.';
        Alert.alert('Identification Failed', errorMsg);
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
          navigation.navigate('Results', { result: data });
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
    try {
      const response = await api.post('/api/v1/url/compare', {
        url1: urlInput.trim(),
        url2: url2Input.trim(),
        region: 'bahrain',
        selected_category: selectedCategory,
      });
      if (response.data.success) {
        await increment();
        navigation.navigate('Results', { result: response.data });
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

  return (
    <SafeAreaView style={styles.container}>
      {/* Header: logo + search bar */}
      <View style={styles.header}>
        <Text style={styles.logo}>{t('app.name')}</Text>
        <TouchableOpacity
          style={styles.searchBar}
          onPress={() => setSearchOverlayVisible(true)}
          activeOpacity={0.7}
        >
          <Search size={18} color={colors.text.placeholder} />
          <Text style={styles.searchPlaceholder}>{t('home.search.placeholder')}</Text>
        </TouchableOpacity>
      </View>

      {/* Category chips */}
      <CategorySelector value={selectedCategory} onChange={setSelectedCategory} />

      {/* Camera viewfinder or permission request */}
      <View style={styles.cameraArea}>
        {!cameraPermissionGranted ? (
          <View style={styles.permissionCard}>
            <Camera size={48} color={colors.text.secondary} />
            <Text style={styles.permissionTitle}>Camera Permission Needed</Text>
            <Text style={styles.permissionText}>
              Qaren needs camera access to photograph products for comparison.
            </Text>
            <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
              <Text style={styles.permissionButtonText}>Grant Permission</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.galleryFallback} onPress={pickFromGallery}>
              <Text style={styles.galleryFallbackText}>Or pick from gallery</Text>
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
                  Found: {detectedProduct.brand} {detectedProduct.name}
                </Text>
                <Text style={styles.detectedSubtitle}>
                  Only 1 product identified. Take another photo of a different product.
                </Text>
                <TouchableOpacity
                  style={styles.retakeButton}
                  onPress={() => setDetectedProduct(null)}
                >
                  <Text style={styles.retakeButtonText}>Take Another Photo</Text>
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
                    <Text style={styles.processingText}>Identifying products...</Text>
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
                          Compare {capturedImages.length} Products
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
              placeholder="Product 1 URL (Amazon, Noon, etc.)"
              placeholderTextColor={colors.text.placeholder}
              value={urlInput}
              onChangeText={setUrlInput}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TextInput
              style={styles.urlInput}
              placeholder="Product 2 URL"
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
                <Text style={styles.urlCompareButtonText}>Compare URLs</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Mode chips + counter */}
      <View style={styles.bottomBar}>
        <View style={styles.modeChips}>
          <TouchableOpacity
            style={[styles.modeChip, inputMode === 'scan' && styles.modeChipActive]}
            onPress={() => setInputMode('scan')}
          >
            <Camera size={14} color={inputMode === 'scan' ? '#FFF' : colors.text.secondary} />
            <Text style={[styles.modeChipText, inputMode === 'scan' && styles.modeChipTextActive]}>
              {t('home.scan')}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.modeChip, inputMode === 'url' && styles.modeChipActive]}
            onPress={() => setInputMode('url')}
          >
            <Link2 size={14} color={inputMode === 'url' ? '#FFF' : colors.text.secondary} />
            <Text style={[styles.modeChipText, inputMode === 'url' && styles.modeChipTextActive]}>
              {t('home.url')}
            </Text>
          </TouchableOpacity>
        </View>

        <ComparisonCounter used={used} total={total} />
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
          onClose={() => setSearchOverlayVisible(false)}
          onSubmit={handleTextCompare}
          recentSearches={recentSearches}
        />
      </Modal>
    </SafeAreaView>
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
    paddingBottom: spacing.sm,
    gap: spacing.md,
  },
  logo: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
  },
  searchBar: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  searchPlaceholder: {
    ...typography.body,
    color: colors.text.placeholder,
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

  // Bottom bar
  bottomBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  modeChips: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  modeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.secondary,
  },
  modeChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  modeChipText: {
    ...typography.caption,
    color: colors.text.secondary,
    fontWeight: '500',
  },
  modeChipTextActive: {
    color: '#FFF',
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
