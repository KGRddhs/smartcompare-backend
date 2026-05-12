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
import {
  X,
  HelpCircle,
  Camera,
  Image as ImageIcon,
  Zap,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';
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

  const updateSlots = (next: Slots) => {
    _slotsCache = next;
    setSlots(next);
  };

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
          <TouchableOpacity
            testID="shutter-button"
            onPress={onCapture}
            accessibilityRole="button"
            accessibilityLabel={t('home.camera.a11y.shutter')}
            style={styles.shutter}
            disabled={nextEmptyIndex(slots) === null}
          >
            <View style={styles.shutterInner} />
          </TouchableOpacity>
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
});
