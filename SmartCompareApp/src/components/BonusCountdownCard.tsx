/**
 * BonusCountdownCard — Home surface for invitee bonus state.
 *
 * Phase 4 Task 41. Per design § 4e bonus-expiry mechanics:
 * - Active bonus → "{baseFreeRemaining + bonusRemaining} free this month"
 *   + "{bonusRemaining} from {referrer} (expires 2d 14h)" with a
 *   per-minute-updating countdown
 * - No active bonus (bonusRemaining=0, no expiresAt, or already expired)
 *   → "{baseFreeRemaining} free anytime"
 * - Both zero → renders nothing
 *
 * Pure presentational. Parent owns fetching the referral status from
 * /api/v1/referrals/status and passing the snapshot in. The component
 * holds an interval that re-renders once per minute so the time label
 * decays without requiring the parent to push updates.
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';

interface Props {
  /** Lifetime free comparisons still available (the always-on 3). */
  baseFreeRemaining: number;
  /** Invitee bonus comparisons still available (Loop 2 reward). */
  bonusRemaining: number;
  /** The friend who triggered the bonus. Optional — falls back to "a friend". */
  referrerName?: string;
  /** When the bonus expires. Component renders no-bonus state if past. */
  expiresAt?: Date;
}

const TICK_MS = 60 * 1000;

export function BonusCountdownCard({
  baseFreeRemaining,
  bonusRemaining,
  referrerName,
  expiresAt,
}: Props) {
  const { t } = useTranslation();
  // Drives the per-minute re-render; we don't need the value, just the
  // setState to re-trigger render so the formatted label decays.
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!expiresAt) return;
    const id = setInterval(() => {
      setTick((n) => n + 1);
    }, TICK_MS);
    return () => clearInterval(id);
  }, [expiresAt]);

  const totalRemaining = baseFreeRemaining + bonusRemaining;
  if (totalRemaining <= 0) return null;

  const now = Date.now();
  const expiryMs = expiresAt ? expiresAt.getTime() : 0;
  const remainingMs = expiryMs - now;
  const bonusActive = bonusRemaining > 0 && expiresAt != null && remainingMs > 0;

  return (
    <View testID="bonus-countdown-card" style={styles.card}>
      <Text style={styles.headlineLine}>
        {t('home.bonus.headline', {
          count: totalRemaining,
          defaultValue: `${totalRemaining} free comparisons available`,
        })}
      </Text>
      {bonusActive ? (
        <Text style={styles.bonusLine}>
          <Text testID="bonus-countdown-bonus">
            {t('home.bonus.fromReferrer', {
              count: bonusRemaining,
              referrer: referrerName ?? t('home.bonus.aFriend', { defaultValue: 'a friend' }),
              defaultValue: `• ${bonusRemaining} from ${referrerName ?? 'a friend'}`,
            })}
          </Text>
          <Text>{' '}</Text>
          <Text testID="bonus-countdown-time" style={styles.timeLine}>
            {t('home.bonus.expiresIn', {
              time: formatRemaining(remainingMs),
              defaultValue: `(expires ${formatRemaining(remainingMs)})`,
            })}
          </Text>
        </Text>
      ) : (
        <Text style={styles.bonusLine}>
          {t('home.bonus.anytime', {
            count: baseFreeRemaining,
            defaultValue: `• ${baseFreeRemaining} anytime`,
          })}
        </Text>
      )}
    </View>
  );
}

/**
 * Format remaining ms as "Xd Yh" / "Xh Ym" / "<1m". Avoids jittery
 * second-precision so the per-minute interval stays sufficient.
 */
function formatRemaining(ms: number): string {
  const totalMinutes = Math.max(0, Math.floor(ms / 60000));
  if (totalMinutes <= 0) return '<1m';
  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    alignSelf: 'flex-start',
    gap: spacing.xs,
  },
  headlineLine: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  bonusLine: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  timeLine: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
  },
});
