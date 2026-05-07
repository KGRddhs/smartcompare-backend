/**
 * OnboardingFlow — 17-step orchestrator (Phase 2 Task 9).
 *
 * Owns step state, validation gating, back/next navigation, RTL-aware
 * slide direction. Sub-step components render placeholder bodies in this
 * task; Tasks 13-23 swap each placeholder for the full screen build.
 *
 * Slide-transition timing comes from `motion.screenTransition` per design
 * spec Section 1 (320ms cubic-bezier, RTL-mirrored). Visual transitions
 * are deferred to per-screen tasks; this orchestrator simply exposes
 * `data-direction` on the wrapper so screen-builders can mirror their
 * own animations.
 */

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../../hooks/useLanguage';
import { Button } from '../../components/Button';
import { ProgressBar } from '../../components/ProgressBar';
import { BackIcon, flipForRTL } from '../../icons';
import { trackEvents } from '../../services/api';
import { colors, spacing, typography } from '../../theme';
import {
  OnboardingFlowData,
  OnboardingStep,
  ONBOARDING_TOTAL_STEPS,
} from './types';

/**
 * Stable English step names for analytics. The locale-resolved label
 * lives in i18n; these stay fixed so canary dashboards can group
 * events cleanly across EN/AR. Mirrors design § 2 screen names.
 */
const STEP_NAMES: Record<OnboardingStep, string> = {
  1: 'welcome',
  2: 'language',
  3: 'value_prop',
  4: 'country',
  5: 'trust_bridge',
  6: 'age_group',
  7: 'gender',
  8: 'priorities',
  9: 'budget',
  10: 'brand_attitude',
  11: 'attribution',
  12: 'cohort_proof',
  13: 'anticipation',
  14: 'theatrical_loading',
  15: 'reveal',
  16: 'account',
  17: 'notifications',
};

interface OnboardingFlowProps {
  /** Fired once step 17 completes. Receives the full accumulated data. */
  onComplete: (data: OnboardingFlowData) => void;
  /** Override the entry step. Defaults to 1. Used by tests. */
  initialStep?: OnboardingStep;
  /** Pre-populated data, e.g. when resuming or in tests. */
  initialData?: Partial<OnboardingFlowData>;
}

/**
 * Returns true when the current step's required fields are filled.
 *
 * Steps with no required input (1 Welcome, 3 Value prop, 5 Trust, 12 Cohort
 * proof, 13 Anticipation, 14 Loading, 15 Reveal, 16 Account is special-cased
 * elsewhere, 17 Notifications offers explicit Allow/Not now buttons) always
 * return true — the user just taps Continue.
 */
function isStepValid(step: OnboardingStep, data: OnboardingFlowData): boolean {
  switch (step) {
    case 2:
      return Boolean(data.language);
    case 4:
      // Country always required. Governorate is the conditional sub-question
      // when country === 'BH'; the design spec phrases it "if Bahrain →
      // conditional second question slides in" — never a hard block.
      return Boolean(data.country);
    case 6:
      return true; // Prefer-not-to-say is also valid
    case 7:
      return true; // Prefer-not-to-say is also valid
    case 8:
      return Array.isArray(data.priorities) && data.priorities.length >= 1
        && data.priorities.length <= 3;
    case 9:
      return Boolean(data.budget);
    case 10:
      return Boolean(data.brand_attitude);
    case 11:
      return Boolean(data.attribution_source);
    default:
      return true;
  }
}

