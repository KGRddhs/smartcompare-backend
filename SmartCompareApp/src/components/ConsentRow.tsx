/**
 * W3-16 — consent capture control.
 *
 * One explicit, unchecked-by-default checkbox: ticking it is the Terms
 * acceptance AND the 13+ age attestation (the sentence states both; the
 * payload records both separately, see services/consent.ts). The Terms and
 * Privacy words are pressable spans that open the Legal screen.
 *
 * Layout uses flexDirection 'row' so React Native mirrors it under RTL; no
 * directional icon is used.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography } from '../theme';

export type LegalDoc = 'terms' | 'privacy';

interface ConsentRowProps {
  checked: boolean;
  onToggle: () => void;
  onOpenLegal: (doc: LegalDoc) => void;
  error?: boolean;
  disabled?: boolean;
  testID?: string;
}

export function ConsentRow({
  checked,
  onToggle,
  onOpenLegal,
  error = false,
  disabled = false,
  testID = 'consent-checkbox',
}: ConsentRowProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Pressable
          testID={testID}
          onPress={onToggle}
          disabled={disabled}
          accessibilityRole="checkbox"
          accessibilityState={{ checked, disabled }}
          accessibilityLabel={t('auth.consent.prefix')}
          hitSlop={12}
          style={[styles.box, checked ? styles.boxChecked : null, error ? styles.boxError : null]}
        >
          {checked ? <Text style={styles.tick}>{'✓'}</Text> : null}
        </Pressable>
        <Text style={styles.text}>
          {t('auth.consent.prefix')}{' '}
          <Text style={styles.link} onPress={() => onOpenLegal('terms')} accessibilityRole="link">
            {t('common.terms')}
          </Text>
          {/* The conjunction carries its own spacing: English " and ", Arabic
              " و" — the Arabic conjunction attaches to the next word. */}
          {t('auth.consent.and')}
          <Text style={styles.link} onPress={() => onOpenLegal('privacy')} accessibilityRole="link">
            {t('common.privacy')}
          </Text>
        </Text>
      </View>
      {error ? (
        <Text testID="consent-error" style={styles.errorText}>
          {t('auth.consent.required')}
        </Text>
      ) : null}
    </View>
  );
}

const BOX_SIZE = 22;

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.base,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  box: {
    width: BOX_SIZE,
    height: BOX_SIZE,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginEnd: spacing.sm,
    marginTop: 1,
  },
  boxChecked: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  boxError: {
    borderColor: colors.destructive,
  },
  tick: {
    color: colors.text.onInverse,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 16,
  },
  text: {
    ...typography.small,
    flex: 1,
    color: colors.text.secondary,
  },
  link: {
    color: colors.text.primary,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    marginTop: spacing.xs,
  },
});

export default ConsentRow;
