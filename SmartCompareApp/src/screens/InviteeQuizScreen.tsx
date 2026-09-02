/**
 * InviteeQuizScreen (F3.3)
 *
 * 4-question wizard for invitees: priority / budget / brand_attitude /
 * non-negotiable. One question per screen for PDF #6 gradual
 * commitment. After Q4 → POST /referrals/invite/{token}/quiz → render a
 * personalized result with a soft signup CTA (PDF #6 + design 3.7).
 *
 * No PII stored pre-signup — backend's quiz endpoint is auth-OPTIONAL
 * and doesn't persist answers. The personalized result is rendered
 * client-side from the response payload.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  SafeAreaView,
  Platform,
  I18nManager,
} from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Trophy, Sparkles } from 'lucide-react-native';
import { DirectionalIcon } from '../components/primitives/DirectionalIcon';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import { ProgressBar } from '../components/ProgressBar';
import { Chip } from '../components/Chip';
import { Button } from '../components/Button';
import { CounterTicker } from '../components/CounterTicker';
import { RootStackParamList } from '../types';
import {
  submitInviteeQuiz,
  ReferralError,
} from '../services/referralService';

type Props = NativeStackScreenProps<RootStackParamList, 'InviteeQuiz'>;

// Reuse the same option lists OnboardingScreen uses; backend's
// VALID_QUIZ_BRAND_ATTITUDE accepts both onboarding's 3 and the cohort's 3,
// so we surface the cohort-flavoured names here for fresh invitees.
const PRIORITY_OPTIONS = [
  'price', 'quality', 'brand_reputation', 'durability',
  'latest_features', 'ease_of_use', 'eco_friendly', 'health_safety',
] as const;

const BUDGET_OPTIONS = ['budget', 'mid', 'premium'] as const;

const QUIZ_BRAND_OPTIONS = ['trust_known_brands', 'open_to_emerging', 'value_first'] as const;

const TOTAL_QUESTIONS = 4;

interface QuizState {
  priority: string;
  budget: string;
  brand_attitude: string;
  non_negotiable: string;
}

export default function InviteeQuizScreen({ navigation, route }: Props) {
  const { t } = useTranslation();
  const { share_token, invite_id } = route.params;

  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<QuizState>({
    priority: '',
    budget: '',
    brand_attitude: '',
    non_negotiable: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const isStepValid = (): boolean => {
    switch (step) {
      case 0: return answers.priority !== '';
      case 1: return answers.budget !== '';
      case 2: return answers.brand_attitude !== '';
      case 3: return true; // non_negotiable is optional
      default: return false;
    }
  };

  const handleBack = () => {
    if (step === 0) {
      navigation.goBack();
    } else {
      setStep(step - 1);
    }
  };

  const handleNext = useCallback(async () => {
    if (!isStepValid()) return; // belt-and-suspenders for accessibility tools that bypass `disabled`
    if (step < TOTAL_QUESTIONS - 1) {
      setStep(step + 1);
      return;
    }
    // Submit
    setSubmitError(null);
    setSubmitting(true);
    try {
      const res = await submitInviteeQuiz(share_token, {
        priority: answers.priority,
        budget: answers.budget,
        brand_attitude: answers.brand_attitude,
        non_negotiable: answers.non_negotiable.trim() || undefined,
      });
      setResult(res);
    } catch (err) {
      const e = err as ReferralError;
      if (e?.status === 503) {
        setSubmitError(t('referrals.quiz.errorUnavailable'));
      } else if (e?.status === 404) {
        setSubmitError(t('referrals.quiz.errorNotFound'));
      } else {
        setSubmitError(t('referrals.quiz.errorGeneric'));
      }
    } finally {
      setSubmitting(false);
    }
  }, [step, share_token, answers, t]);

  const handleSignup = () => {
    // F3.5 follow-up will read this invite_id off the route params on
    // RegisterScreen and POST it through to /api/v1/auth/register so
    // the backend links redeemed_by_user_id. The Auth stack is nested
    // so we resort to `as any` rather than threading every nested param
    // type into the ParamList — well-typed once F3.5 lands the
    // RegisterScreen with an invite_id-aware params type.
    (navigation as any).navigate('Auth', {
      screen: 'Register',
      params: { invite_id },
    });
  };

  // ---------- Result view (after submission) ----------
  if (result) {
    const winnerName: string | undefined =
      result?.overview?.winner?.name ??
      (typeof result?.winner_index === 'number'
        ? result?.products?.[result.winner_index]?.name
        : undefined);
    const winnerReason: string | undefined =
      result?.overview?.winner?.reason ?? result?.recommendation;

    // Phase 4 § 4e — match score animates 0→N. M18 MB-contract-10: the
    // backend ships per-product scores at `scoring.scores.product_N.overall`
    // (response_builder.py:1557-1564) — the previously-read
    // `scoring.products[i].score` exists on NO backend payload shape, so
    // every invitee saw the fabricated 78 fallback. Pick the winner's
    // overall and clamp to [0, 100]; 78 remains the fallback only when
    // scoring data is genuinely absent.
    const winnerIdx: number =
      result?.overview?.winner?.product_index ??
      (typeof result?.winner_index === 'number' ? result.winner_index : 0);
    const rawScore: number =
      result?.scoring?.scores?.[`product_${winnerIdx}`]?.overall ?? 78;
    const matchScore = Math.max(0, Math.min(100, Math.round(rawScore)));

    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Animated.View entering={FadeIn.duration(400)} style={styles.resultHero}>
            <View style={styles.resultIcon}>
              <Trophy size={32} color={colors.accent} />
            </View>
            <Text style={styles.resultTitle}>{t('referrals.quiz.resultTitle')}</Text>
            <Text style={styles.resultSubtitle}>{t('referrals.quiz.resultSubtitle')}</Text>
          </Animated.View>

          {winnerName ? (
            <Animated.View
              testID="quiz-winner-card"
              entering={FadeInDown.delay(150).duration(400)}
              style={styles.winnerCardWrap}
            >
              {/* Emerald glow ring per § 4e — sibling-positioned absolute
                  ring behind the card, offset by negative inset to bleed
                  past the card edge for the "halo" effect. */}
              <View testID="quiz-winner-glow" style={styles.winnerGlow} />
              <View style={styles.winnerCard}>
                <Text style={styles.winnerLabel}>{t('referrals.quiz.bestForYou')}</Text>
                <Text style={styles.winnerName}>{winnerName}</Text>
                {winnerReason ? (
                  <Text style={styles.winnerReason}>{winnerReason}</Text>
                ) : null}
                {/* Match-score CounterTicker — animates 0 → N (1.2s ease-out
                    via the component's default duration). */}
                <View testID="quiz-match-score" style={styles.matchScoreRow}>
                  <CounterTicker
                    target={matchScore}
                    duration={1200}
                    suffix="%"
                    style={styles.matchScoreNumber}
                  />
                  <Text style={styles.matchScoreLabel}>
                    {t('referrals.quiz.matchScoreLabel', {
                      defaultValue: 'match for you',
                    })}
                  </Text>
                </View>
              </View>
            </Animated.View>
          ) : null}

          {/* "How your answers shaped this" — echoes the user's quiz inputs
              so the personalization feels concrete, not magic. */}
          <Animated.View
            testID="quiz-shaped-by"
            entering={FadeInDown.delay(225).duration(400)}
            style={styles.shapedByBlock}
          >
            <Text style={styles.shapedByTitle}>
              {t('referrals.quiz.shapedByTitle', {
                defaultValue: 'How your answers shaped this',
              })}
            </Text>
            {answers.priority ? (
              <Text style={styles.shapedByRow}>
                {t('referrals.quiz.shapedByPriority', {
                  priority: t(`onboarding.priorities.${answers.priority}`),
                  defaultValue: `Priority: ${answers.priority}`,
                })}
              </Text>
            ) : null}
            {answers.budget ? (
              <Text style={styles.shapedByRow}>
                {t('referrals.quiz.shapedByBudget', {
                  budget: t(`onboarding.budget.${answers.budget}`),
                  defaultValue: `Budget: ${answers.budget}`,
                })}
              </Text>
            ) : null}
            {answers.brand_attitude ? (
              <Text style={styles.shapedByRow}>
                {t('referrals.quiz.shapedByBrand', {
                  brand: t(`referrals.quiz.brand.${answers.brand_attitude}`),
                  defaultValue: `Brand: ${answers.brand_attitude}`,
                })}
              </Text>
            ) : null}
          </Animated.View>

          <Animated.View
            entering={FadeInDown.delay(300).duration(400)}
            style={styles.signupBlock}
          >
            <View style={styles.signupHeader}>
              <Sparkles size={18} color={colors.accent} />
              <Text style={styles.signupTitle}>{t('referrals.quiz.signupTitle')}</Text>
            </View>
            <Text style={styles.signupBody}>{t('referrals.quiz.signupBody')}</Text>
            {/* Soft signup CTA per § 4e — black primary Button, copy
                "Try Qaren free — 5 comparisons" (defined in i18n). */}
            <Button
              testID="quiz-signup-cta"
              title={t('referrals.quiz.signupCtaSoft', {
                defaultValue: 'Try Qaren free — 5 comparisons',
              })}
              variant="primary"
              onPress={handleSignup}
              accessibilityLabel={t('referrals.quiz.signupCtaSoft', {
                defaultValue: 'Try Qaren free — 5 comparisons',
              })}
            />
            <TouchableOpacity
              onPress={() =>
                navigation.reset({ index: 0, routes: [{ name: 'Main' as never }] })
              }
              accessibilityRole="button"
              accessibilityLabel={t('referrals.quiz.skipSignup')}
              style={styles.skipLinkWrap}
            >
              <Text style={styles.skipLink}>{t('referrals.quiz.skipSignup')}</Text>
            </TouchableOpacity>
          </Animated.View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ---------- Quiz wizard ----------
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={handleBack}
          style={styles.headerButton}
          disabled={submitting}
          accessibilityLabel={t('common.back', { defaultValue: 'Back' })}
        >
          <DirectionalIcon>
            <ArrowLeft size={20} color={colors.text.primary} />
          </DirectionalIcon>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {t('referrals.quiz.stepCounter', { current: step + 1, total: TOTAL_QUESTIONS })}
        </Text>
        <View style={styles.headerButton} />
      </View>

      <View style={styles.progressBar}>
        <ProgressBar progress={(step + 1) / TOTAL_QUESTIONS} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {step === 0 ? (
          <Animated.View entering={FadeIn.duration(300)}>
            <Text style={styles.questionTitle}>{t('referrals.quiz.q1.title')}</Text>
            <Text style={styles.questionHint}>{t('referrals.quiz.q1.hint')}</Text>
            <View style={styles.optionsGrid}>
              {PRIORITY_OPTIONS.map((opt) => (
                <Chip
                  key={opt}
                  label={t(`onboarding.priorities.${opt}`)}
                  selected={answers.priority === opt}
                  onPress={() => setAnswers((a) => ({ ...a, priority: opt }))}
                />
              ))}
            </View>
          </Animated.View>
        ) : null}

        {step === 1 ? (
          <Animated.View entering={FadeIn.duration(300)}>
            <Text style={styles.questionTitle}>{t('referrals.quiz.q2.title')}</Text>
            <Text style={styles.questionHint}>{t('referrals.quiz.q2.hint')}</Text>
            <View style={styles.optionsList}>
              {BUDGET_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[
                    styles.optionRow,
                    answers.budget === opt && styles.optionRowSelected,
                  ]}
                  onPress={() => setAnswers((a) => ({ ...a, budget: opt }))}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: answers.budget === opt }}
                >
                  <Text
                    style={[
                      styles.optionLabel,
                      answers.budget === opt && styles.optionLabelSelected,
                    ]}
                  >
                    {t(`onboarding.budget.${opt}`)}
                  </Text>
                  <Text style={styles.optionDesc}>
                    {t(`onboarding.budget.${opt}_desc`)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </Animated.View>
        ) : null}

        {step === 2 ? (
          <Animated.View entering={FadeIn.duration(300)}>
            <Text style={styles.questionTitle}>{t('referrals.quiz.q3.title')}</Text>
            <Text style={styles.questionHint}>{t('referrals.quiz.q3.hint')}</Text>
            <View style={styles.optionsList}>
              {QUIZ_BRAND_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[
                    styles.optionRow,
                    answers.brand_attitude === opt && styles.optionRowSelected,
                  ]}
                  onPress={() => setAnswers((a) => ({ ...a, brand_attitude: opt }))}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: answers.brand_attitude === opt }}
                >
                  <Text
                    style={[
                      styles.optionLabel,
                      answers.brand_attitude === opt && styles.optionLabelSelected,
                    ]}
                  >
                    {t(`referrals.quiz.brand.${opt}`)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </Animated.View>
        ) : null}

        {step === 3 ? (
          <Animated.View entering={FadeIn.duration(300)}>
            <Text style={styles.questionTitle}>{t('referrals.quiz.q4.title')}</Text>
            <Text style={styles.questionHint}>{t('referrals.quiz.q4.hint')}</Text>
            <TextInput
              style={styles.textInput}
              value={answers.non_negotiable}
              onChangeText={(value) => setAnswers((a) => ({ ...a, non_negotiable: value }))}
              placeholder={t('referrals.quiz.q4.placeholder')}
              placeholderTextColor={colors.text.placeholder}
              maxLength={256}
              accessibilityLabel={t('referrals.quiz.q4.title')}
              multiline
            />
            <Text style={styles.charCount}>{answers.non_negotiable.length}/256</Text>
          </Animated.View>
        ) : null}

        {submitError ? <Text style={styles.errorText}>{submitError}</Text> : null}
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[
            styles.primaryButton,
            (!isStepValid() || submitting) && styles.disabled,
          ]}
          onPress={handleNext}
          disabled={!isStepValid() || submitting}
          accessibilityRole="button"
          accessibilityLabel={
            step === TOTAL_QUESTIONS - 1
              ? t('referrals.quiz.submit')
              : t('referrals.quiz.next')
          }
        >
          {submitting ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>
              {step === TOTAL_QUESTIONS - 1
                ? t('referrals.quiz.submit')
                : t('referrals.quiz.next')}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.sm,
  },
  headerButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: { ...typography.body, color: colors.text.secondary, fontWeight: '500' },
  progressBar: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.base,
    paddingBottom: spacing['3xl'],
  },
  questionTitle: { ...typography.title, fontSize: 22, color: colors.text.primary, marginBottom: spacing.sm },
  questionHint: { ...typography.body, color: colors.text.secondary, marginBottom: spacing.xl },
  optionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  optionsList: { gap: spacing.sm },
  optionRow: {
    paddingVertical: spacing.base,
    paddingHorizontal: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.secondary,
  },
  optionRowSelected: {
    borderColor: colors.accent,
    backgroundColor: colors.accentLight,
  },
  optionLabel: { ...typography.body, fontWeight: '600', color: colors.text.primary },
  optionLabelSelected: { color: colors.accent },
  optionDesc: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
  textInput: {
    borderWidth: 1,
    borderColor: colors.border.medium,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    paddingVertical: Platform.OS === 'ios' ? spacing.md : spacing.sm,
    ...typography.body,
    color: colors.text.primary,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  charCount: {
    ...typography.small,
    color: colors.text.placeholder,
    marginTop: spacing.xs,
    // Trailing-edge alignment — flips to 'left' under RTL so the counter
    // stays at the bottom-trailing corner of the textarea in both locales.
    textAlign: I18nManager.isRTL ? 'left' : 'right',
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    marginTop: spacing.base,
    textAlign: 'center',
  },
  footer: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.base,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border.light,
  },
  primaryButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
  },
  primaryButtonText: { ...typography.body, fontWeight: '600', color: '#FFFFFF' },
  disabled: { opacity: 0.4 },
  // Result view
  resultHero: { alignItems: 'center', marginBottom: spacing.xl },
  resultIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.base,
  },
  resultTitle: { ...typography.display, fontSize: 24, color: colors.text.primary, textAlign: 'center' },
  resultSubtitle: { ...typography.body, color: colors.text.secondary, textAlign: 'center', marginTop: spacing.sm },
  /**
   * Wraps the winner card + glow ring. position:relative so the
   * glow's absolute fill nests cleanly. Phase 4 § 4e.
   */
  winnerCardWrap: {
    position: 'relative',
    marginBottom: spacing.xl,
  },
  /**
   * Emerald glow ring per § 4e — sits behind the card, bleeds 8px past
   * each edge so the halo reads as a soft glow rather than a border.
   */
  winnerGlow: {
    position: 'absolute',
    top: -8,
    left: -8,
    right: -8,
    bottom: -8,
    borderRadius: radii.card + 8,
    backgroundColor: colors.accentGlow,
  },
  winnerCard: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
  },
  /** Match-score row: big number + small "match for you" label. */
  matchScoreRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  matchScoreNumber: {
    ...typography.display,
    color: colors.accent,
    fontWeight: '700',
  },
  matchScoreLabel: {
    ...typography.body,
    color: colors.text.secondary,
  },
  /** "How your answers shaped this" block — echoes user's quiz inputs. */
  shapedByBlock: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
    marginBottom: spacing.xl,
    gap: spacing.sm,
  },
  shapedByTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  shapedByRow: {
    ...typography.body,
    color: colors.text.secondary,
  },
  winnerLabel: {
    ...typography.small,
    color: colors.text.secondary,
    textTransform: 'uppercase',
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  winnerName: { ...typography.title, color: colors.accent, marginBottom: spacing.sm },
  winnerReason: { ...typography.body, color: colors.text.primary },
  signupBlock: { gap: spacing.md },
  signupHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  signupTitle: { ...typography.body, fontWeight: '600', color: colors.text.primary },
  signupBody: { ...typography.body, color: colors.text.secondary },
  skipLinkWrap: {
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  skipLink: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.sm,
    fontWeight: '500',
  },
});
