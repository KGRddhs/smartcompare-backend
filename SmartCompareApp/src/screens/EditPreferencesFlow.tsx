// SmartCompareApp/src/screens/EditPreferencesFlow.tsx
//
// B2 sequential 4-page preferences edit (Bundle A §2). Replaces the dead
// Profile → "Preferences" handler (which used to navigate to the pre-auth
// Onboarding stack — invisible to authed users).

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, X } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import PrioritiesPicker from '../components/PrioritiesPicker';
import BudgetPicker, { type BudgetValue } from '../components/BudgetPicker';
import LifestylePicker from '../components/LifestylePicker';
import BrandAttitudePicker, { type BrandAttitudeValue } from '../components/BrandAttitudePicker';
import { getPreferences, savePreferences } from '../services/api';
import { toCanonicalPriorities } from '../utils/priorities';
import type { RootStackParamList, UserPreferences } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'EditPreferences'>;

const PAGES = ['priorities', 'budget', 'lifestyle', 'brand'] as const;
type PageKey = typeof PAGES[number];

const DEFAULT_PREFS: UserPreferences = {
  priorities: [],
  budget: 'mid',
  lifestyle: [],
  brand_attitude: 'best_of_both',
};

export default function EditPreferencesFlow({ navigation }: Props) {
  const { t } = useTranslation();
  const [pageIndex, setPageIndex] = useState(0);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const p = await getPreferences();
        const base = p ?? DEFAULT_PREFS;
        // Map any cohort-seeded priorities to canonical display keys so the
        // picker shows them as selected (otherwise they're invisible yet
        // still fill the 3-cap, blocking selection — device bug 2026-07-04).
        setPrefs({ ...base, priorities: toCanonicalPriorities(base.priorities) });
      } catch {
        setPrefs(DEFAULT_PREFS);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const next = () => {
    try { Haptics.selectionAsync(); } catch {}
    setPageIndex((i) => Math.min(i + 1, PAGES.length - 1));
  };

  const back = () => {
    if (pageIndex === 0) {
      navigation.goBack();
      return;
    }
    try { Haptics.selectionAsync(); } catch {}
    setPageIndex((i) => i - 1);
  };

  const save = async () => {
    if (!prefs) return;
    setSaving(true);
    setErrorKey(null);
    try {
      const result = await savePreferences(prefs);
      if (result.success) {
        try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); } catch {}
        navigation.goBack();
      } else {
        setErrorKey('preferences.error.saveFailed');
      }
    } catch {
      setErrorKey('preferences.error.saveFailed');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !prefs) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  const pageKey: PageKey = PAGES[pageIndex];
  const isLast = pageIndex === PAGES.length - 1;

  const update = (patch: Partial<UserPreferences>) => setPrefs({ ...prefs, ...patch });

  // F-S1.5i: Step 1 (priorities) requires at least 1 pick before Continue
  // is enabled. Backend Pydantic `priorities: min_length=1` rejected
  // empty-array submits as 422; gating the FE button at the source
  // prevents the round-trip and the scary error bar.
  const isContinueDisabled =
    saving ||
    (pageKey === 'priorities' && (prefs.priorities?.length ?? 0) === 0);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={back}
          accessibilityRole="button"
          accessibilityLabel={pageIndex === 0 ? t('common.close') : t('common.back')}
          style={styles.headerBtn}
        >
          {pageIndex === 0 ? (
            <X size={22} color={colors.text.primary} />
          ) : (
            <ChevronLeft size={24} color={colors.text.primary} />
          )}
        </TouchableOpacity>
        <Text style={styles.pageDots}>{`${pageIndex + 1} / ${PAGES.length}`}</Text>
        <View style={styles.headerBtn} />
      </View>

      <ScrollView
        style={styles.body}
        contentContainerStyle={styles.bodyContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.pageTitle}>{t(`preferences.${pageKey}.title`)}</Text>

        {pageKey === 'priorities' && (
          <PrioritiesPicker
            value={prefs.priorities ?? []}
            onChange={(v) => update({ priorities: v })}
          />
        )}
        {pageKey === 'budget' && (
          <BudgetPicker
            value={(prefs.budget ?? 'mid') as BudgetValue}
            onChange={(v) => update({ budget: v })}
          />
        )}
        {pageKey === 'lifestyle' && (
          <LifestylePicker
            value={prefs.lifestyle ?? []}
            onChange={(v) => update({ lifestyle: v })}
          />
        )}
        {pageKey === 'brand' && (
          <BrandAttitudePicker
            value={(prefs.brand_attitude ?? 'best_of_both') as BrandAttitudeValue}
            onChange={(v) => update({ brand_attitude: v })}
          />
        )}
      </ScrollView>

      {errorKey ? <Text style={styles.errorText}>{t(errorKey)}</Text> : null}

      {/* F-S1.5i: Step 1 hint when no priority picked yet — keeps the
          flow invitational instead of red-erroring after a 422. */}
      {pageKey === 'priorities' && (prefs.priorities?.length ?? 0) === 0 ? (
        <Text style={styles.continueHint}>
          {t('editprefs.continue.disabled', {
            defaultValue: 'Pick at least one priority to continue',
          })}
        </Text>
      ) : null}

      <View style={styles.footer}>
        <TouchableOpacity
          onPress={isLast ? save : next}
          disabled={isContinueDisabled}
          style={[styles.btn, isContinueDisabled && styles.btnDisabled]}
          accessibilityRole="button"
          accessibilityState={{ disabled: isContinueDisabled }}
        >
          {saving ? (
            <ActivityIndicator color={colors.cta.onPrimary} />
          ) : (
            <Text style={styles.btnText}>
              {isLast ? t('preferences.flow.save') : t('preferences.flow.continue')}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  headerBtn: { width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  pageDots: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  body: {
    flex: 1,
  },
  bodyContent: {
    padding: spacing.lg,
    paddingBottom: spacing.md,
  },
  pageTitle: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.lg,
  },
  footer: {
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
  },
  btn: {
    backgroundColor: colors.cta.primary,
    padding: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    padding: spacing.md,
    textAlign: 'center',
  },
  // F-S1.5i: gentle hint shown above the disabled Continue button when
  // user is on the priorities step with nothing picked. Placeholder
  // color keeps it quiet next to the dark button.
  continueHint: {
    ...typography.small,
    color: colors.text.placeholder,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xs,
    textAlign: 'center',
  },
});
