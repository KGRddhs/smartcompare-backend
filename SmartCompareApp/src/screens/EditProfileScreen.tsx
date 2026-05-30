// SmartCompareApp/src/screens/EditProfileScreen.tsx
//
// Bundle E S3 REWRITE per docs/claude-design-handoff/ui_kits/mobile/
// EditProfileScreen.jsx (1-233). Element order:
//   1. Header              — back chevron + centered "Edit Profile" + spacer
//                            [JSX:23-43]
//   2. AvatarBlock         — 96x96 circle bg.secondary + 36/700 initial
//                            + "Photo upload coming soon" caption [JSX:45-63]
//   3. Eyebrow "Account"   — [JSX:65-74]
//   4. FormCard            — 2 fields: Display name + Email (or Apple ID mask)
//                            [JSX:76-87, 173-185]
//   5. NavRow Edit style profile (Star icon-circle + label + sub + chevron)
//                            [JSX:122-148, 187-191]
//   6. Eyebrow "Account actions" [JSX:193]
//   7. Delete card (bordered, single NavRow with Trash icon, destructive)
//                            [JSX:194-206]
//   8. Sticky Save CTA (bottom-pinned outside ScrollView) [JSX:210-228]
//
// Element-order checklist: docs/plans/_s3-a1-element-order.md
//
// REWRITES from prior state:
//   - Save CTA moved OUT of ScrollView into a sibling sticky-bottom slot
//     (top hairline border + bg.primary background) so it never scrolls
//     out of reach on long edit screens.
//   - "Danger zone" eyebrow renamed to "Account actions" per JSX:193.
//   - Delete row wrapped in a bordered card (deleteCard style) and gets
//     a Trash2 icon-circle on the left.
//   - Edit-style-profile linkRow gains a Star icon-circle + the
//     "Update priorities, budget, and brand stance" sub-line.
//
// Preserved (S2 6b2be83): Apple Hide-My-Email relay mask — when the
// user's email ends with @privaterelay.appleid.com, the row swaps to
// "Apple ID" label + "Email kept private by Apple" caption.

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
import { ChevronLeft, ChevronRight, Star, Trash2 } from 'lucide-react-native';
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
  // that happened elsewhere.
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
    // Bundle E F-S1.5c: "Edit style profile" maps to EditPreferencesFlow
    // (priorities + budget + brand_attitude), not the full 17-step
    // Onboarding re-run.
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

  // S2 6b2be83 preserved: Apple Hide-My-Email relay mask.
  const isAppleRelay =
    !!user?.email && user.email.toLowerCase().endsWith('@privaterelay.appleid.com');

  return (
    <SafeAreaView style={styles.container}>
      {/* 1. Header */}
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
        {/* 2. AvatarBlock */}
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{avatarLetter}</Text>
          </View>
          <Text style={styles.avatarHint}>{t('editProfile.avatar.placeholder')}</Text>
        </View>

        {/* 3. Eyebrow "Account" */}
        <Text style={styles.sectionLabel}>{t('editProfile.section.account')}</Text>

        {/* 4. FormCard — display name + email (or Apple ID mask) */}
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
          {isAppleRelay ? (
            <>
              <Text style={styles.fieldLabel}>
                {t('editprofile.email.appleLabel', { defaultValue: 'Apple ID' })}
              </Text>
              <Text style={styles.readonly}>
                {t('editprofile.email.applePrivate', {
                  defaultValue: 'Email kept private by Apple',
                })}
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.fieldLabel}>{t('auth.email')}</Text>
              <Text style={styles.readonly}>{user?.email ?? '—'}</Text>
            </>
          )}
        </View>

        {/* 5. NavRow "Edit style profile" — Star icon-circle + label + sub
            + chevron per JSX:122-148, 187-191. */}
        <TouchableOpacity
          testID="edit-style-profile-row"
          onPress={handleEditStyleProfile}
          style={styles.navRow}
          accessibilityRole="button"
        >
          <View style={styles.navRowIconCircle}>
            <Star size={18} color={colors.text.primary} />
          </View>
          <View style={styles.navRowBody}>
            <Text style={styles.navRowLabel}>{t('editProfile.editStyleProfile')}</Text>
            <Text style={styles.navRowSub}>
              {t('editProfile.editStyleProfile.sub', {
                defaultValue: 'Update priorities, budget, and brand stance',
              })}
            </Text>
          </View>
          <ChevronRight size={18} color={colors.text.placeholder} />
        </TouchableOpacity>

        {errorKey ? <Text style={styles.errorText}>{t(errorKey)}</Text> : null}

        {/* 6. Eyebrow "Account actions" (renamed from "Danger zone") */}
        <Text style={[styles.sectionLabel, styles.accountActionsLabel]}>
          {t('editProfile.section.accountActions', { defaultValue: 'Account actions' })}
        </Text>

        {/* 7. Delete card — bordered card containing one destructive NavRow
            with Trash icon-circle. JSX:194-206. */}
        <View style={styles.deleteCard}>
          <TouchableOpacity
            testID="edit-delete-account-row"
            onPress={handleDeleteAccount}
            disabled={deleting}
            style={styles.deleteRow}
            accessibilityRole="button"
          >
            <View style={styles.deleteIconCircle}>
              <Trash2 size={18} color={colors.destructive} />
            </View>
            {deleting ? (
              <ActivityIndicator color={colors.destructive} />
            ) : (
              <Text style={styles.deleteLabel}>{t('editProfile.deleteAccount')}</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* 8. Sticky Save CTA — pinned to bottom OUTSIDE ScrollView per
          JSX:210-228. Top hairline border separates from scroll content. */}
      <View style={styles.saveStickyHost}>
        <TouchableOpacity
          testID="edit-save-cta"
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
  // S3 — NavRow with icon-circle + label + sub + chevron per JSX:122-148.
  navRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    marginBottom: spacing.lg,
    minHeight: 56,
  },
  navRowIconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navRowBody: {
    flex: 1,
    minWidth: 0,
  },
  navRowLabel: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 15 * 1.3,
    color: colors.text.primary,
  },
  navRowSub: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
    marginTop: 2,
  },
  errorText: {
    ...typography.caption,
    color: colors.destructive,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  // S3 — Account actions eyebrow above the Delete card. Extra top margin
  // separates it from the form above.
  accountActionsLabel: {
    marginTop: spacing.xl,
  },
  // S3 — Delete card (bordered, hosts the destructive NavRow). JSX:194-206.
  deleteCard: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border.light,
    overflow: 'hidden',
    marginBottom: spacing.lg,
  },
  deleteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    minHeight: 56,
  },
  deleteIconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteLabel: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 15 * 1.3,
    color: colors.destructive,
  },
  // S3 — Sticky bottom Save CTA host. Top hairline border + bg.primary
  // background. Pinned to bottom OUTSIDE the ScrollView. JSX:210-228.
  saveStickyHost: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
    backgroundColor: colors.bg.primary,
  },
  saveBtn: {
    backgroundColor: colors.cta.primary,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    height: 52,
  },
  saveBtnDisabled: {
    opacity: 0.4,
  },
  saveBtnText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
});
