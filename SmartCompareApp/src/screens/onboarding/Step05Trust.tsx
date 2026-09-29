/**
 * Step05Trust — Bundle E S2.W1 rewrite.
 *
 * REWRITE not compose — JSX OnboardingExtras.jsx s5 dropped the prior
 * lock-badge hero entirely and uses three `<PrivacyRow icon head body />`
 * rows with an emerald-accentWord headline ("Your data, your `call`.")
 * and an "I'm in" CTA. Memory pin:
 * feedback_compose_vs_rewrite_phrasing.md.
 *
 * Trust bridge — pre-empts the "why do you need this?" objection BEFORE
 * we ask for age, gender, etc. The 3 rows mirror the JSX recipe verbatim:
 *   - check    "What we use"          / what's collected
 *   - search   "What reaches OpenAI"  / what is sent to OpenAI, and what never is
 *     (S69 U3: retitled from "What's anonymized", which no longer
 *     described the body)
 *   - X        "What we never share"  / name and email
 *
 * S69 U3 R5 — every sentence here must be true of what the code sends. The
 * budget tier IS in the verdict prompt (extraction_service.py
 * _build_preferences_prompt, "Budget level: …"), so it is no longer listed as
 * never shared, and the subtitle counts two off-limits items, not three. The
 * old "Your queries help MYEZ get smarter. We strip … first" was a data-use
 * claim; it now states what is sent to OpenAI. No opt-out is promised (the
 * Profile AI-sharing toggle routes nothing today, #266).
 *
 * Privacy invariant per qaren-cohort skill: this surface conveys policy,
 * doesn't expose actual signal content. The PrivacyRow primitive owns
 * the visual recipe (36px accentLight circle + accentDark icon).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Check, Search, X } from 'lucide-react-native';
import { Button } from '../../components/Button';
import { PrivacyRow } from '../../components/primitives/PrivacyRow';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
}

const ICON_SIZE = 18;

export function Step05Trust({ onNext }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.body}>
        {/* Emerald accent on "call" per JSX OnbHeadline pattern (matches
            Step04's "shop" accent treatment). Nested Text spans inherit
            sizing from the parent; the accent span overrides color. */}
        <Text style={styles.headline}>
          {t('onboarding.s5.title_before', { defaultValue: 'Your data, your ' })}
          <Text style={styles.headlineAccent}>
            {t('onboarding.s5.title_accent', { defaultValue: 'call' })}
          </Text>
          {t('onboarding.s5.title_after', { defaultValue: '.' })}
        </Text>

        <Text style={styles.subtitle}>
          {t('onboarding.s5.subtitle', {
            defaultValue:
              'A handful of inputs sharpen the match. Two are off-limits, forever.',
          })}
        </Text>

        <View style={styles.rows}>
          <PrivacyRow
            testID="trust-row-use"
            icon={
              <Check
                size={ICON_SIZE}
                color={colors.accentDark}
                strokeWidth={3}
              />
            }
            head={t('onboarding.s5.privacy_use_head', { defaultValue: 'What we use' })}
            body={t('onboarding.s5.privacy_use_body', {
              defaultValue:
                'Age range, governorate, priorities, budget tier, brand stance — to find peers like you and tailor each verdict.',
            })}
          />
          <PrivacyRow
            testID="trust-row-anon"
            icon={
              <Search
                size={ICON_SIZE}
                color={colors.accentDark}
                strokeWidth={3}
              />
            }
            head={t('onboarding.s5.privacy_anon_head', { defaultValue: 'What reaches OpenAI' })}
            body={t('onboarding.s5.privacy_anon_body', {
              defaultValue:
                'To write each comparison, MYEZ sends OpenAI your product names and preferences such as priorities and budget tier — never your name, email or account.',
            })}
          />
          <PrivacyRow
            testID="trust-row-never"
            icon={
              <X size={ICON_SIZE} color={colors.accentDark} strokeWidth={3} />
            }
            head={t('onboarding.s5.privacy_never_head', {
              defaultValue: 'What we never share',
            })}
            body={t('onboarding.s5.privacy_never_body', {
              defaultValue: 'Your name. Your email. Not now, not ever.',
            })}
          />
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          // CTA copy is "I'm in" per JSX, not "Continue" — earns the
          // user's posture before the demographics block lands.
          title={t('onboarding.s5.cta', { defaultValue: "I'm in" })}
          variant="primary"
          onPress={onNext}
          testID="trust-continue"
        />
      </View>
    </View>
  );
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
    paddingTop: spacing.xl,
  },
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
    marginBottom: spacing['2xl'],
  },
  rows: {
    gap: spacing.lg,
  },
  footer: {
    paddingTop: spacing.lg,
  },
});
