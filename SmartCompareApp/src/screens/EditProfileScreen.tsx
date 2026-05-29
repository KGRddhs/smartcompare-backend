// SmartCompareApp/src/screens/EditProfileScreen.tsx
//
// Promotes the cramped inline name edit on Profile to a real screen
// consolidating account edits (Bundle A §3). Avatar upload is stubbed
// pending S3 + image picker work in a later bundle.

import React, { useCallback, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, ChevronRight } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import api, { parseApiError, updateProfile } from '../services/api';
import {
  getSavedUser,
  clearSession,
  updateSavedUserDisplayName,
  type User,
} from '../services/authService';
import type { RootStackParamList } from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'EditProfile'> & {
  onAccountDeleted?: () => void;
};

export default function EditProfileScreen({ navigation, onAccountDeleted }: Props) {
  const { t } = useTranslation();
  const [user, setUser] = useState<User | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [initialName, setInitialName] = useState('');
  const [saving, setSaving] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // F-S1.5k: refetch on focus so the displayed name reflects any update
  // that happened elsewhere (e.g. a future flow that updates the cached
  // user via updateSavedUserDisplayName). The initial mount also triggers
  // this — useFocusEffect fires on mount AND every subsequent focus.
  useFocusEffect(
    useCallback(() => {
      (async () => {
        const u = await getSavedUser();
        setUser(u);
        const n = u?.display_name ?? '';
        setDisplayName(n);
        setInitialName(n);
      })();
    }, []),
  );

  const dirty = displayName.trim() !== initialName.trim();
  const canSave = dirty && displayName.trim().length >= 2 && !saving;

  const handleSave = async () => {
    const trimmed = displayName.trim();
    if (trimmed.length < 2) {
      setErrorKey('editProfile.name.tooShort');
      return;
    }
    setSaving(true);
    setErrorKey(null);
    try {
      const result = await updateProfile(trimmed);
      if (result.success) {
        setInitialName(trimmed);
        // F-S1.5k: write through to the cached user record so
        // ProfileScreen's focus-refetch picks up the new name on the
        // very next render. Without this the user only sees the new
        // name after a full session refresh.
        await updateSavedUserDisplayName(trimmed);
        navigation.goBack();
      } else {
        setErrorKey('editProfile.error.saveFailed');
      }
    } catch (err) {
      setErrorKey('editProfile.error.saveFailed');
    } finally {
      setSaving(false);
    }
  };

  const handleEditStyleProfile = () => {
    // Bundle E F-S1.5c: JSX EditProfileScreen.jsx:189-190 "Edit style profile"
    // subtitle "Update priorities, budget, and brand stance" maps to the
    // lighter EditPreferencesFlow (priorities + budget + brand_attitude),
    // not the full 17-step Onboarding re-run. Both this gateway AND Profile's
    // PrioritiesInline "Tune" CTA converge on EditPreferences for parity.
    navigation.navigate('EditPreferences');
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      t('editProfile.deleteAccount'),
      t('profile.deleteConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('editProfile.deleteAccount'),
          style: 'destructive',
          onPress: async () => {
            setDeleting(true);
            try {
              await api.delete('/api/v1/auth/account');
              await clearSession();
              onAccountDeleted?.();
            } catch (err) {
              setDeleting(false);
              Alert.alert(t('editProfile.error.deleteTitle'), parseApiError(err).message);
            }
          },
        },
      ],
    );
  };

  const avatarLetter = (user?.display_name || user?.email || '?')[0]?.toUpperCase() ?? '?';

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          style={styles.headerBtn}
        >
          <ChevronLeft size={24} color={colors.text.primary} />
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>{t('editProfile.title')}</Text>
        <View style={styles.headerBtn} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Avatar — stubbed; photo upload deferred to a later bundle. */}
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{avatarLetter}</Text>
          </View>
          <Text style={styles.avatarHint}>{t('editProfile.avatar.placeholder')}</Text>
        </View>

        {/* Account section */}
        <Text style={styles.sectionLabel}>{t('editProfile.section.account')}</Text>
        <View style={styles.card}>
          <Text style={styles.fieldLabel}>{t('profile.name')}</Text>
          <TextInput
            style={styles.input}
            value={displayName}
            onChangeText={(v) => {
              setDisplayName(v);
              setErrorKey(null);
            }}
            placeholder={t('profile.name')}
            placeholderTextColor={colors.text.placeholder}
            maxLength={100}
            editable={!saving}
          />
          <Text style={styles.fieldLabel}>{t('auth.email')}</Text>
          <Text style={styles.readonly}>{user?.email ?? '—'}</Text>
        </View>

        {/* Style profile entry */}
        <TouchableOpacity
          onPress={handleEditStyleProfile}
          style={styles.linkRow}
          accessibilityRole="button"
        >
          <Text style={styles.linkLabel}>{t('editProfile.editStyleProfile')}</Text>
          <ChevronRight size={18} color={colors.text.secondary} />
        </TouchableOpacity>

        {errorKey ? <Text style={styles.errorText}>{t(errorKey)}</Text> : null}

        <TouchableOpacity
          onPress={handleSave}
          disabled={!canSave}
          style={[styles.saveBtn, !canSave && styles.saveBtnDisabled]}
          accessibilityRole="button"
          accessibilityState={{ disabled: !canSave }}
        >
          {saving ? (
            <ActivityIndicator color={colors.cta.onPrimary} />
          ) : (
            <Text style={styles.saveBtnText}>{t('common.save')}</Text>
          )}
        </TouchableOpacity>

        {/* Account actions / Danger */}
        <Text style={[styles.sectionLabel, styles.dangerLabel]}>
          {t('editProfile.dangerZone')}
        </Text>
        <TouchableOpacity
          onPress={handleDeleteAccount}
          disabled={deleting}
          style={styles.dangerRow}
          accessibilityRole="button"
        >
          {deleting ? (
            <ActivityIndicator color={colors.destructive} />
          ) : (
            <Text style={styles.dangerLabelText}>{t('editProfile.deleteAccount')}</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
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
  // Bundle D Claude-Design (option small, Task 2.F.2 screen 5): header
  // back-button bumped 32→36 to match EditProfileScreen.jsx + the same
  // pattern shipped on ResultsScreen.tsx:1385 (95691c2). Transparent
  // background per JSX (back button has no fill on EditProfile — modal-
  // style, quieter than the data screens' bg.secondary circular treatment).
  headerBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  title: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
    flex: 1,
    textAlign: 'center',
  },
  scroll: {
    padding: spacing.lg,
  },
  avatarSection: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  // Bundle D Claude-Design (option small, Task 2.F.2 screen 5):
  // avatar bumped 88→96 to match EditProfileScreen.jsx AvatarBlock
  // (width 96, height 96, borderRadius 48). Same bg.secondary fill +
  // hero typography. Larger circle leans into the avatar as the visual
  // hero of the edit surface per the design intent.
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  avatarText: {
    ...typography.hero,
    color: colors.text.primary,
  },
  avatarHint: {
    ...typography.small,
    color: colors.text.placeholder,
  },
  sectionLabel: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  fieldLabel: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
    marginTop: spacing.xs,
  },
  input: {
    backgroundColor: colors.bg.primary,
    padding: spacing.md,
    borderRadius: radii.input,
    marginBottom: spacing.sm,
    ...typography.body,
    color: colors.text.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  readonly: {
    ...typography.body,
    color: colors.text.secondary,
    padding: spacing.md,
  },
  linkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.md,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    marginBottom: spacing.lg,
  },
  linkLabel: {
    ...typography.body,
    color: colors.text.primary,
  },
  saveBtn: {
    backgroundColor: colors.cta.primary,
    padding: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  saveBtnDisabled: {
    opacity: 0.4,
  },
  saveBtnText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  dangerLabel: {
    marginTop: spacing.xl,
  },
  dangerRow: {
    padding: spacing.md,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  dangerLabelText: {
    ...typography.bodyEmphasis,
    color: colors.destructive,
  },
});
