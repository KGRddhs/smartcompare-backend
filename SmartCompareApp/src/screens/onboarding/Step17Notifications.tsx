/**
 * Step17Notifications — Phase 2 Task 23.
 *
 * "Be the first to know when prices drop" — Allow / Not now. Asked AFTER
 * value built, not at launch. Compact mock notification preview as a
 * visual element. See design § 2 row 17 + § 4g audit ("Want price-drop
 * alerts?" → "Be the first to know when prices drop").
 *
 * Permission gate via expo-notifications. Either path advances to the
 * orchestrator's onComplete via onDone(granted: boolean). The 17-step
 * flow ends here.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import * as Notifications from 'expo-notifications';
import { colors, spacing, typography, radii } from '../../theme';

interface Props {
  /** Fires after the user picks Allow (with the OS permission result) or Not now. */
  onDone: (granted: boolean) => void;
}

// JSX OnboardingExtras.jsx Tag function (349-365) — head + body pair
// with emerald dot + bg.secondary card. Restrained per JSX, no SVG.
function NotificationTag({
  head,
  body,
  testID,
}: {
  head: string;
  body: string;
  testID?: string;
}) {
  return (
    <View style={styles.tag} testID={testID}>
      <View style={styles.tagDot} testID={`${testID}-dot`} />
      <View style={styles.tagText}>
        <Text style={styles.tagHead}>{head}</Text>
        <Text style={styles.tagBody}>{body}</Text>
      </View>
    </View>
  );
}

export function Step17Notifications({ onDone }: Props) {
  const { t } = useTranslation();

  const handleAllow = async () => {
    try {
      const result = await Notifications.requestPermissionsAsync();
      onDone(Boolean(result?.granted));
    } catch {
      // Best-effort: a denied permission is not an error path. Surface as
      // "not now" to the orchestrator and continue — nothing scary surfaces.
      onDone(false);
    }
  };

  const handleNotNow = () => onDone(false);

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <View testID="s17-preview" style={styles.previewCard}>
          <Text style={styles.previewBrand}>Qaren</Text>
          <Text style={styles.previewBody}>
            {t('onboarding.s17.preview_body')}
          </Text>
          <Text style={styles.previewMeta}>
            {t('onboarding.s17.preview_meta')}
          </Text>
        </View>

        <Text style={styles.title}>{t('onboarding.s17.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s17.subtitle')}</Text>

        {/* S2.W4 — 3 Tag rows per JSX OnboardingExtras.jsx:319-323 +
            Tag function (349-365). Decision insights / Cohort echoes /
            Smart shortcuts — head + body pair with emerald dot + bg.
            secondary card. Restrained text-only (no SVG glyphs) per
            JSX spec. */}
        <View style={styles.tags} testID="s17-tags">
          <NotificationTag
            testID="s17-tag-insights"
            head={t('onboarding.s17.tag_insights_head', {
              defaultValue: 'Decision insights',
            })}
            body={t('onboarding.s17.tag_insights_body', {
              defaultValue:
                'When a peer match strengthens your last verdict.',
            })}
          />
          <NotificationTag
            testID="s17-tag-echoes"
            head={t('onboarding.s17.tag_echoes_head', {
              defaultValue: 'Cohort echoes',
            })}
            body={t('onboarding.s17.tag_echoes_body', {
              defaultValue:
                'When 5+ peers your age just compared the same pair.',
            })}
          />
          <NotificationTag
            testID="s17-tag-shortcuts"
            head={t('onboarding.s17.tag_shortcuts_head', {
              defaultValue: 'Smart shortcuts',
            })}
            body={t('onboarding.s17.tag_shortcuts_body', {
              defaultValue:
                'A heads-up when an item you scanned drops sharply.',
            })}
          />
        </View>
      </View>

      <View style={styles.choices}>
        <TouchableOpacity
          testID="s17-allow"
          onPress={handleAllow}
          accessibilityRole="button"
          style={[styles.cta, styles.ctaPrimary]}
        >
          <Text style={[styles.ctaLabel, styles.ctaLabelOnDark]}>
            {t('onboarding.s17.allow')}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          testID="s17-not-now"
          onPress={handleNotNow}
          accessibilityRole="button"
          style={styles.notNow}
        >
          <Text style={styles.notNowLabel}>{t('onboarding.s17.not_now')}</Text>
        </TouchableOpacity>
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
  heroBlock: {
    flex: 1,
    alignItems: 'center',
    paddingTop: spacing.xl,
  },
  previewCard: {
    width: '100%',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
    marginBottom: spacing['2xl'],
  },
  previewBrand: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
  },
  previewBody: {
    ...typography.body,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  previewMeta: {
    ...typography.caption,
    color: colors.text.placeholder,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
  },
  choices: {
    gap: spacing.md,
  },
  cta: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.button,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaPrimary: {
    backgroundColor: colors.cta.primary,
  },
  ctaLabel: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  ctaLabelOnDark: {
    color: colors.cta.onPrimary,
  },
  notNow: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  notNowLabel: {
    ...typography.body,
    color: colors.text.secondary,
  },
  // S2.W4 tag rows below the subtitle — restrained bg.secondary cards
  // with an emerald dot + head/body pair per JSX OnboardingExtras.jsx
  // Tag function (349-365).
  tags: {
    width: '100%',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  tag: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  tagDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accent,
    marginTop: 6,
    flexShrink: 0,
  },
  tagText: {
    flex: 1,
    minWidth: 0,
  },
  tagHead: {
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 13 * 1.3,
    color: colors.text.primary,
  },
  tagBody: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
    marginTop: 2,
  },
});
