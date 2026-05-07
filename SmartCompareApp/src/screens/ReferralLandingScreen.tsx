/**
 * ReferralLandingScreen (F3.2)
 *
 * Invitee landing page — opens from a deep link or web URL of the form
 * `qaren.app/c/{share_token}?ref={referrer_code}`. NO signup gate before
 * the quiz (PDF #6 — gradual commitment).
 *
 * Calls GET /api/v1/referrals/invite/{token}?ref={code} on mount and
 * renders curiosity copy with the referrer's display name + product
 * names per design 3.5. The "Start my comparison" CTA pushes onto
 * InviteeQuizScreen with the resolved invite_id.
 *
 * Privacy: backend strips referrer personalization (preferences, budget,
 * verdict reasons) before returning. The `referrer_display_name` here is
 * already gated by the referrer's privacy toggle — falls back to "A
 * friend" when show_name=false.
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Linking,
} from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { ArrowLeft, Sparkles } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';
import { RootStackParamList } from '../types';
import {
  resolveInvite,
  ReferralError,
  InviteResolution,
} from '../services/referralService';
import { CohortBadge } from '../components/CohortBadge';
import { Button } from '../components/Button';
import { useLanguage } from '../hooks/useLanguage';

type Props = NativeStackScreenProps<RootStackParamList, 'ReferralLanding'>;

export default function ReferralLandingScreen({ navigation, route }: Props) {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const { share_token, ref } = route.params;
  const [resolution, setResolution] = useState<InviteResolution | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState<'not_found' | 'unavailable' | 'network' | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await resolveInvite({ share_token, ref });
        if (!cancelled) {
          setResolution(result);
          setErrorState(null);
        }
      } catch (err) {
        if (cancelled) return;
        const e = err as ReferralError;
        if (e?.status === 404) {
          setErrorState('not_found');
        } else if (e?.status === 503) {
          setErrorState('unavailable');
        } else {
          setErrorState('network');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [share_token, ref]);

  // ---------- Loading ----------
  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View
          style={styles.center}
          accessibilityLabel={t('referrals.landing.loading')}
        >
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  // ---------- Error states ----------
  if (errorState || !resolution) {
    const messageKey =
      errorState === 'not_found'
        ? 'referrals.landing.notFound'
        : errorState === 'unavailable'
        ? 'referrals.landing.unavailable'
        : 'referrals.landing.network';
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Text style={styles.fallbackTitle}>{t(messageKey)}</Text>
          <Button
            title={t('referrals.landing.openQaren')}
            variant="primary"
            onPress={() => {
              // "Open Qaren" — drop the user into the main app flow. If they're
              // unauth they'll hit Auth; if they're authed they'll see Home.
              navigation.reset({
                index: 0,
                routes: [{ name: 'Main' as never }],
              });
            }}
            accessibilityLabel={t('referrals.landing.openQaren')}
          />
        </View>
      </SafeAreaView>
    );
  }

  // ---------- Happy path ----------
  const referrerName = resolution.referrer_display_name;
  const products = resolution.comparison?.products ?? [];
  const productA = products[0]?.name ?? '';
  const productB = products[1]?.name ?? '';

  // Phase 4 § 4e — partial-blur invitee landing. We DO NOT surface the
  // winner ✓ here even when the backend returns winner_index. The
  // emotion (verdict + score) is gated behind the quiz/signup CTAs;
  // the information (products + cohort) is fully visible. winner_index
  // is intentionally unused on this screen.
  const cohort: any = (resolution as any).cohort_match ?? null;
  const cohortPeerCount: number =
    cohort?.peers_count ?? cohort?.peer_count ?? 0;
  const cohortGovernorate: string =
    typeof cohort?.governorate === 'string' ? cohort.governorate : '';

  const handleQuizPath = () => {
    navigation.navigate('InviteeQuiz', {
      share_token,
      invite_id: resolution.invite_id,
      ref,
    });
  };

  const handleSkipPath = () => {
    // Cool path: drop the invitee into the main app flow. They'll hit
    // Auth (unauth) or Main (authed); the invitee credit is applied
    // server-side at signup time so they can revisit the comparison
    // from History after registering.
    navigation.reset({
      index: 0,
      routes: [{ name: 'Main' as never }],
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.headerButton}
          accessibilityLabel={t('common.back', { defaultValue: 'Back' })}
        >
          <ArrowLeft size={20} color={colors.text.primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{t('app.name')}</Text>
        <View style={styles.headerButton} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Animated.View entering={FadeInDown.duration(400)} style={styles.heroBlock}>
          <View style={styles.iconBubble}>
            <Sparkles size={28} color={colors.accent} />
          </View>
          {/* Phase 4 § 4e — single sender-opener title; winner stays gated. */}
          <Text style={styles.heroTitle}>
            {t('referrals.landing.titleNoWinner', {
              referrer: referrerName,
              productA,
              productB,
              defaultValue: `${referrerName} thought you'd like this`,
            })}
          </Text>
          <Text style={styles.heroSubtitle}>{t('referrals.landing.subtitle')}</Text>
        </Animated.View>

        {/* Comparison preview — names only. NO winner styling, NO badge.
            The verdict is gated behind the quiz/signup CTAs below. */}
        <Animated.View
          entering={FadeInDown.delay(150).duration(400)}
          style={styles.previewCard}
        >
          <Text style={styles.previewLabel}>
            {t('referrals.landing.previewLabel')}
          </Text>
          <View style={styles.productRow}>
            {products.map((product: any, index: number) => (
              <View
                key={`${product.name}-${index}`}
                testID={`referral-product-pill-${index}`}
                style={styles.productPill}
              >
                <Text style={styles.productName} numberOfLines={2}>
                  {product.name}
                </Text>
              </View>
            ))}
          </View>
        </Animated.View>

        {/* Cohort badge — surfaces inline social proof per build
            principle 6. CohortBadge guards on missing data so the slot
            stays present (testID-only) when there's no match. */}
        <View testID="referral-cohort-badge-slot" style={styles.cohortSlot}>
          <CohortBadge
            peerCount={cohortPeerCount}
            governorate={cohortGovernorate}
            isRTL={isRTL}
          />
        </View>

        {/* Two CTAs per § 4e — emerald hot-path + small text-link cool-path. */}
        <Animated.View
          entering={FadeInDown.delay(300).duration(400)}
          style={styles.ctaContainer}
        >
          <Button
            testID="referral-cta-quiz"
            title={t('referrals.landing.quizCta', {
              defaultValue: 'See how it scores for YOU',
            })}
            variant="signature"
            onPress={handleQuizPath}
            accessibilityLabel={t('referrals.landing.quizCta', {
              defaultValue: 'See how it scores for YOU',
            })}
          />

          <TouchableOpacity
            testID="referral-cta-skip"
            onPress={handleSkipPath}
            accessibilityRole="link"
            accessibilityLabel={t('referrals.landing.skipCta', {
              defaultValue: 'Just give me the app',
            })}
            style={styles.skipLink}
          >
            <Text style={styles.skipLinkText}>
              {t('referrals.landing.skipCta', {
                defaultValue: 'Just give me the app',
              })}
            </Text>
          </TouchableOpacity>

          <Text style={styles.privacyNote}>
            {t('referrals.landing.privacyNote')}
          </Text>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    gap: spacing.lg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border.light,
  },
  headerButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    ...typography.title,
    color: colors.text.primary,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing['3xl'],
  },
  heroBlock: {
    alignItems: 'center',
    marginBottom: spacing['2xl'],
  },
  iconBubble: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.base,
  },
  heroTitle: {
    ...typography.display,
    fontSize: 24,
    color: colors.text.primary,
    textAlign: 'center',
  },
  heroSubtitle: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  previewCard: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    marginBottom: spacing.xl,
  },
  previewLabel: {
    ...typography.small,
    color: colors.text.secondary,
    textTransform: 'uppercase',
    fontWeight: '600',
    marginBottom: spacing.sm,
  },
  productRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  productPill: {
    flex: 1,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    borderRadius: radii.input,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    minHeight: 72,
    justifyContent: 'center',
  },
  productName: {
    ...typography.body,
    color: colors.text.primary,
    textAlign: 'center',
    fontWeight: '500',
  },
  /** Slot for inline cohort social proof — sits between preview + CTAs. */
  cohortSlot: {
    paddingHorizontal: spacing.sm,
    paddingBottom: spacing.lg,
    alignItems: 'flex-start',
  },
  ctaContainer: {
    gap: spacing.md,
    alignItems: 'stretch',
  },
  /**
   * Cool-path link — small, secondary; the emerald hot-path CTA above
   * carries the visual weight per design § 4e ("Just give me the app"
   * is the skim-readers fallback).
   */
  skipLink: {
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  skipLinkText: {
    ...typography.body,
    color: colors.text.secondary,
    textDecorationLine: 'underline',
  },
  privacyNote: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  fallbackTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
});
