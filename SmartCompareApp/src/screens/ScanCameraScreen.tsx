/**
 * Cal-AI-style fullscreen camera modal.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 *
 * Wires:
 *   - <CameraView /> background with `expo-camera` permissions hook
 *   - shutter button → takePictureAsync → next empty slot
 *   - gallery button → ImagePicker.launchImageLibraryAsync → next empty slot
 *   - flash button → cycles off | on | auto
 *   - Compare CTA → only renders when both slots are non-null; navigates
 *     to Results with `vision_products: [uri0, uri1]`
 *   - × close preserves slot state in a module-scoped cache so the user
 *     can dismiss + return without losing captures.
 */
import React, { useRef, useState } from 'react';
import {
  View,
  SafeAreaView,
  StyleSheet,
  TouchableOpacity,
  Text,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
// Bundle B/C/D Task 3.2 — Reanimated press-scale on the shutter button.
// Worklet-native; runs entirely on the UI thread.
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import {
  X,
  HelpCircle,
  Camera,
  Image as ImageIcon,
  Zap,
  Check,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';
import { motion } from '../theme/motion';
import ImageSlotRow, { Slots, Slot } from '../components/ImageSlotRow';
import ScannerReticle from '../components/ScannerReticle';

type FlashMode = 'off' | 'on' | 'auto';
const FLASH_CYCLE: FlashMode[] = ['off', 'on', 'auto'];

type Props = {
  navigation: {
    goBack: () => void;
    navigate: (route: string, params?: any) => void;
  };
  route: any;
};

// Module-scoped cache preserves slots across modal dismiss/reopen so the
// user can step out (e.g., to tweak a setting) and return without losing
// captures. Cleared on Compare CTA fire (or via __resetScanCameraCacheForTests
// in test environments).
let _slotsCache: Slots = [null, null];

// Test-only helper so test files can reset the module cache between
// scenarios. Production code does not call this.
export function __resetScanCameraCacheForTests() {
  _slotsCache = [null, null];
}

function nextEmptyIndex(slots: Slots): 0 | 1 | null {
  if (slots[0] === null) return 0;
  if (slots[1] === null) return 1;
  return null;
}

export default function ScanCameraScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const [permission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [slots, setSlots] = useState<Slots>(_slotsCache);
  const [flash, setFlash] = useState<FlashMode>('off');
  // Bundle B/C/D Task 3.2 — press-scale on the shutter. Tactile feedback
  // without flashing the whole frame; 80ms in / 120ms out feels snappy
  // without competing with the actual capture flash.
  const shutterScale = useSharedValue(1);
  const shutterAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: shutterScale.value }],
  }));
  const onShutterPressIn = () => {
    shutterScale.value = withTiming(0.95, { duration: 80 });
  };
  const onShutterPressOut = () => {
    shutterScale.value = withTiming(1, { duration: 120 });
  };
  const fireShutterHaptic = () => {
    try {
      const maybePromise = Haptics.impactAsync(
        Haptics.ImpactFeedbackStyle.Light
      );
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => { /* haptic engine unavailable */ });
      }
    } catch {
      /* synchronous haptic failure — silently no-op */
    }
  };

  // Bundle B § 4.3 — 3-part "ready to compare" celebration. Fires once on
  // partial → both-filled transition. Reverse direction dims silently with
  // no haptic.
  const slot0Scale = useSharedValue(1);
  const slot1Scale = useSharedValue(1);
  const ctaCelebrationOpacity = useSharedValue(0);
  const ctaCelebrationGlow = useSharedValue(0);
  const justFlippedReadyRef = useRef(false);

  const fireReadyHaptic = () => {
    try {
      const maybePromise = Haptics.notificationAsync(
        Haptics.NotificationFeedbackType.Success
      );
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => { /* haptic engine unavailable */ });
      }
    } catch {
      /* synchronous haptic failure — silently no-op */
    }
  };

  const updateSlots = (next: Slots) => {
    const wasReady = slots[0] !== null && slots[1] !== null;
    const isReady = next[0] !== null && next[1] !== null;
    _slotsCache = next;
    setSlots(next);

    if (!wasReady && isReady && !justFlippedReadyRef.current) {
      justFlippedReadyRef.current = true;
      const spring = motion.springConfig.chip;
      slot0Scale.value = withSequence(
        withSpring(1.12, spring),
        withSpring(1.0, spring)
      );
      slot1Scale.value = withSequence(
        withSpring(1.12, spring),
        withSpring(1.0, spring)
      );
      ctaCelebrationOpacity.value = withTiming(1.0, { duration: 200 });
      ctaCelebrationGlow.value = withTiming(12, { duration: 240 });
      fireReadyHaptic();
    } else if (wasReady && !isReady) {
      justFlippedReadyRef.current = false;
      ctaCelebrationOpacity.value = withTiming(0, { duration: 300 });
      ctaCelebrationGlow.value = withTiming(0, { duration: 300 });
    }
  };

  const slot0AnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: slot0Scale.value }],
  }));
  const slot1AnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: slot1Scale.value }],
  }));
  const ctaAnimStyle = useAnimatedStyle(() => ({
    opacity: ctaCelebrationOpacity.value,
    shadowColor: colors.accent,
    shadowOpacity: ctaCelebrationGlow.value > 0 ? 0.45 : 0,
    shadowRadius: ctaCelebrationGlow.value,
    shadowOffset: { width: 0, height: 0 },
  }));

  const onCapture = async () => {
    const idx = nextEmptyIndex(slots);
    if (idx === null) return;
    try {
      const photo = await cameraRef.current?.takePictureAsync?.();
      if (!photo?.uri) return;
      const next: Slots = [slots[0], slots[1]];
      next[idx] = { uri: photo.uri } as Slot;
      updateSlots(next);
    } catch {
      // Slot stays empty on capture failure; not user-facing here.
    }
  };

  const onGalleryPick = async () => {
    const idx = nextEmptyIndex(slots);
    if (idx === null) return;
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
      });
      if (result.canceled || !result.assets?.[0]?.uri) return;
      const next: Slots = [slots[0], slots[1]];
      next[idx] = { uri: result.assets[0].uri } as Slot;
      updateSlots(next);
    } catch {
      // Slot stays empty on picker failure.
    }
  };

  const onFlashCycle = () => {
    const i = FLASH_CYCLE.indexOf(flash);
    setFlash(FLASH_CYCLE[(i + 1) % FLASH_CYCLE.length]);
  };

  const onCompare = () => {
    const visionProducts = slots
      .filter((s): s is { uri: string } => s !== null)
      .map((s) => s.uri);
    if (visionProducts.length < 2) return;
    _slotsCache = [null, null];
    navigation.navigate('Results', {
      vision_products: visionProducts,
    } as any);
  };

  const bothFilled = slots[0] !== null && slots[1] !== null;

  if (!permission?.granted) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity
            testID="scan-camera-close"
            onPress={() => navigation.goBack()}
            accessibilityRole="button"
            accessibilityLabel={t('home.camera.a11y.close')}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <X color={colors.text.onInverse} size={28} />
          </TouchableOpacity>
        </View>
        <View testID="scan-camera-permission" style={styles.permissionPad}>
          <Camera size={48} color={colors.text.onInverse} />
          <Text style={styles.permissionText}>
            {t('home.permission.title')}
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        flash={flash}
      />
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="scan-camera-close"
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel={t('home.camera.a11y.close')}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <X color={colors.text.onInverse} size={28} />
        </TouchableOpacity>
        <TouchableOpacity
          testID="scan-camera-help"
          accessibilityRole="button"
          accessibilityLabel={t('home.camera.a11y.help')}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <HelpCircle color={colors.text.onInverse} size={28} />
        </TouchableOpacity>
      </View>
      <ScannerReticle />
      <View style={styles.bottomArea}>
        <ImageSlotRow slots={slots} onChange={updateSlots} />
        {bothFilled && (
          <Animated.View
            testID="scan-celebration-overlay"
            pointerEvents="box-none"
            style={[styles.celebrationOverlay]}
          >
            <Animated.View style={[styles.slotPulse, styles.slotPulseLeft, slot0AnimStyle]}>
              <Check size={14} color={colors.bg.primary} strokeWidth={3} />
            </Animated.View>
            <Animated.View style={[styles.slotPulse, styles.slotPulseRight, slot1AnimStyle]}>
              <Check size={14} color={colors.bg.primary} strokeWidth={3} />
            </Animated.View>
          </Animated.View>
        )}
        {bothFilled && (
          <Animated.View style={ctaAnimStyle}>
            <TouchableOpacity
              testID="compare-cta"
              style={styles.compareCta}
              onPress={onCompare}
              accessibilityRole="button"
            >
              <Text style={styles.compareCtaText}>
                {t('home.camera.compareCta')}
              </Text>
            </TouchableOpacity>
          </Animated.View>
        )}
        <View style={styles.shutterRow}>
          <TouchableOpacity
            testID="flash-button"
            onPress={onFlashCycle}
            accessibilityRole="button"
            accessibilityLabel={t('home.camera.a11y.flash')}
            accessibilityState={{ checked: flash !== 'off' }}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            style={styles.sideButton}
          >
            <Zap
              color={flash === 'off' ? colors.text.onInverse : colors.accent}
              size={26}
            />
          </TouchableOpacity>
          <Animated.View style={shutterAnimStyle}>
            <TouchableOpacity
              testID="shutter-button"
              onPress={() => {
                fireShutterHaptic();
                onCapture();
              }}
              onPressIn={onShutterPressIn}
              onPressOut={onShutterPressOut}
              accessibilityRole="button"
              accessibilityLabel={t('home.camera.a11y.shutter')}
              style={styles.shutter}
              disabled={nextEmptyIndex(slots) === null}
            >
              <View style={styles.shutterInner} />
            </TouchableOpacity>
          </Animated.View>
          <TouchableOpacity
            testID="gallery-button"
            onPress={onGalleryPick}
            accessibilityRole="button"
            accessibilityLabel={t('home.camera.a11y.gallery')}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            style={styles.sideButton}
          >
            <ImageIcon color={colors.text.onInverse} size={26} />
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.inverse,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.md,
  },
  bottomArea: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: spacing['2xl'],
    alignItems: 'center',
  },
  shutterRow: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    alignItems: 'center',
    width: '100%',
    marginTop: spacing.base,
  },
  shutter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: colors.text.onInverse,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
  },
  shutterInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.text.onInverse,
  },
  sideButton: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareCta: {
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderRadius: radii.chip,
    backgroundColor: colors.accent,
    marginBottom: spacing.base,
  },
  compareCtaText: {
    ...typography.body,
    color: colors.text.onInverse,
    fontWeight: '700',
  },
  permissionPad: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing['2xl'],
  },
  permissionText: {
    ...typography.body,
    color: colors.text.onInverse,
    marginTop: spacing.lg,
    textAlign: 'center',
  },
  // Bundle B § 4.3 — celebration overlay sits above the ImageSlotRow,
  // pointer-events transparent so taps still reach the underlying slots.
  celebrationOverlay: {
    position: 'absolute',
    top: -28,
    left: 0,
    right: 0,
    height: 24,
    flexDirection: 'row',
    justifyContent: 'center',
  },
  slotPulse: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  slotPulseLeft: {
    marginEnd: spacing.lg,
  },
  slotPulseRight: {
    marginStart: spacing.lg,
  },
});
