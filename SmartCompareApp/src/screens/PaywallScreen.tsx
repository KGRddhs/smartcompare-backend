/**
 * Qaren - Paywall Screen
 * Bottom sheet overlay with subscription plan cards (placeholder — no real IAP)
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { Check } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';

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
        <TouchableOpacity style={styles.backdrop} onPress={onDismiss} activeOpacity={1} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <Text style={styles.title}>{t('paywall.title')}</Text>

          <View style={styles.planRow}>
            <TouchableOpacity
              style={[styles.planCard, plan === 'monthly' && styles.planCardActive]}
              onPress={() => setPlan('monthly')}
              activeOpacity={0.7}
            >
              <Text style={styles.planLabel}>{t('paywall.monthly')}</Text>
              <Text style={styles.planPrice}>$4.99</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.planCard, plan === 'yearly' && styles.planCardActive]}
              onPress={() => setPlan('yearly')}
              activeOpacity={0.7}
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

          <TouchableOpacity
            style={styles.subscribeButton}
            onPress={() => {
              // TODO: actual subscription via RevenueCat / StoreKit
            }}
            activeOpacity={0.8}
          >
            <Text style={styles.subscribeText}>{t('paywall.subscribe')}</Text>
          </TouchableOpacity>

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
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
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
  title: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  planRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  planCard: {
    flex: 1,
    padding: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
  },
  planCardActive: {
    borderColor: colors.accent,
    borderWidth: 2,
    backgroundColor: colors.accentLight,
  },
  planLabel: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
  },
  planPrice: {
    ...typography.title,
    color: colors.text.primary,
  },
  saveBadge: {
    position: 'absolute',
    top: -10,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.chip,
  },
  saveBadgeText: {
    ...typography.small,
    color: '#FFFFFF',
    fontWeight: '700',
  },
  features: {
    marginBottom: spacing.xl,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  featureText: {
    ...typography.body,
    color: colors.text.primary,
  },
  subscribeButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.base,
    borderRadius: radii.button,
    alignItems: 'center',
  },
  subscribeText: {
    ...typography.body,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  restoreButton: {
    alignSelf: 'center',
    marginTop: spacing.base,
  },
  restoreText: {
    ...typography.caption,
    color: colors.text.secondary,
    textDecorationLine: 'underline',
  },
  social: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.base,
  },
});
