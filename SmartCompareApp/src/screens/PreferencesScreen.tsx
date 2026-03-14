/**
 * PreferencesScreen - 4-card mandatory preference collection
 * Used for onboarding (first login) and editing (from AccountScreen)
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList, UserPreferences } from '../types';
import { getPreferences, savePreferences } from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Preferences'>;
  route: RouteProp<RootStackParamList, 'Preferences'>;
  onComplete?: () => void;
  onLogout?: () => void;
};

const TOTAL_STEPS = 4;

// Card 1: Priority chips (pick 1-3)
const PRIORITY_OPTIONS = [
  { value: 'price', label: 'Price' },
  { value: 'quality', label: 'Quality' },
  { value: 'brand_reputation', label: 'Brand Reputation' },
  { value: 'durability', label: 'Durability' },
  { value: 'latest_features', label: 'Latest Features' },
  { value: 'ease_of_use', label: 'Ease of Use' },
  { value: 'eco_friendly', label: 'Eco-Friendly' },
  { value: 'health_safety', label: 'Health & Safety' },
];

// Card 2: Budget radio (single select)
const BUDGET_OPTIONS = [
  { value: 'budget', label: 'Budget', description: 'I look for the best deals' },
  { value: 'mid', label: 'Balanced', description: 'I balance price and quality' },
  { value: 'premium', label: 'Premium', description: 'I go for the best, price is secondary' },
];

// Card 3: Lifestyle chips (pick 1+)
const LIFESTYLE_OPTIONS = [
  { value: 'gamer', label: 'Gamer' },
  { value: 'photographer', label: 'Photographer' },
  { value: 'fitness_enthusiast', label: 'Fitness' },
  { value: 'vegan', label: 'Vegan' },
  { value: 'sensitive_skin', label: 'Sensitive Skin' },
  { value: 'parent', label: 'Parent' },
  { value: 'student', label: 'Student' },
  { value: 'professional', label: 'Professional' },
  { value: 'outdoor_adventurer', label: 'Outdoor' },
  { value: 'minimalist', label: 'Minimalist' },
  { value: 'tech_enthusiast', label: 'Tech Enthusiast' },
];

// Card 4: Brand attitude radio (single select)
const BRAND_OPTIONS = [
  { value: 'brand_loyal', label: 'Brand Loyal', description: 'I stick with brands I trust' },
  { value: 'function_first', label: 'Function First', description: 'Whatever works best, brand doesn\'t matter' },
  { value: 'best_of_both', label: 'Best of Both', description: 'Good brands preferred, but function wins if clear' },
];

export default function PreferencesScreen({ navigation, route, onComplete, onLogout }: Props) {
  const mode = route.params?.mode || 'onboarding';
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(mode === 'edit');
  const [saving, setSaving] = useState(false);

  // Preference state
  const [priorities, setPriorities] = useState<string[]>([]);
  const [budget, setBudget] = useState<string>('');
  const [lifestyle, setLifestyle] = useState<string[]>([]);
  const [brandAttitude, setBrandAttitude] = useState<string>('');

  useEffect(() => {
    if (mode === 'edit') {
      loadExisting();
    }
  }, [mode]);

  const loadExisting = async () => {
    try {
      const prefs = await getPreferences();
      if (prefs) {
        setPriorities(prefs.priorities || []);
        setBudget(prefs.budget || '');
        setLifestyle(prefs.lifestyle || []);
        setBrandAttitude(prefs.brand_attitude || '');
      }
    } catch (err) {
      // Start fresh if load fails
    } finally {
      setLoading(false);
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

  const isStepValid = (): boolean => {
    switch (step) {
      case 0: return priorities.length >= 1 && priorities.length <= 3;
      case 1: return budget !== '';
      case 2: return lifestyle.length >= 1;
      case 3: return brandAttitude !== '';
      default: return false;
    }
  };

  const handleComplete = async () => {
    const prefs: UserPreferences = {
      priorities,
      budget: budget as UserPreferences['budget'],
      lifestyle,
      brand_attitude: brandAttitude as UserPreferences['brand_attitude'],
    };

    setSaving(true);
    try {
      await savePreferences(prefs);
      if (onComplete) {
        onComplete();
      } else if (navigation.canGoBack()) {
        navigation.goBack();
      }
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleNext = () => {
    if (step < TOTAL_STEPS - 1) {
      setStep(step + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
        </View>
      </SafeAreaView>
    );
  }

  // Progress bar
  const progress = (step + 1) / TOTAL_STEPS;

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={styles.headerTitle}>
            {mode === 'onboarding' ? 'Set Up Your Preferences' : 'Edit Preferences'}
          </Text>
          {onLogout && (
            <TouchableOpacity onPress={onLogout}>
              <Text style={{ color: '#FF3B30', fontSize: 14 }}>Logout</Text>
            </TouchableOpacity>
          )}
        </View>
        <Text style={styles.headerSubtitle}>
          Step {step + 1} of {TOTAL_STEPS}
        </Text>
      </View>

      {/* Progress bar */}
      <View style={styles.progressBarContainer}>
        <View style={[styles.progressBarFill, { width: `${progress * 100}%` }]} />
      </View>

      {/* Card content */}
      <ScrollView
        style={styles.cardContainer}
        contentContainerStyle={styles.cardContent}
      >
        {step === 0 && (
          <View>
            <Text style={styles.cardTitle}>What matters most to you?</Text>
            <Text style={styles.cardDescription}>Pick 1 to 3 priorities</Text>
            <View style={styles.chipGrid}>
              {PRIORITY_OPTIONS.map((opt) => {
                const isSelected = priorities.includes(opt.value);
                return (
                  <TouchableOpacity
                    key={opt.value}
                    testID={`priority-chip-${opt.value}`}
                    style={[styles.chip, isSelected && styles.chipActive]}
                    onPress={() => toggleChip(opt.value, priorities, setPriorities, 3)}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.chipText, isSelected && styles.chipTextActive]}>
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        )}

        {step === 1 && (
          <View>
            <Text style={styles.cardTitle}>How do you usually spend?</Text>
            <Text style={styles.cardDescription}>Select your general budget level</Text>
            {BUDGET_OPTIONS.map((opt) => {
              const isSelected = budget === opt.value;
              return (
                <TouchableOpacity
                  key={opt.value}
                  testID={`budget-radio-${opt.value}`}
                  style={[styles.radioCard, isSelected && styles.radioCardActive]}
                  onPress={() => setBudget(opt.value)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.radioCircle, isSelected && styles.radioCircleActive]}>
                    {isSelected && <View style={styles.radioCircleFill} />}
                  </View>
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, isSelected && styles.radioLabelActive]}>
                      {opt.label}
                    </Text>
                    <Text style={styles.radioDescription}>{opt.description}</Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {step === 2 && (
          <View>
            <Text style={styles.cardTitle}>What describes you?</Text>
            <Text style={styles.cardDescription}>Pick any that apply</Text>
            <View style={styles.chipGrid}>
              {LIFESTYLE_OPTIONS.map((opt) => {
                const isSelected = lifestyle.includes(opt.value);
                return (
                  <TouchableOpacity
                    key={opt.value}
                    testID={`lifestyle-chip-${opt.value}`}
                    style={[styles.chip, isSelected && styles.chipActive]}
                    onPress={() => toggleChip(opt.value, lifestyle, setLifestyle)}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.chipText, isSelected && styles.chipTextActive]}>
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        )}

        {step === 3 && (
          <View>
            <Text style={styles.cardTitle}>Your approach to brands?</Text>
            <Text style={styles.cardDescription}>How do you choose products?</Text>
            {BRAND_OPTIONS.map((opt) => {
              const isSelected = brandAttitude === opt.value;
              return (
                <TouchableOpacity
                  key={opt.value}
                  testID={`brand-radio-${opt.value}`}
                  style={[styles.radioCard, isSelected && styles.radioCardActive]}
                  onPress={() => setBrandAttitude(opt.value)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.radioCircle, isSelected && styles.radioCircleActive]}>
                    {isSelected && <View style={styles.radioCircleFill} />}
                  </View>
                  <View style={styles.radioContent}>
                    <Text style={[styles.radioLabel, isSelected && styles.radioLabelActive]}>
                      {opt.label}
                    </Text>
                    <Text style={styles.radioDescription}>{opt.description}</Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* Navigation buttons */}
      <View style={styles.buttonRow}>
        {step > 0 ? (
          <TouchableOpacity style={styles.backButton} onPress={handleBack}>
            <Text style={styles.backButtonText}>Back</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.backButton} />
        )}

        <TouchableOpacity
          style={[styles.nextButton, !isStepValid() && styles.nextButtonDisabled]}
          onPress={handleNext}
          disabled={!isStepValid() || saving}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#FFF" />
          ) : (
            <Text style={styles.nextButtonText}>
              {step === TOTAL_STEPS - 1 ? 'Complete' : 'Next'}
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
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 4,
  },
  progressBarContainer: {
    height: 4,
    backgroundColor: '#E0E0E0',
    marginHorizontal: 20,
    borderRadius: 2,
    marginBottom: 8,
  },
  progressBarFill: {
    height: 4,
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  cardContainer: {
    flex: 1,
  },
  cardContent: {
    padding: 20,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
    marginBottom: 6,
  },
  cardDescription: {
    fontSize: 14,
    color: '#888',
    marginBottom: 20,
  },
  chipGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  chip: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  chipActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  chipText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  chipTextActive: {
    color: '#FFF',
    fontWeight: '600',
  },
  radioCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  radioCardActive: {
    borderColor: '#007AFF',
    backgroundColor: '#F0F7FF',
  },
  radioCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#CCC',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  radioCircleActive: {
    borderColor: '#007AFF',
  },
  radioCircleFill: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#007AFF',
  },
  radioContent: {
    flex: 1,
  },
  radioLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  radioLabelActive: {
    color: '#007AFF',
  },
  radioDescription: {
    fontSize: 13,
    color: '#888',
    marginTop: 2,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    backgroundColor: '#FFF',
  },
  backButton: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    minWidth: 80,
  },
  backButtonText: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '500',
  },
  nextButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 10,
    minWidth: 100,
    alignItems: 'center',
  },
  nextButtonDisabled: {
    backgroundColor: '#B0B0B0',
  },
  nextButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
