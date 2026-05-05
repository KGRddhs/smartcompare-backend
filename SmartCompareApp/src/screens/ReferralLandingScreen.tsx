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

type Props = NativeStackScreenProps<RootStackParamList, 'ReferralLanding'>;

export default function ReferralLandingScreen({ navigation, route }: Props) {
  const { t } = useTranslation();
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
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => {
              // "Open Qaren" — drop the user into the main app flow. If they're
              // unauth they'll hit Auth; if they're authed they'll see Home.
              navigation.reset({
                index: 0,
                routes: [{ name: 'Main' as never }],
              });
            }}
            accessibilityRole="button"
            accessibilityLabel={t('referrals.landing.openQaren')}
          >
            <Text style={styles.primaryButtonText}>{t('referrals.landing.openQaren')}</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ---------- Happy path ----------
  const referrerName = resolution.referrer_display_name;
  const products = resolution.comparison?.products ?? [];
  const productA = products[0]?.name ?? '';
  const productB = products[1]?.name ?? '';
  const winnerIndex: number | undefined = resolution.comparison?.winner_index;
  const winnerName =
    typeof winnerIndex === 'number' ? products[winnerIndex]?.name : undefined;

  const handleStart = () => {
    navigation.navigate('InviteeQuiz', {
      share_token,
      invite_id: resolution.invite_id,
      ref,
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
          <Text style={styles.heroTitle}>
            {/* Whether the winner name is known dictates which copy variant we show. */}
            {winnerName
              ? t('referrals.landing.titleWithWinner', {
                  referrer: referrerName,
                  productA,
                  productB,
                  winner: winnerName,
                })
              : t('referrals.landing.titleNoWinner', {
                  referrer: referrerName,
                  productA,
                  productB,
                })}
          </Text>
          <Text style={styles.heroSubtitle}>{t('referrals.landing.subtitle')}</Text>
        </Animated.View>

        {/* Comparison preview — products only, no preferences/budget */}
        <Animated.View
          entering={FadeInDown.delay(150).duration(400)}
          style={styles.previewCard}
        >
          <Text style={styles.previewLabel}>{t('referrals.landing.previewLabel')}</Text>
          <View style={styles.productRow}>
            {products.map((product: any, index: number) => (
              <View
                key={`${product.name}-${index}`}
                style={[
                  styles.productPill,
                  winnerIndex === index && styles.productPillWinner,
                ]}
              >
                <Text
                  style={[
                    styles.productName,
                    winnerIndex === index && styles.productNameWinner,
                  ]}
                  numberOfLines={2}
                >
                  {product.name}
                </Text>
                {winnerIndex === index ? (
                  <Text style={styles.winnerBadge}>{t('referrals.landing.winnerBadge')}</Text>
                ) : null}
              </View>
            ))}
          </View>
        </Animated.View>

        {/* CTA */}
        <Animated.View
          entering={FadeInDown.delay(300).duration(400)}
          style={styles.ctaContainer}
        >
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleStart}
            accessibilityRole="button"
            accessibilityLabel={t('referrals.landing.startCta')}
            activeOpacity={0.85}
          >
            <Text style={styles.primaryButtonText}>{t('referrals.landing.startCta')}</Text>
          </TouchableOpacity>
          <Text style={styles.privacyNote}>{t('referrals.landing.privacyNote')}</Text>
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
  productPillWinner: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  productName: {
    ...typography.body,
    color: colors.text.primary,
    textAlign: 'center',
    fontWeight: '500',
  },
  productNameWinner: {
    color: colors.accent,
    fontWeight: '600',
  },
  winnerBadge: {
    ...typography.small,
    color: colors.accent,
    fontWeight: '600',
    marginTop: spacing.xs,
    textTransform: 'uppercase',
  },
  ctaContainer: {
    alignItems: 'center',
  },
  primaryButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing['2xl'],
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    width: '100%',
  },
  primaryButtonText: {
    ...typography.body,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  privacyNote: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  fallbackTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
});
