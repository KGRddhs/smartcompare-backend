/**
 * PaywallScreen — the honest limit sheet (S69 U2). The app sells no
 * subscription, so the screen behind the `Paywall` route (name and params
 * kept for every call site) only says where the free comparisons stand.
 *
 * State: getUsageStatus() on EVERY mount decides first (the 429 envelope has
 * no counts): remaining.monthly 0 -> monthly (wins over daily), remaining.daily
 * 0 -> daily, else "open". On null / reject: initialUsage.reason, then the
 * "(daily_limit)" / "(monthly_limit)" suffix of initialUsage.error, then
 * initialUsage.remaining, else "unknown" (no counts, no "used up" claim).
 * Reset copy never says "tomorrow": the backend keys roll at 00:00 UTC.
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { X, Clock } from 'lucide-react-native';
import { arabicLineHeightMultiplier, colors, radii, spacing } from '../theme';
import { getUsageStatus, type UsageStatus } from '../services/usageService';
import type { RootStackParamList } from '../types/types';

type PaywallRouteProp = RouteProp<RootStackParamList, 'Paywall'>;
type PaywallNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Paywall'>;
type InitialUsage = NonNullable<NonNullable<RootStackParamList['Paywall']>['initialUsage']>;

export type LimitState =
  | { kind: 'daily'; used?: number; limit?: number }
  | { kind: 'monthly'; used?: number; limit?: number }
  | { kind: 'open'; remaining: number }
  | { kind: 'unknown' };

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** The fetched /usage/status decides first. */
export function stateFromStatus(status: UsageStatus | null | undefined): LimitState | null {
  const rem = status?.remaining;
  if (!status || !rem || !isNum(rem.daily) || !isNum(rem.monthly)) return null;
  if (rem.monthly === 0) {
    return { kind: 'monthly', used: status.used?.monthly, limit: status.limits?.monthly };
  }
  if (rem.daily === 0) {
    return { kind: 'daily', used: status.used?.daily, limit: status.limits?.daily };
  }
  return { kind: 'open', remaining: openRemaining(status) };
}

// Lifetime-free window: /usage/status reports the FULL allowance, but each
// lifetime-free compare still bumps the counters (usage_service.py:360-365).
function openRemaining({ tier, used, limits, remaining: rem }: UsageStatus): number {
  const lf = rem.lifetime_free;
  if (tier !== 'free' || !isNum(lf) || lf <= 0) return Math.min(rem.daily, rem.monthly);
  const headroom = Math.min(limits?.daily - used?.daily, limits?.monthly - used?.monthly);
  return isNum(headroom) ? lf + Math.max(0, headroom - lf) : Math.min(rem.daily, rem.monthly, lf);
}

/** Fallback: the 429 detail the caller passed (no counts on the wire). */
export function stateFromInitial(initial: InitialUsage | undefined): LimitState {
  if (!initial) return { kind: 'unknown' };
  const axis = /monthly/.test(initial.reason ?? '')
    ? 'monthly'
    : /daily/.test(initial.reason ?? '')
      ? 'daily'
      : /\((daily|monthly)_limit\)/.exec(initial.error ?? '')?.[1];
  if (axis === 'monthly' || axis === 'daily') return { kind: axis };
  const rem = initial.remaining;
  if (rem && rem.monthly === 0) return { kind: 'monthly' };
  if (rem && rem.daily === 0) return { kind: 'daily' };
  return { kind: 'unknown' };
}

export default function PaywallScreen() {
  const { t, i18n } = useTranslation();
  const navigation = useNavigation<PaywallNavigationProp>();
  const route = useRoute<PaywallRouteProp>();
  const initialUsage = route.params?.initialUsage;
  const isAR = !!i18n?.language?.startsWith('ar');

  const [fetched, setFetched] = useState<LimitState | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.resolve()
      .then(() => getUsageStatus())
      .then((status) => {
        if (alive) setFetched(stateFromStatus(status));
      })
      .catch(() => {
        // A failed read degrades to the initialUsage fallback; never an alert.
      });
    return () => {
      alive = false;
    };
  }, []);

  const state: LimitState = fetched ?? stateFromInitial(initialUsage);
  const onDismiss = () => navigation.goBack();

  let title: string;
  let counts: string | null = null;
  let resets: string | null;
  switch (state.kind) {
    case 'daily':
      title = t('paywall.dailyLimit');
      if (isNum(state.used) && isNum(state.limit)) {
        counts = t('paywall.limit.today', { used: state.used, limit: state.limit });
      }
      resets = t('paywall.limit.resets_daily');
      break;
    case 'monthly':
      title = t('paywall.monthlyLimit');
      if (isNum(state.used) && isNum(state.limit)) {
        counts = t('paywall.usageMessage', { used: state.used, limit: state.limit });
      }
      resets = t('paywall.limit.resets_monthly');
      break;
    case 'open':
      title = t('paywall.limit.title');
      counts = t('paywall.limit.remaining', { remaining: state.remaining });
      resets = null;
      break;
    default:
      title = t('paywall.limit.title');
      resets = t('paywall.limit.resets_unknown');
  }

  const arLine = (base: number) => (isAR ? { lineHeight: base * arabicLineHeightMultiplier } : null);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          testID="paywall-close"
          onPress={onDismiss}
          accessibilityRole="button"
          accessibilityLabel={t('common.close')}
          style={styles.closeBtn}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <X size={18} color={colors.text.primary} strokeWidth={2.4} />
        </TouchableOpacity>
      </View>

      <View style={styles.body}>
        <View style={styles.iconCircle}>
          <Clock size={28} color={colors.accent} strokeWidth={2.2} />
        </View>
        <Text
          testID="paywall-title"
          accessibilityRole="header"
          style={[styles.title, arLine(TITLE_LINE_HEIGHT)]}
        >
          {title}
        </Text>
        {counts != null ? (
          <Text testID="paywall-counts" style={[styles.counts, arLine(COUNTS_LINE_HEIGHT)]}>
            {counts}
          </Text>
        ) : null}
        {resets != null ? (
          <Text testID="paywall-resets" style={[styles.resets, arLine(RESETS_LINE_HEIGHT)]}>
            {resets}
          </Text>
        ) : null}
      </View>

      <View style={styles.footer}>
        <TouchableOpacity
          testID="paywall-done"
          onPress={onDismiss}
          accessibilityRole="button"
          accessibilityLabel={t('common.done')}
          style={styles.doneBtn}
        >
          <Text style={styles.doneText}>{t('common.done')}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const TITLE_LINE_HEIGHT = 26 * 1.2;
const COUNTS_LINE_HEIGHT = 16 * 1.5;
const RESETS_LINE_HEIGHT = 14 * 1.5;
const ICON_CIRCLE = 64;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary, paddingTop: 50 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.xs,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.xl },
  iconCircle: {
    width: ICON_CIRCLE,
    height: ICON_CIRCLE,
    borderRadius: ICON_CIRCLE / 2,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    lineHeight: TITLE_LINE_HEIGHT,
    letterSpacing: -0.3,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  counts: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: COUNTS_LINE_HEIGHT,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  resets: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: RESETS_LINE_HEIGHT,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 320,
  },
  footer: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing['2xl'] },
  doneBtn: {
    height: 52,
    borderRadius: radii.button,
    backgroundColor: colors.text.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneText: { fontSize: 16, fontWeight: '600', color: colors.text.onInverse },
});
