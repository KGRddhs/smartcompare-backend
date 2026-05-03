import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp, NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { ProgressBar } from '../components/ProgressBar';
import { useLanguage } from '../hooks/useLanguage';
import { savePreferences } from '../services/api';
import { RootStackParamList, OnboardingData } from '../types';

const TOTAL_STEPS = 6;

const REGIONS = [
  { value: 'bahrain', flag: '🇧🇭' },
  { value: 'saudi_arabia', flag: '🇸🇦' },
  { value: 'uae', flag: '🇦🇪' },
  { value: 'kuwait', flag: '🇰🇼' },
  { value: 'qatar', flag: '🇶🇦' },
  { value: 'oman', flag: '🇴🇲' },
] as const;

const PRIORITY_OPTIONS = [
  'price', 'quality', 'brand_reputation', 'durability',
  'latest_features', 'ease_of_use', 'eco_friendly', 'health_safety',
] as const;

const BUDGET_OPTIONS = ['budget', 'mid', 'premium'] as const;

const LIFESTYLE_OPTIONS = [
  'gamer', 'photographer', 'fitness_enthusiast', 'vegan', 'sensitive_skin',
  'parent', 'student', 'professional', 'outdoor_adventurer', 'minimalist', 'tech_enthusiast',
] as const;

const BRAND_OPTIONS = ['brand_loyal', 'function_first', 'best_of_both'] as const;

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Onboarding'>;
  route?: NativeStackScreenProps<RootStackParamList, 'Onboarding'>['route'];
  onComplete?: () => void;
};

