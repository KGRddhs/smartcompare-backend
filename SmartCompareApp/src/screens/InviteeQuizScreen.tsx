/**
 * InviteeQuizScreen (F3.3 — placeholder)
 *
 * STUB: full 4-question quiz implementation lands in the next commit.
 * Mounted now so the navigation type compiles and ReferralLandingScreen
 * can `navigate('InviteeQuiz')` without runtime crash. Renders a minimal
 * "coming soon" view that respects the back gesture.
 */

import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'InviteeQuiz'>;

export default function InviteeQuizScreen({ navigation }: Props) {
  const { t } = useTranslation();
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.headerButton}
          accessibilityLabel={t('common.back', { defaultValue: 'Back' })}
        >
          <ArrowLeft size={20} color={colors.text.primary} />
        </TouchableOpacity>
      </View>
      <View style={styles.body}>
        <Text style={styles.title}>{t('referrals.quiz.placeholder')}</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.sm,
  },
  headerButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
});
