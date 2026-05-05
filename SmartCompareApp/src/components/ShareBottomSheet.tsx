/**
 * ShareBottomSheet
 *
 * Privacy-toggled, multi-target share sheet for referrals (F2.3).
 * Renders 3 togglable privacy options + 1 locked-off (budget never shared)
 * + 5 share targets (WhatsApp, Copy, X, Telegram, Snapchat). On any target
 * tap: POST /referrals/share to create the invite (Loop 1 trigger), then
 * fan-out to the platform-specific share intent with the returned share_link.
 *
 * Copy verbatim from design Section 3.2 (story-format pre-filled message)
 * and 3.3 (privacy toggles).
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  Modal,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Switch,
  Linking,
  Share,
  Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTranslation } from 'react-i18next';
import { MessageCircle, Copy as CopyIcon, Send, AtSign, Camera } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { createShare, ReferralError, ShareTarget, CreateShareResult } from '../services/referralService';

export interface ShareBottomSheetComparison {
  id: string;
  productA: string;
  productB: string;
  winnerName?: string;
}

export interface ShareBottomSheetProps {
  visible: boolean;
  comparison: ShareBottomSheetComparison;
  deviceFingerprintHash?: string;
  onClose: () => void;
  onShared: (result: CreateShareResult) => void;
}

interface PrivacyToggles {
  name: boolean;
  result: boolean;
  reasons: boolean;
  // budget intentionally absent here — locked OFF, never shared
}

const TARGETS: { key: ShareTarget; iconKey: string; labelKey: string }[] = [
  { key: 'whatsapp', iconKey: 'whatsapp', labelKey: 'referrals.share.target.whatsapp' },
  { key: 'copy', iconKey: 'copy', labelKey: 'referrals.share.target.copy' },
  { key: 'x', iconKey: 'x', labelKey: 'referrals.share.target.x' },
  { key: 'telegram', iconKey: 'telegram', labelKey: 'referrals.share.target.telegram' },
  { key: 'snapchat', iconKey: 'snapchat', labelKey: 'referrals.share.target.snapchat' },
];

function buildShareIntent(target: ShareTarget, message: string, link: string): string {
  // Pre-formatted full text (message already includes link via i18n interpolation)
  const text = encodeURIComponent(message);
  switch (target) {
    case 'whatsapp':
      return `whatsapp://send?text=${text}`;
    case 'x':
      return `https://x.com/intent/post?text=${text}`;
    case 'telegram':
      // Telegram share-url accepts ?url= + ?text=
      return `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${text}`;
    case 'snapchat':
    case 'copy':
    case 'other':
    default:
      return '';
  }
}

function TargetIcon({ iconKey }: { iconKey: string }) {
  // lucide-react-native doesn't ship branded icons; use generic fallbacks tinted
  // by accent. Brand glyphs (WA/X/TG/Snap) live in the static admin pages but
  // we keep the in-app sheet glyph-light to avoid trademark drag.
  const size = 24;
  const color = colors.text.primary;
  switch (iconKey) {
    case 'whatsapp':
      return <MessageCircle size={size} color={color} />;
    case 'copy':
      return <CopyIcon size={size} color={color} />;
    case 'x':
      return <AtSign size={size} color={color} />;
    case 'telegram':
      return <Send size={size} color={color} />;
    case 'snapchat':
      return <Camera size={size} color={color} />;
    default:
      return <Send size={size} color={color} />;
  }
}

export default function ShareBottomSheet({
  visible,
  comparison,
  deviceFingerprintHash,
  onClose,
  onShared,
}: ShareBottomSheetProps) {
  const { t } = useTranslation();
  const [privacy, setPrivacy] = useState<PrivacyToggles>({ name: true, result: true, reasons: true });
  const [submitting, setSubmitting] = useState<ShareTarget | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const previewMessage = t('referrals.share.message', {
    productA: comparison.productA,
    productB: comparison.productB,
    winner: comparison.winnerName ?? comparison.productB,
  });

  const togglePrivacy = (key: keyof PrivacyToggles) => {
    try { Haptics.selectionAsync(); } catch {}
    setPrivacy((p) => ({ ...p, [key]: !p[key] }));
  };

  const handleTargetPress = async (target: ShareTarget) => {
    if (submitting) return;
    setErrorMessage(null);
    setSubmitting(target);
    try {
      const result = await createShare({
        comparison_id: comparison.id,
        share_target: target,
        device_fingerprint_hash: deviceFingerprintHash,
        privacy: {
          show_name: privacy.name,
          show_result: privacy.result,
          show_reasons: privacy.reasons,
        },
      });
      // Compose final outgoing message: base story + share_link
      const outgoing = `${previewMessage}\n${result.share_link}`;
      try {
        if (target === 'copy' || target === 'snapchat') {
          // System share sheet — gives user Copy/Snap targets reliably without
          // depending on snapchat-creativekit or expo-clipboard
          await Share.share({ message: outgoing });
        } else {
          const intent = buildShareIntent(target, outgoing, result.share_link);
          if (intent) {
            const can = await Linking.canOpenURL(intent).catch(() => false);
            if (can) {
              await Linking.openURL(intent);
            } else {
              // Graceful fallback to system share sheet
              await Share.share({ message: outgoing });
            }
          } else {
            await Share.share({ message: outgoing });
          }
        }
        try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); } catch {}
        onShared(result);
      } catch {
        // Even if the share intent fails, the invite WAS created server-side —
        // surface success to the parent so the Loop 1 toast still fires.
        onShared(result);
      }
    } catch (err) {
      try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error); } catch {}
      const ref = err as ReferralError;
      if (ref?.code === 'WEEKLY_INVITE_CAP') {
        setErrorMessage(t('referrals.share.error.weeklyCap'));
      } else {
        setErrorMessage(ref?.message ?? t('referrals.share.error.generic'));
      }
    } finally {
      setSubmitting(null);
    }
  };

  if (!visible) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.sheet} accessibilityViewIsModal>
          <View style={styles.handle} />
          <Text style={styles.title}>{t('referrals.share.title')}</Text>
          <Text style={styles.subtitle}>{t('referrals.share.subtitle')}</Text>

          {/* Privacy toggles (3 togglable + 1 locked OFF) */}
          <View style={styles.section}>
            <View style={styles.toggleRow}>
              <Text style={styles.toggleLabel}>{t('referrals.share.toggle.name')}</Text>
              <Switch
                value={privacy.name}
                onValueChange={() => togglePrivacy('name')}
                accessibilityLabel={t('referrals.share.toggle.name')}
                trackColor={{ false: colors.border.medium, true: colors.accent }}
                thumbColor={'#FFFFFF'}
              />
            </View>
            <View style={styles.toggleRow}>
              <Text style={styles.toggleLabel}>{t('referrals.share.toggle.result')}</Text>
              <Switch
                value={privacy.result}
                onValueChange={() => togglePrivacy('result')}
                accessibilityLabel={t('referrals.share.toggle.result')}
                trackColor={{ false: colors.border.medium, true: colors.accent }}
                thumbColor={'#FFFFFF'}
              />
            </View>
            <View style={styles.toggleRow}>
              <Text style={styles.toggleLabel}>{t('referrals.share.toggle.reasons')}</Text>
              <Switch
                value={privacy.reasons}
                onValueChange={() => togglePrivacy('reasons')}
                accessibilityLabel={t('referrals.share.toggle.reasons')}
                trackColor={{ false: colors.border.medium, true: colors.accent }}
                thumbColor={'#FFFFFF'}
              />
            </View>
            {/* Budget — locked OFF per design 3.3 */}
            <View style={[styles.toggleRow, styles.toggleLocked]}>
              <View style={{ flex: 1 }}>
                <Text style={styles.toggleLabel}>{t('referrals.share.toggle.budget')}</Text>
                <Text style={styles.toggleLockedHint}>{t('referrals.share.toggle.budgetLocked')}</Text>
              </View>
              <Switch
                value={false}
                onValueChange={() => { /* locked — ignore */ }}
                disabled
                accessibilityLabel={t('referrals.share.toggle.budget')}
                trackColor={{ false: colors.border.light, true: colors.border.light }}
                thumbColor={colors.border.medium}
              />
            </View>
            <Text style={styles.privacyNote}>{t('referrals.share.privacyNote')}</Text>
          </View>

          {/* Pre-filled message preview */}
          <View style={styles.messagePreview}>
            <Text style={styles.messagePreviewLabel}>{t('referrals.share.messagePreview')}</Text>
            <Text style={styles.messagePreviewText} numberOfLines={4}>
              {previewMessage}
            </Text>
          </View>

          {/* 5 share targets */}
          <View style={styles.targets}>
            {TARGETS.map((target) => {
              const isThisLoading = submitting === target.key;
              const anyLoading = submitting !== null;
              return (
                <TouchableOpacity
                  key={target.key}
                  accessibilityRole="button"
                  accessibilityLabel={t(target.labelKey)}
                  style={[styles.targetButton, anyLoading && !isThisLoading && styles.disabled]}
                  onPress={() => handleTargetPress(target.key)}
                  disabled={anyLoading}
                  activeOpacity={0.7}
                >
                  {isThisLoading ? (
                    <ActivityIndicator size="small" color={colors.accent} />
                  ) : (
                    <TargetIcon iconKey={target.iconKey} />
                  )}
                  <Text style={styles.targetLabel}>{t(target.labelKey)}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}

          <TouchableOpacity
            accessibilityRole="button"
            style={styles.cancelButton}
            onPress={onClose}
            disabled={submitting !== null}
          >
            <Text style={styles.cancelText}>{t('common.cancel')}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.bg.primary,
    borderTopStartRadius: spacing.xl,
    borderTopEndRadius: spacing.xl,
    paddingTop: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingBottom: Platform.OS === 'ios' ? spacing['3xl'] : spacing.xl,
    maxHeight: '90%',
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  section: {
    marginBottom: spacing.base,
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border.light,
  },
  toggleLocked: {
    opacity: 0.6,
  },
  toggleLabel: {
    ...typography.body,
    color: colors.text.primary,
    flex: 1,
  },
  toggleLockedHint: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: 2,
  },
  privacyNote: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  messagePreview: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.md,
    marginBottom: spacing.base,
  },
  messagePreviewLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
  },
  messagePreviewText: {
    ...typography.body,
    color: colors.text.primary,
  },
  targets: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  targetButton: {
    flexBasis: '18%',
    minWidth: 60,
    aspectRatio: 1,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm,
  },
  targetLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  disabled: {
    opacity: 0.5,
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  cancelButton: {
    paddingVertical: spacing.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  cancelText: {
    ...typography.body,
    color: colors.text.secondary,
  },
});