export default function OnboardingScreen({ navigation, route, onComplete }: Props) {
  // When opened from the Profile screen's StyleProfileCard, the route carries
  // source='styleProfile' so we surface the "These were inferred" banner.
  const isInferredEdit = route?.params?.source === 'styleProfile';
  const { t } = useTranslation();
  const { language, switchLanguage } = useLanguage();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  // Onboarding data
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'ar'>(language);
  const [region, setRegion] = useState<string>('');
  const [priorities, setPriorities] = useState<string[]>([]);
  const [budget, setBudget] = useState<string>('');
  const [lifestyle, setLifestyle] = useState<string[]>([]);
  const [brandAttitude, setBrandAttitude] = useState<string>('');

  const progress = (step + 1) / TOTAL_STEPS;

  const isStepValid = (): boolean => {
    switch (step) {
      case 0: return true; // language always has a default
      case 1: return region !== '';
      case 2: return priorities.length >= 1 && priorities.length <= 3;
      case 3: return budget !== '';
      case 4: return true; // lifestyle is optional
      case 5: return brandAttitude !== '';
      default: return false;
    }
  };

  const toggleChip = (
    value: string,
    selected: string[],
    setter: (v: string[]) => void,
    maxCount?: number,
  ) => {
    if (selected.includes(value)) {
      setter(selected.filter((v) => v !== value));
    } else if (!maxCount || selected.length < maxCount) {
      setter([...selected, value]);
    }
  };

  const handleNext = async () => {
    if (step === 0 && selectedLanguage !== language) {
      // Language changed — this will restart the app
      await switchLanguage(selectedLanguage);
      return;
    }
    if (step < TOTAL_STEPS - 1) {
      setStep(step + 1);
    } else {
      // Complete onboarding
      setSaving(true);
      try {
        await savePreferences({
          priorities,
          budget: budget as any,
          lifestyle,
          brand_attitude: brandAttitude as any,
        });
        if (onComplete) onComplete();
      } catch (err: any) {
        // Silently fail — preferences can be set later
        if (onComplete) onComplete();
      } finally {
        setSaving(false);
      }
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.language.title')}</Text>
            <View style={styles.optionList}>
              {(['en', 'ar'] as const).map((lang) => (
                <TouchableOpacity
                  key={lang}
                  style={[styles.radioCard, selectedLanguage === lang && styles.radioCardActive]}
                  onPress={() => setSelectedLanguage(lang)}
                >
                  <Text style={[styles.radioLabel, selectedLanguage === lang && styles.radioLabelActive]}>
                    {lang === 'en' ? 'English' : 'العربية'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 1:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.region.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.region.subtitle')}</Text>
            <View style={styles.optionList}>
              {REGIONS.map((r) => (
                <TouchableOpacity
                  key={r.value}
                  style={[styles.radioCard, region === r.value && styles.radioCardActive]}
                  onPress={() => setRegion(r.value)}
                >
                  <Text style={styles.radioFlag}>{r.flag}</Text>
                  <Text style={[styles.radioLabel, region === r.value && styles.radioLabelActive]}>
                    {t(`onboarding.region.${r.value}`)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 2:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.priorities.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.priorities.subtitle')}</Text>
            <View style={styles.chipGrid}>
              {PRIORITY_OPTIONS.map((opt) => (
                <Chip
                  key={opt}
                  label={t(`onboarding.priorities.${opt}`)}
                  selected={priorities.includes(opt)}
                  onPress={() => toggleChip(opt, priorities, setPriorities, 3)}
                />
              ))}
            </View>
          </View>
        );
      case 3:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.budget.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.budget.subtitle')}</Text>
            <View style={styles.optionList}>
              {BUDGET_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[styles.radioCard, budget === opt && styles.radioCardActive]}
                  onPress={() => setBudget(opt)}
                >
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, budget === opt && styles.radioLabelActive]}>
                      {t(`onboarding.budget.${opt}`)}
                    </Text>
                    <Text style={styles.radioDesc}>{t(`onboarding.budget.${opt}_desc`)}</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      case 4:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.lifestyle.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.lifestyle.subtitle')}</Text>
            <View style={styles.chipGrid}>
              {LIFESTYLE_OPTIONS.map((opt) => (
                <Chip
                  key={opt}
                  label={t(`onboarding.lifestyle.${opt}`)}
                  selected={lifestyle.includes(opt)}
                  onPress={() => toggleChip(opt, lifestyle, setLifestyle)}
                />
              ))}
            </View>
          </View>
        );
      case 5:
        return (
          <View>
            <Text style={styles.title}>{t('onboarding.brand.title')}</Text>
            <Text style={styles.subtitle}>{t('onboarding.brand.subtitle')}</Text>
            <View style={styles.optionList}>
              {BRAND_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt}
                  style={[styles.radioCard, brandAttitude === opt && styles.radioCardActive]}
                  onPress={() => setBrandAttitude(opt)}
                >
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, brandAttitude === opt && styles.radioLabelActive]}>
                      {t(`onboarding.brand.${opt}`)}
                    </Text>
                    <Text style={styles.radioDesc}>{t(`onboarding.brand.${opt}_desc`)}</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        );
      default:
        return null;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <ProgressBar progress={progress} />
      </View>
      {isInferredEdit ? (
        <View style={styles.inferredBanner}>
          <Text style={styles.inferredBannerText}>
            {t('profile.styleProfile.banner')}
          </Text>
        </View>
      ) : null}
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {renderStep()}
      </ScrollView>
      <View style={styles.footer}>
        {step > 0 ? (
          <TouchableOpacity onPress={handleBack}>
            <Text style={styles.backText}>{t('onboarding.back')}</Text>
          </TouchableOpacity>
        ) : (
          <View />
        )}
        <Button
          title={step === TOTAL_STEPS - 1 ? t('onboarding.complete') : t('onboarding.next')}
          onPress={handleNext}
          disabled={!isStepValid()}
          loading={saving}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.base },
  inferredBanner: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: radii.card,
    backgroundColor: colors.accentLight,
    borderWidth: 1,
    borderColor: colors.accent,
  },
  inferredBannerText: {
    ...typography.caption,
    color: colors.text.primary,
  },
  content: { flex: 1 },
  contentInner: { padding: spacing.lg, paddingTop: spacing['2xl'] },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.base,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
  },
  title: { ...typography.display, color: colors.text.primary, marginBottom: spacing.sm },
  subtitle: { ...typography.body, color: colors.text.secondary, marginBottom: spacing.xl },
  chipGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  optionList: { gap: spacing.md },
  radioCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  radioCardActive: { borderColor: colors.accent, backgroundColor: colors.accentLight },
  radioFlag: { fontSize: 24, marginEnd: spacing.md },
  radioContent: { flex: 1 },
  radioLabel: { ...typography.body, fontWeight: '600', color: colors.text.primary },
  radioLabelActive: { color: colors.accent },
  radioDesc: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
  backText: { ...typography.body, color: colors.accent, fontWeight: '500' },
});
