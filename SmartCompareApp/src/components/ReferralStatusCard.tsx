/**
 * ReferralStatusCard
 *
 * Profile-screen card showing the user's referral state per design 4.5:
 *   - Referral code (tap to copy)
 *   - Weekly gifts used / 3
 *   - Monthly bonus comparisons earned
 *   - Lifetime invites that converted (Loop 2 fired)
 *   - Available Deep Review credits
 *
 * Renders nothing when:
 *   - User isn't authenticated (no referral state)
 *   - Backend returns 503 / SERVICE_UNAVAILABLE (ENABLE_REFERRAL_SYSTEM=false)
 *   - Network failure (best-effort, never blocks the rest of Profile)
 *
 * Reads data from GET /api/v1/referrals/status (B2.2). Refreshes on focus.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Share,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTranslation } from 'react-i18next';
import { Gift, Copy as CopyIcon, Sparkles } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { getReferralStatus, ReferralStatus } from '../services/referralService';

const WEEKLY_CAP = 3;

export interface ReferralStatusCardProps {
  /** Re-fetch when this prop changes (e.g. after a successful share). */
  refreshKey?: number;
}

export default function ReferralStatusCard({ refreshKey }: ReferralStatusCardProps) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<ReferralStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getReferralStatus();
      setStatus(result);
      setUnavailable(false);
    } catch {
      // Any failure (503 feature flag off, 401 unauth, network, unknown)
      // collapses to "hide the card" — best-effort UX, the rest of the
      // Profile screen never blocks on referral state.
      setUnavailable(true);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const handleCopyCode = async () => {
    if (!status?.referral_code) return;
    try { Haptics.selectionAsync(); } catch {}
    try {
      // Bundle A §1.3: share the full debate-ending message with code + link
      // (not the bare 9-char code) so the recipient can tap straight through.
      const link = `https://qaren.app/r/${status.referral_code}`;
      const fullMessage = t('referrals.share.messageWithLink', {
        link,
        code: status.referral_code,
      });
      await Share.share({ message: fullMessage });
      setCopied(true);
      try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); } catch {}
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // ignore — user dismissed the share sheet
    }
  };

  if (loading) {
    return (
      <View style={styles.cardLoading} accessibilityLabel={t('referrals.status.loading')}>
        <ActivityIndicator size="small" color={colors.accent} />
      </View>
    );
  }

  if (unavailable || !status) {
    // Silent hide — feature flag off, network down, or anonymous user.
    return null;
  }

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Gift size={18} color={colors.accent} />
        <Text style={styles.headerTitle}>{t('referrals.status.title')}</Text>
      </View>

      <Text style={styles.subtitle}>{t('referrals.status.subtitle')}</Text>

      {/* Referral code with copy affordance */}
      <TouchableOpacity
        style={styles.codeRow}
        onPress={handleCopyCode}
        accessibilityRole="button"
        accessibilityLabel={t('referrals.status.copyCode')}
        activeOpacity={0.7}
      >
        <Text style={styles.codeText}>{status.referral_code}</Text>
        <View style={styles.codeIcon}>
          <CopyIcon size={14} color={copied ? colors.accent : colors.text.secondary} />
          <Text style={[styles.codeAction, copied && { color: colors.accent }]}>
            {copied ? t('referrals.status.copied') : t('referrals.status.copy')}
          </Text>
        </View>
      </TouchableOpacity>

      {/* Stats grid */}
      <View style={styles.statsGrid}>
        <View style={styles.stat}>
          <Text style={styles.statValue}>
            {t('referrals.status.weeklyUsed', {
              used: status.weekly_invites_used,
              total: WEEKLY_CAP,
            })}
          </Text>
          <Text style={styles.statLabel}>{t('referrals.status.weeklyLabel')}</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statValue}>
            {t('referrals.status.bonusValue', { count: status.monthly_bonus_comparisons })}
          </Text>
          <Text style={styles.statLabel}>{t('referrals.status.bonusLabel')}</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statValue}>
            {t('referrals.status.lifetimeValue', { count: status.total_lifetime_redemptions })}
          </Text>
          <Text style={styles.statLabel}>{t('referrals.status.lifetimeLabel')}</Text>
        </View>
      </View>

      {/* Deep Review credits — only when > 0, smart progressive disclosure */}
      {status.deep_review_credits_available > 0 ? (
        <View style={styles.creditsRow}>
          <Sparkles size={14} color={colors.accent} />
          <Text style={styles.creditsText}>
            {t('referrals.status.creditsAvailable', {
              count: status.deep_review_credits_available,
            })}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    marginBottom: spacing.sm,
  },
  cardLoading: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
    marginBottom: spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 80,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  headerTitle: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.xs,
    marginBottom: spacing.base,
  },
  codeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.bg.primary,
    borderRadius: radii.input,
    borderWidth: 1,
    borderColor: colors.border.light,
    marginBottom: spacing.base,
  },
  codeText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.accent,
    letterSpacing: 1,
  },
  codeIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  codeAction: {
    ...typography.small,
    color: colors.text.secondary,
    fontWeight: '500',
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  stat: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  statValue: {
    ...typography.title,
    color: colors.text.primary,
  },
  statLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: 2,
    textAlign: 'center',
  },
  creditsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border.light,
  },
  creditsText: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '500',
  },
});
