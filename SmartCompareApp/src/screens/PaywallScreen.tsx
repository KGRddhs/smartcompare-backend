/**
 * Qaren - Paywall Screen
 * Bottom sheet overlay showing usage status, tier comparison, and upgrade CTA.
 * Accepts optional usageStatus from USAGE_LIMIT error or fetches from backend.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { Check, Crown, Zap } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { getUsageStatus, UsageStatus } from '../services/usageService';

interface PaywallScreenProps {
  visible: boolean;
  onDismiss: () => void;
  /** Pre-populated from USAGE_LIMIT error detail, or fetched on mount */
  initialUsage?: {
    tier?: string;
    reason?: string;
    remaining?: { daily: number; monthly: number; lifetime_free: number };
  };
}

export default function PaywallScreen({ visible, onDismiss, initialUsage }: PaywallScreenProps) {
  const { t } = useTranslation();
  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible && !usage) {
      setLoading(true);
      getUsageStatus().then((data) => {
        setUsage(data);
        setLoading(false);
      });
    }
  }, [visible]);

  const tier = usage?.tier || initialUsage?.tier || 'free';
  const reason = initialUsage?.reason;
  const usedMonthly = usage?.used?.monthly ?? 0;
  const limitMonthly = usage?.limits?.monthly ?? 10;

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

          {/* Usage status */}
          {loading ? (
            <ActivityIndicator size="small" color={colors.accent} style={{ marginBottom: spacing.lg }} />
          ) : (
            <View style={styles.usageSection}>
              {reason && (
                <Text style={styles.limitMessage}>
                  {reason === 'daily_limit' ? t('paywall.dailyLimit') : t('paywall.monthlyLimit')}
                </Text>
              )}
              <Text style={styles.usageText}>
                {t('paywall.usageMessage', { used: usedMonthly, limit: limitMonthly })}
              </Text>
              {/* Progress bar */}
              <View style={styles.progressBar}>
                <View
                  style={[
                    styles.progressFill,
                    { width: `${Math.min(100, (usedMonthly / limitMonthly) * 100)}%` },
                    usedMonthly >= limitMonthly && styles.progressFillFull,
                  ]}
                />
              </View>
            </View>
          )}

          {/* Tier comparison */}
          <View style={styles.tierRow}>
            {/* Free tier card */}
            <View style={[styles.tierCard, tier === 'free' && styles.tierCardCurrent]}>
              <Zap size={20} color={colors.text.secondary} />
              <Text style={styles.tierName}>{t('paywall.free.title')}</Text>
              <Text style={styles.tierDetail}>{t('paywall.free.daily', { count: 3 })}</Text>
              <Text style={styles.tierDetail}>{t('paywall.free.monthly', { count: 10 })}</Text>
              {tier === 'free' && (
                <View style={styles.currentBadge}>
                  <Text style={styles.currentBadgeText}>{t('paywall.free.current')}</Text>
                </View>
              )}
            </View>

            {/* Premium tier card */}
            <View style={[styles.tierCard, styles.tierCardPremium]}>
              <Crown size={20} color={colors.accent} />
              <Text style={[styles.tierName, { color: colors.accent }]}>{t('paywall.premium.title')}</Text>
              <Text style={styles.tierDetail}>{t('paywall.premium.daily', { count: 10 })}</Text>
              <Text style={styles.tierDetail}>{t('paywall.premium.monthly', { count: 70 })}</Text>
            </View>
          </View>

          {/* Premium features */}
          <View style={styles.features}>
            {features.map((f, i) => (
              <View key={i} style={styles.featureRow}>
                <Check size={18} color={colors.accent} />
                <Text style={styles.featureText}>{f}</Text>
              </View>
            ))}
          </View>

          {/* Subscribe button */}
          <TouchableOpacity
            style={styles.subscribeButton}
            activeOpacity={0.8}
            onPress={() => {
              // Placeholder — will integrate Tap Payments / Benefit Pay
            }}
          >
            <Text style={styles.subscribeText}>{t('paywall.subscribe')}</Text>
          </TouchableOpacity>

          {/* Payment providers note */}
          <Text style={styles.paymentNote}>{t('paywall.payment')}</Text>

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
    marginBottom: spacing.lg,
  },

  // Usage section
  usageSection: {
    marginBottom: spacing.xl,
    alignItems: 'center',
  },
  limitMessage: {
    ...typography.body,
    fontWeight: '600',
    color: colors.warning,
    marginBottom: spacing.xs,
  },
  usageText: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  progressBar: {
    width: '80%',
    height: 6,
    backgroundColor: colors.bg.secondary,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.accent,
    borderRadius: 3,
  },
  progressFillFull: {
    backgroundColor: colors.warning,
  },

  // Tier comparison
  tierRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  tierCard: {
    flex: 1,
    padding: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    gap: spacing.xs,
  },
  tierCardCurrent: {
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.secondary,
  },
  tierCardPremium: {
    borderColor: colors.accent,
    borderWidth: 2,
    backgroundColor: colors.accentLight,
  },
  tierName: {
    ...typography.body,
    fontWeight: '700',
    color: colors.text.primary,
  },
  tierDetail: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  currentBadge: {
    marginTop: spacing.xs,
    backgroundColor: colors.border.medium,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.chip,
  },
  currentBadgeText: {
    ...typography.small,
    color: colors.text.secondary,
    fontWeight: '600',
  },

  // Features
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

  // Subscribe
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
  paymentNote: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  social: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.base,
  },
});
