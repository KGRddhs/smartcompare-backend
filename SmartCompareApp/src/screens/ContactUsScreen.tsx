// SmartCompareApp/src/screens/ContactUsScreen.tsx
//
// Wires the previously dead `() => {}` Contact Us handler in Profile.
// POSTs to /api/v1/feedback with the category encoded in change_suggestion
// (e.g. "[Bug] Title\n\nBody") so operators can grep tickets without
// backend schema changes. See Bundle A §4.2.

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  Linking,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Haptics from 'expo-haptics';
import { colors, spacing, radii, typography } from '../theme';
import api from '../services/api';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'ContactUs'>;
type Category = 'bug' | 'suggestion' | 'business' | 'other';

const CATEGORIES: Category[] = ['bug', 'suggestion', 'business', 'other'];

// M18 CD-uncovered-02 / MB-flows-09: the change_suggestion prefix is the
// operators' triage key (`change_suggestion LIKE '[Bug]%'`), so it must be a
// STABLE ENGLISH tag independent of the device locale. t() is for the
// on-screen chip labels only — an Arabic reporter previously produced
// a localized Arabic prefix, invisible to the documented grep.
const CATEGORY_TAGS: Record<Category, string> = {
  bug: 'Bug',
  suggestion: 'Suggestion',
  business: 'Business',
  other: 'Other',
};

const MIN_MESSAGE = 10;
const MAX_SUBJECT = 120;
// Backend FeedbackRequest.change_suggestion caps at 1000 chars.
// Composed payload = "[<tag>] <subject>\n\n<body>"; worst-case overhead is
// "[Suggestion] " (13) + MAX_SUBJECT (120) + "\n\n" (2) = 135, so the honest
// message cap is 1000 - 135 = 865. (Was 2000, which silently truncated.)
const BACKEND_MAX_CHANGE_SUGGESTION = 1000;
const MAX_MESSAGE =
  BACKEND_MAX_CHANGE_SUGGESTION - ('[Suggestion] '.length + MAX_SUBJECT + '\n\n'.length);
const RATE_LIMIT_MS = 30_000;

