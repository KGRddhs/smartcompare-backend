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
import { SlideTransition } from '../../components/SlideTransition';
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
  /**
   * F-S2.step16-skip (task #42): when true, Step16Account ("Save your
   * advisor — Sign in so X") is omitted from the traversal. Step 15
   * next-press advances directly to Step 17; back from Step 17 goes
   * to Step 15; the progress denominator drops to 16; Step 16 is
   * never mounted.
   *
   * Production wiring (App.tsx → NewOnboardingHost): the Onboarding
   * stack is gated on `isAuthenticated === true` at the navigator
   * level, so any user reaching this orchestrator is already
   * authenticated. Asking them to "Save your advisor — Sign in so X"
   * at Step 16 is redundant (Ahmed walk 2026-05-29, task #42).
   *
   * Defaults `false` so the original 17-step sequence is preserved
   * for any future call site (e.g. an anonymous-trial flow) + for
   * existing tests that don't pass the prop.
   */
  isAuthenticated?: boolean;
}

/**
 * Canonical step traversal orders. The authenticated variant filters
 * out Step 16 (Save Advisor — Sign in). Step state remains the canonical
 * numeric step (1..17) the rest of the codebase pivots on; the orchestrator
 * just navigates BY-SEQUENCE rather than by raw step++/-- so a 15 → 17
 * hop is a single index advance.
 */
const FULL_STEP_SEQUENCE: ReadonlyArray<OnboardingStep> = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
];
const AUTHED_STEP_SEQUENCE: ReadonlyArray<OnboardingStep> = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17,
];

/**
 * Steps that render their own CTA inline (no orchestrator footer needed).
 * The orchestrator's back+Next footer would otherwise stack a duplicate
 * "Continue" / "Next" button below the step's own primary action — which
 * Ahmed flagged in F-S2.W4.hotfix as the "stray magnifier + Next" symptom
 * on Step15 (the BackIcon read as a magnifier glyph on his device + the
 * orchestrator's Next button rendered alongside Step15's own "Compare
 * your first product" CTA).
 *
 * The list below covers every step that owns its primary action:
 *   - 1  Step01Welcome:        Continue + Sign-in link
 *   - 3  Step03ValueProp:      Continue (own Button)
 *   - 5  Step05Trust:          "I'm in"
 *   - 12 Step12CohortProof:    Continue
 *   - 13 Step13Anticipation:   "Almost there…" / Continue (dynamic CTA)
 *   - 14 Step14Loading:        no CTA, auto-completes after 3.2s floor
 *   - 15 Step15Reveal:         "Compare your first product"
 *   - 16 Step16Account:        Apple / Google / email CTAs
 *   - 17 Step17Notifications:  Allow / Maybe later
 *
 * Multi-input steps (2/4/6/7/8/9/10/11) keep the orchestrator footer
 * because they don't render their own primary action.
 */
