/**
 * Qaren - Reset Password Screen (W3-6)
 *
 * Reached from the qaren://reset-password recovery link. The linking
 * override parks the link's access token in a memory-only slot; this screen
 * consumes it ONCE on mount, never renders or logs it, and hands it to the
 * backend completion route with the new password. An empty slot (expired or
 * spent link, cold remount) or a backend RECOVERY_TOKEN_INVALID renders the
 * "request a new link" state; an UPSTREAM_UNAVAILABLE blip keeps the form with
 * a retry line (the link still works); every other failure renders
 * common.error.
 *
 * Both CTAs use navigation.reset, not navigate: on the cold-start deep-link
 * path the Auth stack holds only [ResetPassword], so a push would leave Back
 * landing on a screen whose slot is already spent.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { usePreventScreenCapture } from 'expo-screen-capture';
import { completePasswordRecovery } from '../services/authService';
import { parseApiError } from '../services/api';
import { consumePendingRecovery } from '../services/passwordRecoveryLink';
import { AuthStackParamList } from '../types';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { Button } from '../components/Button';

type ResetPasswordScreenProps = {
  navigation: NativeStackNavigationProp<AuthStackParamList, 'ResetPassword'>;
};

// Same rule as RegisterScreen and the backend's _validate_password_strength.
function isWeakPassword(password: string): boolean {
  return (
    password.length < 10 ||
    !/[A-Z]/.test(password) ||
    !/[a-z]/.test(password) ||
    !/[0-9]/.test(password)
  );
}

export default function ResetPasswordScreen({ navigation }: ResetPasswordScreenProps) {
  const { t } = useTranslation();
  usePreventScreenCapture();
  const [recovery] = useState(() => consumePendingRecovery());
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [linkInvalid, setLinkInvalid] = useState(false);

  const handleSubmit = async () => {
    if (!recovery) {
      return;
    }
    if (isWeakPassword(password)) {
      setError(t('auth.passwordRequirements'));
      return;
    }
    if (password !== confirm) {
      setError(t('auth.passwordsDoNotMatch'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await completePasswordRecovery(recovery.accessToken, password);
      setDone(true);
    } catch (err: any) {
      // Render by CODE, never by `.message`: the real parseApiError returns
      // an EMPTY message for a codeless transport failure (offline, axios
      // deadline, bare 503), and the backend's own sentence is English-only.
      const code = parseApiError(err).code;
      if (code === 'RECOVERY_TOKEN_INVALID') {
        // The token is dead — the form can never succeed; offer a new link.
        setLinkInvalid(true);
      } else if (code === 'UPSTREAM_UNAVAILABLE') {
        // A Supabase blip, not a verdict on the link: it still works, so
        // keep the form and say a tap will do it.
        setError(t('auth.resetConnectionRetry'));
      } else {
        setError(t('common.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  if (!recovery || linkInvalid) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{t('auth.resetLinkExpired')}</Text>
            <Text style={styles.cardText}>{t('auth.resetLinkExpiredMessage')}</Text>
            <Button
              title={t('auth.requestNewLink')}
              testID="reset-password-request-new-link"
              onPress={() =>
                navigation.reset({
                  index: 1,
                  routes: [{ name: 'Login' }, { name: 'ForgotPassword' }],
                })
              }
            />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  if (done) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{t('auth.passwordUpdated')}</Text>
            <Text style={styles.cardText}>{t('auth.passwordUpdatedMessage')}</Text>
            <Button
              title={t('auth.signIn')}
              testID="reset-password-signin"
              onPress={() => navigation.reset({ index: 0, routes: [{ name: 'Login' }] })}
            />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <View style={styles.content}>
          <View style={styles.form}>
            <Text style={styles.title}>{t('auth.setNewPassword')}</Text>

            {error ? (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            <View style={styles.inputContainer}>
              <Text style={styles.label}>{t('auth.newPassword')}</Text>
              <TextInput
                style={styles.input}
                placeholder={t('auth.newPassword')}
                placeholderTextColor={colors.text.placeholder}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                editable={!loading}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>{t('auth.confirmPassword')}</Text>
              <TextInput
                style={styles.input}
                placeholder={t('auth.confirmPassword')}
                placeholderTextColor={colors.text.placeholder}
                value={confirm}
                onChangeText={setConfirm}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                editable={!loading}
              />
            </View>

            <Button
              title={t('auth.setNewPassword')}
              testID="reset-password-submit"
              onPress={handleSubmit}
              disabled={loading}
              loading={loading}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.secondary,
  },
  keyboardView: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: spacing.xl,
    justifyContent: 'center',
  },
  form: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    padding: spacing.xl,
    ...shadows.card,
  },
  title: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: spacing.xl,
    textAlign: 'center',
  },
  errorContainer: {
    backgroundColor: '#FEF2F2',
    borderRadius: spacing.sm,
    padding: spacing.md,
    marginBottom: spacing.base,
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    textAlign: 'center',
  },
  inputContainer: {
    marginBottom: spacing.lg,
  },
  label: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    height: 48,
    ...typography.body,
    color: colors.text.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  card: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    padding: spacing['2xl'],
    alignItems: 'center',
    ...shadows.card,
  },
  cardTitle: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  cardText: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: typography.caption.lineHeight * 1.3,
    marginBottom: spacing.xl,
  },
});
