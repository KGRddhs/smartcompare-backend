/**
 * Qaren - Paywall Screen
 * Bottom-sheet overlay shown via Stack.Navigator with presentation:
 * 'transparentModal'. Reads optional initialUsage from route.params
 * (populated by USAGE_LIMIT error detail); otherwise fetches from backend.
 *
 * Bundle D 2.F.2 Screen 10 — visual refresh applies Claude-Design v3
 * elements that don't require Tap Payments integration: HeroVisual
 * (3 mini-vs cards as brand moment) + SocialProof avatar/rating strip.
 * The Yearly/Monthly PlanCardLarge cards from v3 are deferred until
 * real pricing + payment SDK lands — current screen continues to be a
 * usage-status reveal + single subscribe placeholder.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Check, Crown, Zap, Star, X } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { getUsageStatus, UsageStatus } from '../services/usageService';
import type { RootStackParamList } from '../types/types';

type PaywallRouteProp = RouteProp<RootStackParamList, 'Paywall'>;
type PaywallNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Paywall'>;

export default function PaywallScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<PaywallNavigationProp>();
  const route = useRoute<PaywallRouteProp>();
  const initialUsage = route.params?.initialUsage;

  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!usage) {
      setLoading(true);
      getUsageStatus().then((data) => {
        setUsage(data);
        setLoading(false);
      });
    }
  }, [usage]);

  const onDismiss = () => navigation.goBack();

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
    <View style={styles.overlay}>
      <TouchableOpacity style={styles.backdrop} onPress={onDismiss} activeOpacity={1} />
      <View style={styles.sheet}>
        <View style={styles.handleRow}>
          <View style={styles.handle} />
          <TouchableOpacity
            testID="paywall-close"
            onPress={onDismiss}
            style={styles.closeBtn}
            accessibilityRole="button"
            accessibilityLabel={t('common.cancel')}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <X size={18} color={colors.text.primary} />
          </TouchableOpacity>
        </View>

        {/* Bundle D 2.F.2 Screen 10 HERO — 3 stacked mini vs-pairs. Pure
            visual brand moment; no data deps. Middle card sits 6px above
            the line per Claude-Design v3. */}
        <View testID="paywall-hero" style={styles.hero}>
          {[
            { a: '#E8E9ED', b: '#1B1C1F', winnerB: true, offset: 0 },
            { a: '#FBE6E6', b: '#FFEAD4', winnerA: true, offset: -6 },
            { a: '#E6EEF9', b: '#FFF1DA', winnerB: true, offset: 0 },
          ].map((it, i) => (
            <View
              key={i}
              style={[
                styles.heroCard,
                { transform: [{ translateY: it.offset }] },
                it.offset !== 0 && styles.heroCardElevated,
              ]}
            >
              <View style={styles.heroRow}>
                <View
                  style={[
                    styles.heroTile,
                    { backgroundColor: it.a },
                    it.winnerA && styles.heroTileWinner,
                  ]}
                />
                <View style={styles.heroVsPill}>
                  <Text style={styles.heroVsText}>{t('profile.recent.vs')}</Text>
                </View>
                <View
                  style={[
                    styles.heroTile,
                    { backgroundColor: it.b },
                    it.winnerB && styles.heroTileWinner,
                  ]}
                />
              </View>
            </View>
          ))}
        </View>

        <Text style={styles.title}>{t('paywall.title')}</Text>

        {/* SocialProof — 5 avatar dots + trust line + 4.8★ pill */}
        <View testID="paywall-social-proof" style={styles.socialProof}>
          <View style={styles.avatarStack}>
            {['#FCD9D2', '#E6EEF9', '#FFF1DA', '#FBE6E6', '#1B1C1F'].map((c, i) => (
              <View
                key={i}
                style={[
                  styles.avatarDot,
                  { backgroundColor: c, marginStart: i ? -8 : 0 },
                ]}
              >
                <Text
                  style={[
                    styles.avatarLetter,
                    i === 4 && { color: '#fff' },
                  ]}
                >
                  {['K', 'M', 'A', 'S', '+'][i]}
                </Text>
              </View>
            ))}
          </View>
          <View style={styles.ratingPill}>
            <Star size={11} color={colors.accentDark} fill={colors.accentDark} />
            <Text style={styles.ratingText}>4.8</Text>
          </View>
        </View>

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
  handleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    position: 'relative',
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: spacing.lg,
  },
  closeBtn: {
    position: 'absolute',
    right: 0,
    top: 0,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Bundle D 2.F.2 Screen 10 — HeroVisual styles
  hero: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  heroCard: {
    padding: 8,
    borderRadius: 12,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  heroCardElevated: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  heroRow: {
    flexDirection: 'row',
    gap: 4,
    position: 'relative',
    alignItems: 'center',
  },
  heroTile: {
    width: 38,
    height: 38,
    borderRadius: 8,
  },
  heroTileWinner: {
    borderWidth: 2,
    borderColor: colors.accent,
  },
  heroVsPill: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: [{ translateX: -10 }, { translateY: -8 }],
    height: 16,
    paddingHorizontal: 5,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: colors.bg.secondary,
    zIndex: 1,
  },
  heroVsText: {
    fontSize: 8,
    fontWeight: '700',
    color: colors.accentDark,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  // SocialProof styles
  socialProof: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  avatarStack: {
    flexDirection: 'row',
  },
  avatarDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.bg.primary,
  },
  avatarLetter: {
    fontSize: 9,
    fontWeight: '700',
    color: 'rgba(0,0,0,0.4)',
  },
  ratingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: spacing.sm,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
  },
  ratingText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.accentDark,
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
