/**
 * A9 — the blocking screen behind the force-update lever.
 *
 * Rendered INSTEAD of the whole navigator (App.tsx, after the splash gate
 * releases) when `useForcedUpdateGate()` returns a gate. There is
 * deliberately no dismiss, no back affordance and no route in or out: the
 * only exit is updating the app. That is the point of the lever — but it
 * also means every other guard in this feature is written to fail open, so
 * this screen is only reachable on an affirmative server answer.
 *
 * COPY (Build Principle #4 — never frame the app as scary): this is a
 * "there is a newer version" message, not a failure notice. No banned
 * vocabulary in either language (see `src/i18n/.copy-policy.json`).
 *
 * RTL: the layout is centred and carries no directional icon and no
 * physical `textAlign: left/right`, so it reads correctly in both
 * `I18nManager.isRTL` branches. Arabic gets the 1.7x line-height
 * multiplier on the body presets, same as PaywallBanner.
 */
import React from 'react';
import { Linking, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Sparkles } from 'lucide-react-native';
import { Button } from '../components/Button';
import { arabicLineHeightMultiplier, colors, radii, spacing, typography } from '../theme';

export interface UpdateRequiredScreenProps {
  /** Platform store URL. When absent, the screen asks the user to update
   *  from their own store rather than showing a CTA that goes nowhere. */
  updateUrl?: string | null;
  testID?: string;
}

export default function UpdateRequiredScreen({
  updateUrl,
  testID = 'update-required',
}: UpdateRequiredScreenProps) {
  const { t, i18n } = useTranslation();
  const isAR = i18n.language?.startsWith('ar');
  const arLineHeight = (base: number) => base * arabicLineHeightMultiplier;

  const handleOpenStore = () => {
    if (!updateUrl) return;
    try {
      const maybePromise = Linking.openURL(updateUrl);
      // A store URL the OS refuses leaves the user on this screen with the
      // manual instruction still visible — nothing to surface, nothing to
      // crash on.
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => {});
      }
    } catch {
      /* Linking unavailable — the manual line below still applies. */
    }
  };

  return (
    <SafeAreaView style={styles.safe} testID={testID}>
      <View style={styles.content}>
        <View style={styles.iconCircle}>
          <Sparkles size={28} color={colors.accent} />
        </View>

        <Text
          style={[styles.title, isAR && { lineHeight: arLineHeight(typography.display.lineHeight) }]}
          testID={`${testID}-title`}
        >
          {t('update.required.title')}
        </Text>

        <Text
          style={[styles.body, isAR && { lineHeight: arLineHeight(typography.body.lineHeight) }]}
          testID={`${testID}-body`}
        >
          {t('update.required.body')}
        </Text>

        {updateUrl ? (
          <Button
            title={t('update.required.cta')}
            onPress={handleOpenStore}
            style={styles.cta}
            testID={`${testID}-cta`}
          />
        ) : (
          <Text
            style={[
              styles.manual,
              isAR && { lineHeight: arLineHeight(typography.caption.lineHeight) },
            ]}
            testID={`${testID}-manual`}
          >
            {t('update.required.manual')}
          </Text>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: radii.chip,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  body: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  cta: {
    alignSelf: 'stretch',
  },
  manual: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});