export function OnboardingFlow({
  onComplete,
  initialStep = 1,
  initialData,
}: OnboardingFlowProps) {
  const { t } = useTranslation();
  const { isRTL, language } = useLanguage();
  const [step, setStep] = useState<OnboardingStep>(initialStep);
  const [data, setData] = useState<OnboardingFlowData>({ ...(initialData ?? {}) });

  /**
   * Canary-monitoring analytics (Task #53 + #58 follow-up).
   *
   * Every payload carries:
   * - `step_number`, `step_name` — for per-step drop-off heatmaps
   * - `locale` — for EN/AR cohort segments
   * - `flow_variant` — locked at "new" for cohort segmentation against
   *   the legacy 6-step flow during canary (Tasks 47-48). Captured
   *   ONCE at first observation and held in a ref — never flips
   *   mid-session even if features.ENABLE_NEW_ONBOARDING somehow
   *   toggles, so dashboards can join cleanly without joining on
   *   bucket assignment.
   *
   * `trackEvents` is fire-and-forget — never block the user.
   */
  const flowVariantRef = useRef<'new'>('new');

  const fireEvent = useCallback(
    (event_type: string, extra?: Record<string, unknown>) => {
      void trackEvents([
        {
          event_type,
          event_data: {
            step_number: step,
            step_name: STEP_NAMES[step],
            locale: language,
            flow_variant: flowVariantRef.current,
            ...(extra ?? {}),
          },
        },
      ]);
    },
    [step, language]
  );

  // Fire `onboarding_started` once on initial mount. We stamp it with
  // the entry step (initialStep, usually 1) so resumed-mid-flow sessions
  // are distinguishable from fresh starts.
  useEffect(() => {
    void trackEvents([
      {
        event_type: 'onboarding_started',
        event_data: {
          step_number: initialStep,
          step_name: STEP_NAMES[initialStep],
          locale: language,
          flow_variant: flowVariantRef.current,
        },
      },
    ]);
    // Intentional: fire-once on mount only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const valid = useMemo(() => isStepValid(step, data), [step, data]);

  const setField = useCallback(<K extends keyof OnboardingFlowData>(
    key: K,
    value: OnboardingFlowData[K]
  ) => {
    setData((prev: OnboardingFlowData) => ({ ...prev, [key]: value }));
  }, []);

  const handleNext = useCallback(() => {
    if (!valid) return;
    // Fire step_completed BEFORE advancing so the event payload's
    // step_number reflects the step the user just finished. fireEvent
    // closes over the current step value via the useCallback dep.
    fireEvent('onboarding_step_completed');
    if (step >= ONBOARDING_TOTAL_STEPS) {
      fireEvent('onboarding_completed');
      onComplete(data);
      return;
    }
    setStep((prev: OnboardingStep) => (prev + 1) as OnboardingStep);
  }, [valid, step, data, onComplete, fireEvent]);

  const handleBack = useCallback(() => {
    setStep((prev: OnboardingStep) => (prev > 1 ? ((prev - 1) as OnboardingStep) : prev));
  }, []);

  const progress = step / ONBOARDING_TOTAL_STEPS;

  return (
    <SafeAreaView style={styles.safe}>
      <View
        testID="onboarding-progress"
        // Expose step totals on the host node for test assertions and a11y.
        // ProgressBar itself owns the visual fill animation.
        {...{ 'data-total-steps': ONBOARDING_TOTAL_STEPS, 'data-current-step': step }}
        accessibilityRole="progressbar"
        accessibilityValue={{ now: Math.round(progress * 100), min: 0, max: 100 }}
        style={styles.progressWrap}
      >
        <ProgressBar progress={progress} />
      </View>

      <View
        testID="onboarding-slide-wrapper"
        // Tells screen-builders (Tasks 13-23) which side their slide-in
        // animations should originate from. Matches design Section 1.
        {...{ 'data-direction': isRTL ? 'rtl' : 'ltr' }}
        style={styles.body}
      >
        <ScrollView
          contentContainerStyle={styles.bodyContent}
          showsVerticalScrollIndicator={false}
        >
          <StepContent step={step} data={data} setField={setField} t={t} />
        </ScrollView>
      </View>

      <View style={styles.footer}>
        <TouchableOpacity
          testID="onboarding-back"
          onPress={handleBack}
          accessibilityRole="button"
          accessibilityLabel={t('common.back', { defaultValue: 'Back' })}
          style={styles.backBtn}
        >
          {/* Custom back chevron (Task 5) — flipped under RTL via the
              direction-bearing helper. The icon-only target is wide
              enough to keep ≥44pt touch surface (backBtn padding). */}
          <View style={flipForRTL(isRTL)}>
            <BackIcon size={24} color={colors.text.secondary} />
          </View>
        </TouchableOpacity>

        <Button
          testID="onboarding-next"
          title={
            step === ONBOARDING_TOTAL_STEPS
              ? t('onboarding.finish', { defaultValue: 'Finish' })
              : t('onboarding.next', { defaultValue: 'Continue' })
          }
          variant="primary"
          disabled={!valid}
          onPress={handleNext}
        />
      </View>
    </SafeAreaView>
  );
}

interface StepContentProps {
  step: OnboardingStep;
  data: OnboardingFlowData;
  setField: <K extends keyof OnboardingFlowData>(
    key: K,
    value: OnboardingFlowData[K]
  ) => void;
  t: (key: string, opts?: { defaultValue?: string }) => string;
}

/**
 * Step body — one host node per step, tagged with `onboarding-step-N`.
 * Step 4 also exposes a country chip (`country-bahrain`) so the orchestrator's
 * validation-gate behavior is testable in isolation. Every other step renders
 * a minimal placeholder; Tasks 13-23 build the rich screens.
 */
function StepContent({ step, data, setField, t }: StepContentProps) {
  return (
    <View testID={`onboarding-step-${step}`} style={styles.stepBody}>
      <Text style={styles.stepEyebrow}>
        {t('onboarding.step_label', { defaultValue: `Step ${step} of ${ONBOARDING_TOTAL_STEPS}` })}
      </Text>

      {step === 4 && (
        <View>
          <Text style={styles.stepTitle}>
            {t('onboarding.country.title', { defaultValue: 'Where are you shopping from?' })}
          </Text>
          <View style={styles.countryRow}>
            <CountryChip
              testID="country-bahrain"
              label="🇧🇭 Bahrain"
              selected={data.country === 'BH'}
              onPress={() => setField('country', 'BH')}
            />
            <CountryChip
              testID="country-saudi_arabia"
              label="🇸🇦 Saudi Arabia"
              selected={data.country === 'SA'}
              onPress={() => setField('country', 'SA')}
            />
          </View>
        </View>
      )}
    </View>
  );
}

interface CountryChipProps {
  testID: string;
  label: string;
  selected: boolean;
  onPress: () => void;
}

function CountryChip({ testID, label, selected, onPress }: CountryChipProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[styles.countryChip, selected && styles.countryChipSelected]}
    >
      <Text style={[styles.countryChipText, selected && styles.countryChipTextSelected]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  progressWrap: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  body: {
    flex: 1,
  },
  bodyContent: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
  },
  stepBody: {
    flex: 1,
    paddingTop: spacing.xl,
  },
  stepEyebrow: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    marginBottom: spacing.md,
  },
  stepTitle: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.xl,
  },
  countryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  countryChip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.secondary,
  },
  countryChipSelected: {
    borderColor: colors.cta.primary,
    backgroundColor: colors.cta.primary,
  },
  countryChipText: {
    ...typography.body,
    color: colors.text.primary,
  },
  countryChipTextSelected: {
    color: colors.cta.onPrimary,
  },
  footer: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border.light,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  backBtn: {
    // Padding gives the icon-only target ≥44pt touch surface.
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