const STEPS_WITH_OWN_CTA: ReadonlySet<OnboardingStep> = new Set([
  1, 3, 5, 12, 13, 14, 15, 16, 17,
]);

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
  isAuthenticated = false,
}: OnboardingFlowProps) {
  const { t } = useTranslation();
  const { isRTL, language } = useLanguage();
  const [step, setStep] = useState<OnboardingStep>(initialStep);
  const [data, setData] = useState<OnboardingFlowData>({ ...(initialData ?? {}) });

  // F-S2.step16-skip (task #42): pick the traversal sequence at mount.
  // `useMemo` so the array reference is stable across re-renders — the
  // shape is fixed (no state-bearing fields), so this is cheap.
  const stepSequence = useMemo<ReadonlyArray<OnboardingStep>>(() => {
    const base = isAuthenticated ? AUTHED_STEP_SEQUENCE : FULL_STEP_SEQUENCE;
    // `lastStep` (Bundle D edit-mode subset) trims the tail. We honor
    // both inputs so the auth-skip composes with the edit-mode subset
    // (Step 16 isn't in the edit subset 8-10 anyway, but the
    // composition is contract-correct).
    if (lastStep == null) return base;
    return base.filter((s) => s <= lastStep);
  }, [isAuthenticated, lastStep]);

  const terminalStep: OnboardingStep = stepSequence[stepSequence.length - 1];

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
    // F-S2.step16-skip: advance by sequence index, not by raw step++.
    // In the auth'd sequence, advancing from 15 lands on 17 (not 16)
    // because Step 16 isn't in the sequence array. terminalStep is
    // already sequence-aware (the last entry).
    const currentIndex = stepSequence.indexOf(step);
    const isAtTerminal = currentIndex < 0 || currentIndex >= stepSequence.length - 1;
    if (isAtTerminal) {
      fireEvent('onboarding_completed');
      onComplete(data);
      return;
    }
    setStep(stepSequence[currentIndex + 1]);
  }, [valid, step, data, onComplete, fireEvent, stepSequence]);

  const handleBack = useCallback(() => {
    setStep((prev: OnboardingStep) => {
      // F-S2.step16-skip: retreat by sequence index. In the auth'd
      // sequence, back from 17 lands on 15 (not 16). If the current
      // step somehow isn't in the sequence (defensive — shouldn't
      // happen under the prop contract), fall through to the
      // pre-skip linear retreat so the user is never trapped.
      const currentIndex = stepSequence.indexOf(prev);
      if (currentIndex > 0) return stepSequence[currentIndex - 1];
      if (currentIndex === 0) return prev; // at the first step
      // Fallback: not in sequence. Linear retreat with a 1 floor.
      return (prev > 1 ? ((prev - 1) as OnboardingStep) : prev);
    });
  }, [stepSequence]);

  // F-S2.step16-skip: progress denominator reflects the actual
  // sequence length. Auth'd flow = 16 steps; anonymous flow = 17.
  // Current-index is 1-based so "Step 5 of 17" reads naturally.
  const currentIndex = stepSequence.indexOf(step);
  const totalSteps = stepSequence.length;
  const currentStepDisplay = currentIndex >= 0 ? currentIndex + 1 : 1;
  const progress = currentStepDisplay / totalSteps;

  return (
    <SafeAreaView style={styles.safe}>
      <View
        testID="onboarding-progress"
        // Expose step totals on the host node for test assertions + a11y.
        // ProgressBar itself owns the visual fill animation. The
        // data-total-steps attribute reflects the ACTUAL traversal
        // length: 16 in the auth'd flow (Step 16 skipped) and 17 in
        // the anonymous flow. data-current-step exposes the canonical
        // step number for assertion (still 17 even though 16 was
        // skipped in the auth'd flow). data-current-step-index is the
        // 1-based position within the active sequence, useful for
        // "Step N of M" display assertions.
        {...{
          'data-total-steps': totalSteps,
          'data-current-step': step,
          'data-current-step-index': currentStepDisplay,
        }}
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
          {/* F-S2.X1 — SlideTransition chrome wrap. Keyed on `step` so a
              step transition retriggers the slide-in animation; same-step
              re-renders (data field updates, validation flips, etc.) do
              NOT replay the slide per the primitive contract. Direction
              mirrors I18nManager.isRTL via the primitive itself — LTR
              slides in from right (+width), RTL from left (-width).
              motion.screenTransition timing (320ms cubic-bezier 0.32,
              0.72, 0, 1) is owned by the primitive. Single wrap at the
              chrome layer means we get the rhythm across all 17 steps
              without touching individual step files. */}
          <SlideTransition step={step} testID="onboarding-step-slide">
            <StepContent
              step={step}
              data={data}
              setField={setField}
              t={t}
              currentStepIndex={currentStepDisplay}
              totalSteps={totalSteps}
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
          </SlideTransition>
        </ScrollView>
      </View>

      {/* F-S2.W4.hotfix: orchestrator footer back chevron stays on
          every step (useful for backtracking from any surface), but
          the orchestrator's Next/Continue button is gated to steps
          WITHOUT their own primary CTA inline. Per Ahmed's W4 device
          walk on Step15 ("stray magnifier + Next" — the BackIcon
          chevron reads as a magnifier glyph at small sizes on iOS +
          the orchestrator's Next button stacked under Step15's own
          "Compare your first product" CTA), gating the Next button
          alone removes the duplicate without breaking the back-chevron
          back-compat that 6 existing OnboardingFlow tests pin
          (onboarding-back/onboarding-next interactions). */}
      <View style={styles.footer} testID="onboarding-footer">
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

        {STEPS_WITH_OWN_CTA.has(step) ? null : (
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
        )}
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
  /**
   * F-S2.step16-skip (task #42): the user-facing "Step X of Y" eyebrow
   * should reflect the active traversal length — 16 in the auth'd flow,
   * 17 in the anonymous flow. Passed through from the orchestrator so
   * the eyebrow stays consistent with the progress-bar denominator.
   */
  currentStepIndex: number;
  totalSteps: number;
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
  currentStepIndex,
  totalSteps,
  onNext,
  onLoadingComplete,
  onSelectAuthMethod,
  onNotificationsDone,
}: StepContentProps & StepContentExtraProps) {
  return (
    <View testID={`onboarding-step-${step}`} style={styles.stepBody}>
      <Text style={styles.stepEyebrow}>
        {t('onboarding.step_label', {
          // F-S2.step16-skip: eyebrow shows position-in-sequence
          // (1..totalSteps) not the canonical step number. Auth'd flow
          // at Step 17 displays "Step 16 of 16" not "Step 17 of 16".
          current: currentStepIndex,
          total: totalSteps,
          defaultValue: `Step ${currentStepIndex} of ${totalSteps}`,
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
          governorate={data.governorate}
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
