/**
 * Cal-AI-style fullscreen camera modal.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 *
 * Phase 1: skeleton with close/help affordances + reticle + dual slots.
 * Phase 2 layers in camera capture, gallery picker, and Compare CTA.
 */
import React, { useState } from 'react';
import { View, SafeAreaView, StyleSheet, TouchableOpacity } from 'react-native';
import { X, HelpCircle } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing } from '../theme';
import ImageSlotRow, { Slots } from '../components/ImageSlotRow';
import ScannerReticle from '../components/ScannerReticle';

type Props = {
  navigation: { goBack: () => void; navigate: (route: string, params?: any) => void };
  route: any;
};

export default function ScanCameraScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState<Slots>([null, null]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity
          testID="scan-camera-close"
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel={t('camera.close')}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <X color={colors.text.onInverse} size={28} />
        </TouchableOpacity>
        <TouchableOpacity
          testID="scan-camera-help"
          accessibilityRole="button"
          accessibilityLabel={t('camera.help')}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <HelpCircle color={colors.text.onInverse} size={28} />
        </TouchableOpacity>
      </View>
      <ScannerReticle />
      <View style={styles.bottomArea}>
        <ImageSlotRow slots={slots} onChange={setSlots} />
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
  },
});