export default function ContactUsScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const [category, setCategory] = useState<Category>('bug');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [lastSubmitAt, setLastSubmitAt] = useState(0);

  const trimmedMessage = message.trim();
  const canSubmit = trimmedMessage.length >= MIN_MESSAGE && !submitting;

  const submit = async () => {
    if (Date.now() - lastSubmitAt < RATE_LIMIT_MS) {
      setErrorKey('contact.error.rateLimit');
      return;
    }
    setSubmitting(true);
    setErrorKey(null);
    try {
      // Category encoded inline so we don't need a new backend endpoint.
      // Operators query: `change_suggestion LIKE '[Bug]%'` etc. — the tag is
      // the stable English enum (CATEGORY_TAGS), NEVER the localized label,
      // so the grep works for every locale.
      const categoryTag = CATEGORY_TAGS[category];
      const composed = subject.trim()
        ? `[${categoryTag}] ${subject.trim()}\n\n${trimmedMessage}`
        : `[${categoryTag}] ${trimmedMessage}`;
      await api.post('/api/v1/feedback', {
        // A bug report is not positive feedback; other contact reasons are
        // neutral-to-positive. (`useful` is required by FeedbackRequest.)
        useful: category !== 'bug',
        mattered_most: [],
        // MAX_MESSAGE + MAX_SUBJECT are sized so this never exceeds the
        // backend cap; the slice is a defensive backstop, not a truncator.
        change_suggestion: composed.slice(0, BACKEND_MAX_CHANGE_SUGGESTION),
      });
      try { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); } catch {}
      setSuccess(true);
      setLastSubmitAt(Date.now());
    } catch {
      setErrorKey('contact.error.generic');
    } finally {
      setSubmitting(false);
    }
  };

  const Header = () => (
    <View style={styles.header}>
      <TouchableOpacity
        onPress={() => navigation.goBack()}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        style={styles.headerBtn}
      >
        <ChevronLeft size={24} color={colors.text.primary} />
      </TouchableOpacity>
      <Text style={styles.title} numberOfLines={1}>{t('contact.title')}</Text>
      <View style={styles.headerBtn} />
    </View>
  );

  if (success) {
    return (
      <SafeAreaView style={styles.container}>
        <Header />
        <View style={styles.center}>
          <Text style={styles.successTitle}>{t('contact.success.title')}</Text>
          <Text style={styles.successBody}>{t('contact.success.body')}</Text>
          <TouchableOpacity
            onPress={() => {
              setSuccess(false);
              setSubject('');
              setMessage('');
              setErrorKey(null);
            }}
            style={styles.btn}
            accessibilityRole="button"
          >
            <Text style={styles.btnText}>{t('contact.submit.again')}</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <Header />
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.label}>{t('contact.category.label')}</Text>
          <View style={styles.categoryRow}>
            {CATEGORIES.map((c) => {
              const active = category === c;
              return (
                <TouchableOpacity
                  key={c}
                  onPress={() => {
                    try { Haptics.selectionAsync(); } catch {}
                    setCategory(c);
                  }}
                  style={[styles.categoryChip, active && styles.categoryChipActive]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                >
                  <Text style={[styles.categoryText, active && styles.categoryTextActive]}>
                    {t(`contact.category.${c}`)}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <TextInput
            style={styles.input}
            placeholder={t('contact.subject.placeholder')}
            placeholderTextColor={colors.text.placeholder}
            value={subject}
            onChangeText={setSubject}
            maxLength={MAX_SUBJECT}
            editable={!submitting}
          />
          <TextInput
            style={[styles.input, styles.textarea]}
            placeholder={t('contact.message.placeholder')}
            placeholderTextColor={colors.text.placeholder}
            value={message}
            onChangeText={setMessage}
            multiline
            maxLength={MAX_MESSAGE}
            numberOfLines={6}
            editable={!submitting}
          />
          <Text style={styles.charCount}>{`${trimmedMessage.length} / ${MAX_MESSAGE}`}</Text>

          {errorKey ? <Text style={styles.errorText}>{t(errorKey)}</Text> : null}

          <TouchableOpacity
            onPress={submit}
            disabled={!canSubmit}
            style={[styles.btn, !canSubmit && styles.btnDisabled]}
            accessibilityRole="button"
            accessibilityState={{ disabled: !canSubmit }}
          >
            {submitting ? (
              <ActivityIndicator color={colors.cta.onPrimary} />
            ) : (
              <Text style={styles.btnText}>{t('contact.submit')}</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => Linking.openURL('mailto:support@qaren.app?subject=Qaren%20Support')}
            style={styles.emailFallback}
            accessibilityRole="link"
          >
            <Text style={styles.emailFallbackText}>{t('contact.email.fallback')}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  flex: { flex: 1 },
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
  title: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
    flex: 1,
    textAlign: 'center',
  },
  scroll: {
    padding: spacing.lg,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  label: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  categoryRow: {
    flexDirection: 'row',
    marginBottom: spacing.lg,
    flexWrap: 'wrap',
  },
  categoryChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.chip,
    marginEnd: spacing.sm,
    marginBottom: spacing.sm,
  },
  categoryChipActive: {
    backgroundColor: colors.cta.primary,
  },
  categoryText: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
  },
  categoryTextActive: {
    color: colors.cta.onPrimary,
  },
  input: {
    backgroundColor: colors.bg.secondary,
    padding: spacing.md,
    borderRadius: radii.input,
    marginBottom: spacing.md,
    ...typography.body,
    color: colors.text.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  textarea: {
    minHeight: 120,
    textAlignVertical: 'top',
  },
  charCount: {
    ...typography.small,
    color: colors.text.placeholder,
    textAlign: 'right',
    marginBottom: spacing.md,
  },
  btn: {
    backgroundColor: colors.cta.primary,
    padding: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginTop: spacing.sm,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
  emailFallback: {
    alignItems: 'center',
    padding: spacing.lg,
  },
  emailFallbackText: {
    ...typography.body,
    color: colors.accent,
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  successTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  successBody: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
});
