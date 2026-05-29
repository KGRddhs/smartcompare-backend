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

// Bundle D Phase 3 device-leg fix (2026-05-25): wire the 17 Step components
// into StepContent. They were built in Sessions 36+37 but the orchestrator
// only rendered step 4 inline content. On Ahmed's iPhone every other step
// showed an empty body. Each Step* has its own prop shape — see the adapter
// inside StepContent below for the per-step mapping.
import { Step01Welcome } from './Step01Welcome';
import { Step02Language } from './Step02Language';
import { Step03ValueProp } from './Step03ValueProp';
import { Step04Country } from './Step04Country';
import { Step05Trust } from './Step05Trust';
import { Step06Age } from './Step06Age';
import { Step07Gender } from './Step07Gender';
import { Step08Priorities } from './Step08Priorities';
import { Step09Budget } from './Step09Budget';
import { Step10BrandAttitude } from './Step10BrandAttitude';
import { Step11Attribution } from './Step11Attribution';
import { Step12CohortProof } from './Step12CohortProof';
import { Step13Anticipation } from './Step13Anticipation';
import { Step14Loading } from './Step14Loading';
import { Step15Reveal } from './Step15Reveal';
import { Step16Account } from './Step16Account';
import { Step17Notifications } from './Step17Notifications';
import { Platform } from 'react-native';

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
  /**
   * Bundle D 1.F.3: terminate the flow at this step rather than at
   * `ONBOARDING_TOTAL_STEPS`. Used by NewOnboardingHost edit-mode to
   * limit the user to the style-profile subset (steps 8-10).
   */
  lastStep?: OnboardingStep;
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
  lastStep,
}: OnboardingFlowProps) {
  const terminalStep: OnboardingStep = lastStep ?? ONBOARDING_TOTAL_STEPS;
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
    if (step >= terminalStep) {
      fireEvent('onboarding_completed');
      onComplete(data);
      return;
    }
    setStep((prev: OnboardingStep) => (prev + 1) as OnboardingStep);
  }, [valid, step, data, onComplete, fireEvent, terminalStep]);

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
          <StepContent
            step={step}
            data={data}
            setField={setField}
            t={t}
            onNext={handleNext}
            onLoadingComplete={handleNext}
            onSelectAuthMethod={() => {
              // Bundle D Phase 3: Step 16 ("Save your advisor") hands off to
              // the AuthScreen stack. The orchestrator advances to step 17 so
              // the next mount lands on the notifications screen. Actual
              // auth is performed via App.tsx Stack.Navigator routes that
              // App.tsx swaps to once `onComplete` fires after step 17.
              handleNext();
            }}
            onNotificationsDone={(granted) => {
              setField('notifications_enabled', granted);
              handleNext();
            }}
          />
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
            step >= terminalStep
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
  // Bundle D Phase 3: widened from `{ defaultValue?: string }` to accept
  // arbitrary interpolation params (e.g. `{ current, total, defaultValue }`).
  // i18next's TFunction signature is variadic — the narrow type was a stub
  // from Phase 2 when only defaultValue was passed.
  t: (key: string, opts?: Record<string, unknown>) => string;
}

interface StepContentExtraProps {
  /** Advance to the next step (Step01/03/05/12/13 own internal CTA buttons). */
  onNext: () => void;
  /** Step 14 onComplete handler — fires after the 3.2s minimum loading floor. */
  onLoadingComplete: () => void;
  /** Step 16 onSelectMethod handler — hands off to the AuthScreen stack. */
  onSelectAuthMethod: (method: 'apple' | 'google' | 'email' | 'sign_in') => void;
  /** Step 17 onDone — persists notifications_enabled then finishes the flow. */
  onNotificationsDone: (granted: boolean) => void;
}

/**
 * Step body — one host node per step, tagged with `onboarding-step-N`.
 *
 * Bundle D Phase 3 device-leg fix (2026-05-25): renders the matching
 * Step* component built in Sessions 36+37. Each Step* has its own prop
 * shape; the adapter below maps onto the orchestrator's setField + data.
 *
 * Country chip (`country-bahrain`) test contract preserved — Step04Country
 * exposes the same testIDs internally.
 */
function StepContent({
  step,
  data,
  setField,
  t,
  onNext,
  onLoadingComplete,
  onSelectAuthMethod,
  onNotificationsDone,
}: StepContentProps & StepContentExtraProps) {
  return (
    <View testID={`onboarding-step-${step}`} style={styles.stepBody}>
      <Text style={styles.stepEyebrow}>
        {t('onboarding.step_label', {
          current: step,
          total: ONBOARDING_TOTAL_STEPS,
          defaultValue: `Step ${step} of ${ONBOARDING_TOTAL_STEPS}`,
        })}
      </Text>

      {step === 1 && <Step01Welcome onNext={onNext} />}
      {step === 2 && (
        <Step02Language
          value={data.language}
          onChange={(lang) => setField('language', lang)}
        />
      )}
      {step === 3 && <Step03ValueProp onNext={onNext} />}
      {step === 4 && (
        <Step04Country
          country={data.country}
          governorate={data.governorate}
          onChangeCountry={(c) => setField('country', c)}
          onChangeGovernorate={(g) => setField('governorate', g)}
        />
      )}
      {step === 5 && <Step05Trust onNext={onNext} />}
      {step === 6 && (
        <Step06Age
          value={data.age_group}
          onChange={(age) => setField('age_group', age)}
          onSkip={onNext}
        />
      )}
      {step === 7 && (
        <Step07Gender
          value={data.gender}
          onChange={(g) => setField('gender', g)}
          onSkip={onNext}
        />
      )}
      {step === 8 && (
        <Step08Priorities
          value={data.priorities ?? []}
          onChange={(p) => setField('priorities', p)}
        />
      )}
      {step === 9 && (
        <Step09Budget
          value={data.budget}
          onChange={(b) => setField('budget', b)}
        />
      )}
      {step === 10 && (
        <Step10BrandAttitude
          value={data.brand_attitude}
          onChange={(b) => setField('brand_attitude', b)}
        />
      )}
      {step === 11 && (
        <Step11Attribution
          value={data.attribution_source}
          onChange={(s) => setField('attribution_source', s)}
        />
      )}
      {step === 12 && <Step12CohortProof onNext={onNext} />}
      {step === 13 && (
        <Step13Anticipation
          onNext={onNext}
          governorate={data.governorate}
        />
      )}
      {step === 14 && (
        <Step14Loading
          cohortPeerCount={47}
          onComplete={onLoadingComplete}
        />
      )}
      {step === 15 && (
        <Step15Reveal
          onNext={onNext}
          profile={{
            priorities: data.priorities ?? [],
            budget: data.budget,
            brand_attitude: data.brand_attitude,
            age_group: data.age_group,
            gender: data.gender,
            country: data.country,
            governorate: data.governorate,
          } as any}
        />
      )}
      {step === 16 && (
        <Step16Account
          onSelectMethod={onSelectAuthMethod}
          appleAvailable={Platform.OS === 'ios'}
        />
      )}
      {step === 17 && <Step17Notifications onDone={onNotificationsDone} />}
    </View>
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
