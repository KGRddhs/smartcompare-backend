/**
 * CameraHelpOverlay — Bundle D Task 1.F.4 (R17).
 *
 * Three-step explainer surfaced from the ? button on ScanCameraScreen.
 * Copy is i18n-resolved (`home.camera.help.*`); approved vocabulary per
 * Bundle D anchor R17 — no `couldn't` / `try again` / `failed to` /
 * `تعذر` / `فشل` / `estimated`.
 *
 * Rendered as a translucent Modal so the camera viewfinder stays partly
 * visible behind the explainer; tap-anywhere closes via `onClose`. No
 * haptics on open/close per Build Principle #4 (overlay open isn't in
 * the approved chip/stage/winner vocabulary).
 */

import React from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';

interface CameraHelpOverlayProps {
  visible: boolean;
  onClose: () => void;
}

export function CameraHelpOverlay({ visible, onClose }: CameraHelpOverlayProps) {
  const { t } = useTranslation();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      {/* Backdrop is a tap-to-close target; activeOpacity=1 avoids the
          dimming flash on tap. Inner card swallows the press with its
          own non-bubbling TouchableOpacity wrap. */}
      <TouchableOpacity
        activeOpacity={1}
        onPress={onClose}
        style={styles.backdrop}
        testID="camera-help-overlay"
      >
        <TouchableOpacity activeOpacity={1} style={styles.card}>
          <View style={styles.headerRow}>
            <Text style={styles.title}>
              {t('home.camera.help.title')}
            </Text>
            <TouchableOpacity
              testID="camera-help-overlay-close"
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel={t('home.camera.help.close')}
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            >
              <X size={22} color={colors.text.primary} />
            </TouchableOpacity>
          </View>

          <View style={styles.step}>
            <Text style={styles.stepNumber}>1</Text>
            <Text style={styles.stepText}>
              {t('home.camera.help.step1')}
            </Text>
          </View>
          <View style={styles.step}>
            <Text style={styles.stepNumber}>2</Text>
            <Text style={styles.stepText}>
              {t('home.camera.help.step2')}
            </Text>
          </View>
          <View style={styles.step}>
            <Text style={styles.stepNumber}>3</Text>
            <Text style={styles.stepText}>
              {t('home.camera.help.step3')}
            </Text>
          </View>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  card: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    padding: spacing.lg,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    flex: 1,
  },
  step: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginTop: spacing.sm,
  },
  stepNumber: {
    ...typography.body,
    color: colors.accent,
    fontWeight: '600',
    width: 24,
  },
  stepText: {
    ...typography.body,
    color: colors.text.primary,
    flex: 1,
  },
});
