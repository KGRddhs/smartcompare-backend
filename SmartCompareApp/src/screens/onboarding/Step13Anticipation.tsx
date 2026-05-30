/**
 * Step13Anticipation — Bundle E S2.W3 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingExtras.jsx
 * s13 QarenOnboardingBuildScreen (lines 201-276).
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — the prior Phase 2 anatomy (ConcentricMotif hero + bare
 * title + immediate Continue CTA) shares only the screen container with
 * the JSX recipe. The JSX dictates:
 *   1. Emerald-accentWord headline "Building your `advisor`…"
 *   2. Subtitle "One profile, four steps. Stay with us."
 *   3. 4-stage StageChecklist auto-progressing every STAGE_TICK_MS
 *      (region → priorities → peers → calibrate)
 *   4. Factoid line below the card (centered, 13/400 secondary)
 *   5. Sticky CTA disabled with "Almost there…" copy until all stages
 *      reach done; flips to "Continue" + enabled once complete.
 *
 * Build moment that earns the theatrical loading on Step14. Reuses the
 * shipped StageChecklist primitive (24px circles, ✓⟳○ glyphs, haptic on
 * transition into done per its existing test contract).
 *
 * Governorate substitution into the "peers in {governorate}" stage:
 * prop accepted from OnboardingFlow which passes `data.governorate`.
 * Per qaren-cohort privacy invariant, when governorate is null we fall
 * back to "the GCC" — no raw identifying value leaks into the copy.
 *
 * STAGES MUST stay in sync with Step14 (LoadingScreenVariants
 * ConcentricVariant) so the perceived continuity holds. Both surfaces
 * read from the same STAGE_IDS array shape, but Step13 sets the
 * orchestration cadence (auto-progress with 900ms tick) while Step14
 * runs them against the SSE / fetch progress instead.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { StageChecklist, Stage } from '../../components/StageChecklist';
import { colors, spacing, typography } from '../../theme';
import { OnboardingGovernorate } from './types';

interface Props {
  onNext: () => void;
  /** From OnboardingFlow `data.governorate` — falls back to "the GCC". */
  governorate?: OnboardingGovernorate;
  /** Stage tick override; default 900ms per JSX setTimeout(850). */
  stageTickMs?: number;
}

const DEFAULT_STAGE_TICK_MS = 900;

const STAGE_IDS = ['region', 'priorities', 'peers', 'calibrate'] as const;

export function Step13Anticipation({
  onNext,
  governorate,
  stageTickMs = DEFAULT_STAGE_TICK_MS,
}: Props) {
  const { t } = useTranslation();
  // tick advances every stageTickMs from 0 to STAGE_IDS.length. The
  // status of each stage is derived from tick vs its index.
  const [tick, setTick] = useState(0);
  const complete = tick >= STAGE_IDS.length;

  useEffect(() => {
    if (complete) return;
    const id = setTimeout(() => setTick((prev) => prev + 1), stageTickMs);
    return () => clearTimeout(id);
  }, [tick, complete, stageTickMs]);

  // Governorate substitution: null/undefined → "the GCC" per privacy
  // invariant (no raw identifying value in copy when user opted out).
  const governorateDisplay = governorate
    ? t(`onboarding.s4.gov_${governorate.toLowerCase()}`, {
        defaultValue: governorate,
      })
    : t('onboarding.s13.gcc_fallback', { defaultValue: 'the GCC' });

  const stages: Stage[] = useMemo(
    () =>
      STAGE_IDS.map((id, index) => {
        let status: Stage['status'] = 'pending';
        if (tick > index) status = 'done';
        else if (tick === index) status = 'active';
        return {
          id,
          status,
          label: t(`onboarding.s13.stage_${id}`, {
            governorate: governorateDisplay,
            defaultValue: defaultStageCopy(id, governorateDisplay),
          }),
        };
      }),
    [tick, t, governorateDisplay],
  );

  const ctaLabel = complete
    ? t('onboarding.s13.cta_ready', { defaultValue: 'Continue' })
    : t('onboarding.s13.cta_loading', { defaultValue: 'Almost there…' });

  return (
    <View style={styles.container}>
      <View style={styles.body}>
        {/* Headline — emerald accent on "advisor" per JSX OnbHeadline. */}
        <Text style={styles.headline} testID="s13-headline">
          {t('onboarding.s13.title_before', { defaultValue: 'Building your ' })}
          <Text style={styles.headlineAccent}>
            {t('onboarding.s13.title_accent', { defaultValue: 'advisor' })}
          </Text>
          {t('onboarding.s13.title_after', { defaultValue: '…' })}
        </Text>
        <Text style={styles.subtitle}>
          {t('onboarding.s13.subtitle_v2', {
            defaultValue: 'One profile, four steps. Stay with us.',
          })}
        </Text>

        <View style={styles.stageCard} testID="s13-stage-card">
          <StageChecklist stages={stages} />
        </View>

        <Text style={styles.factoid} testID="s13-factoid">
          {t('onboarding.s13.factoid', {
            governorate: governorateDisplay,
            defaultValue: `Did you know — 73% of ${governorateDisplay} shoppers your age prioritize Quality first.`,
          })}
        </Text>
      </View>

      <View style={styles.footer}>
        <Button
          title={ctaLabel}
          variant="primary"
          onPress={onNext}
          disabled={!complete}
          testID="s13-cta"
        />
      </View>
    </View>
  );
}

function defaultStageCopy(
  id: (typeof STAGE_IDS)[number],
  governorate: string,
): string {
  switch (id) {
    case 'region':
      return 'Locking your region';
    case 'priorities':
      return 'Mapping your priorities';
    case 'peers':
      return `Matching to peers in ${governorate}`;
    case 'calibrate':
      return 'Calibrating your advisor';
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    justifyContent: 'space-between',
  },
  body: {
    flex: 1,
    paddingTop: spacing.sm,
  },
  // OnbHeadline analog — same display weight as Step04 / Step05, with
  // the emerald accent span isolated so RTL flips correctly.
  headline: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  headlineAccent: {
    color: colors.accent,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  // The JSX card sits on bg.secondary with a 1px border.light hairline +
  // 20px radius — the inner StageChecklist owns its own row padding so
  // we just provide the surrounding card chrome.
  stageCard: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border.light,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  // Factoid stays restrained: secondary text, centered, 13/400 per JSX.
  factoid: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.5,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.xl,
    paddingHorizontal: spacing.md,
  },
  footer: {
    paddingTop: spacing.lg,
  },
});
