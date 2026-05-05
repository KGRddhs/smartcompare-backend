/**
 * Qaren - Profile Screen
 * Settings, language, account management in grouped cards
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  Modal,
  SafeAreaView,
  Platform,
  Switch,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import {
  User,
  Globe,
  MapPin,
  Sliders,
  Bell,
  FileText,
  ScrollText,
  MessageCircle,
  LogOut,
  Trash2,
  ChevronRight,
  Lock,
  Shield,
} from 'lucide-react-native';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import {
  updateProfile,
  updateEmail,
  changePassword,
  parseApiError,
  getCohortProfile,
  CohortDisplayProfile,
  getPreferences,
  savePreferences,
} from '../services/api';
import type { UserPreferences } from '../types';
import { getSavedUser, logout, signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';
import StyleProfileCard from '../components/StyleProfileCard';
import ReferralStatusCard from '../components/ReferralStatusCard';

interface ProfileScreenProps {
  navigation: any;
  onLogout: () => void;
}

export default function ProfileScreen({ navigation, onLogout }: ProfileScreenProps) {
  const { t } = useTranslation();
  const { language, switchLanguage } = useLanguage();

  const [user, setUser] = useState<any>(null);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');

  // Edit states
  const [editingName, setEditingName] = useState(false);
  const [nameLoading, setNameLoading] = useState(false);
  const [nameError, setNameError] = useState('');

  // Password modal
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  // Cohort display profile (null when confidence < medium or not yet collected)
  const [cohortDisplay, setCohortDisplay] = useState<CohortDisplayProfile | null>(null);

  // Preferences (kept in state so toggling AI sharing round-trips through PUT /preferences)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [aiSharingSaving, setAiSharingSaving] = useState(false);
  const [aiSharingError, setAiSharingError] = useState('');

  useEffect(() => {
    loadUser();
    loadCohortProfile();
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    const p = await getPreferences();
    setPreferences(p);
  };

  // Default ON when undefined (matches backend semantics from B1.4)
  const aiSharingEnabled = preferences?.ai_sharing_enabled !== false;

  const handleAiSharingToggle = async (value: boolean) => {
    if (aiSharingSaving) return;
    setAiSharingError('');
    const previous = preferences;
    const next: UserPreferences = {
      priorities: previous?.priorities ?? [],
      budget: previous?.budget ?? 'mid',
      lifestyle: previous?.lifestyle ?? [],
      brand_attitude: previous?.brand_attitude ?? 'best_of_both',
      ai_sharing_enabled: value,
    };
    setPreferences(next);
    setAiSharingSaving(true);
    try {
      const result = await savePreferences(next);
      if (!result.success) {
        setPreferences(previous);
        setAiSharingError(result.error || t('profile.aiSharing.errorSave'));
      }
    } catch (err: any) {
      setPreferences(previous);
      setAiSharingError(parseApiError(err).message || t('profile.aiSharing.errorSave'));
    } finally {
      setAiSharingSaving(false);
    }
  };

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    if (savedUser) {
      setUser(savedUser);
      setDisplayName((savedUser as any).display_name || savedUser.email?.split('@')[0] || '');
      setEmail(savedUser.email || '');
    }
  };

  const loadCohortProfile = async () => {
    try {
      const { display } = await getCohortProfile();
      setCohortDisplay(display);
    } catch {
      setCohortDisplay(null);
    }
  };

  const handleEditStyleProfile = () => {
    // Reuses the existing onboarding flow in edit mode. The seeded
    // preferences come pre-filled; saving any field flips its source
    // from "inferred" to "user_stated" via PUT /preferences (B.6).
    navigation.navigate('Onboarding', { mode: 'edit', source: 'styleProfile' });
  };

  const handleUpdateName = async () => {
    const trimmed = displayName.trim();
    if (trimmed.length < 2) {
      setNameError('Name must be at least 2 characters');
      return;
    }
    setNameError('');
    setNameLoading(true);
    try {
      const result = await updateProfile(trimmed);
      if (result.success) {
        setEditingName(false);
      } else {
        setNameError(result.error || 'Update failed');
      }
    } catch (err: any) {
      setNameError(parseApiError(err).message);
    } finally {
      setNameLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword) { setPasswordError('Current password is required'); return; }
    if (newPassword.length < 6) { setPasswordError('Password must be at least 6 characters'); return; }
    if (newPassword !== confirmPassword) { setPasswordError('Passwords do not match'); return; }
    setPasswordError('');
    setPasswordLoading(true);
    try {
      const result = await changePassword(currentPassword, newPassword);
      if (result.success) {
        Alert.alert('Success', 'Password changed successfully');
        setPasswordModalVisible(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setPasswordError(result.error || 'Password change failed');
      }
    } catch (err: any) {
      setPasswordError(parseApiError(err).message);
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleLogout = () => {
    Alert.alert(t('profile.logout'), t('profile.deleteConfirm').replace('This cannot be undone.', ''), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('profile.logout'),
        style: 'destructive',
        onPress: async () => {
          await logout();
          onLogout();
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(t('profile.deleteAccount'), t('profile.deleteConfirm'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('profile.deleteAccount'),
        style: 'destructive',
        onPress: async () => {
          // TODO: call delete account API when available
          Alert.alert('Not available', 'Account deletion coming soon.');
        },
      },
    ]);
  };

  const renderRow = (
    icon: React.ReactNode,
    label: string,
    right: React.ReactNode,
    onPress?: () => void,
    isLast = false
  ) => (
    <TouchableOpacity
      style={[styles.row, !isLast && styles.rowBorder]}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={onPress ? 0.6 : 1}
    >
      <View style={styles.rowStart}>
        {icon}
        <Text style={styles.rowLabel}>{label}</Text>
      </View>
      {right}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.screenTitle}>{t('profile.title')}</Text>

        {/* Cohort style profile (only renders when confidence >= medium) */}
        <StyleProfileCard display={cohortDisplay} onEditPress={handleEditStyleProfile} />

        {/* Referral status card (F4.5) — silently hides when feature flag is off, anon, or network down */}
        <ReferralStatusCard />

        {/* Account Card */}
        <View style={styles.card}>
          <View style={styles.profileRow}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(displayName || email || '?')[0].toUpperCase()}
              </Text>
            </View>
            <View style={styles.profileInfo}>
              {editingName ? (
                <View style={styles.editNameRow}>
                  <TextInput
                    style={styles.nameInput}
                    value={displayName}
                    onChangeText={(text) => { setDisplayName(text); setNameError(''); }}
                    autoFocus
                    maxLength={100}
                  />
                  <TouchableOpacity onPress={handleUpdateName} disabled={nameLoading}>
                    {nameLoading ? (
                      <ActivityIndicator size="small" color={colors.accent} />
                    ) : (
                      <Text style={styles.saveName}>{t('common.save')}</Text>
                    )}
                  </TouchableOpacity>
                </View>
              ) : (
                <Text style={styles.profileName}>{displayName}</Text>
              )}
              <Text style={styles.profileEmail}>{email}</Text>
              {nameError ? <Text style={styles.errorText}>{nameError}</Text> : null}
            </View>
          </View>
          <TouchableOpacity onPress={() => setEditingName(!editingName)}>
            <Text style={styles.editLink}>
              {editingName ? t('common.cancel') : t('profile.editProfile')}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Settings Card */}
        <Text style={styles.sectionLabel}>{t('profile.settings')}</Text>
        <View style={styles.card}>
          {renderRow(
            <Globe size={18} color={colors.text.secondary} />,
            t('profile.language'),
            <View style={styles.langToggle}>
              <TouchableOpacity
                style={[styles.langOption, language === 'en' && styles.langOptionActive]}
                onPress={() => switchLanguage('en')}
              >
                <Text style={[styles.langText, language === 'en' && styles.langTextActive]}>EN</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.langOption, language === 'ar' && styles.langOptionActive]}
                onPress={() => switchLanguage('ar')}
              >
                <Text style={[styles.langText, language === 'ar' && styles.langTextActive]}>عر</Text>
              </TouchableOpacity>
            </View>
          )}
          {renderRow(
            <Sliders size={18} color={colors.text.secondary} />,
            t('profile.preferences'),
            <ChevronRight size={16} color={colors.text.placeholder} />,
            () => navigation.navigate('Onboarding', { mode: 'edit' })
          )}
          {renderRow(
            <Lock size={18} color={colors.text.secondary} />,
            'Change Password',
            <ChevronRight size={16} color={colors.text.placeholder} />,
            () => setPasswordModalVisible(true),
            true
          )}
        </View>

        {/* Privacy Card */}
        <Text style={styles.sectionLabel}>{t('profile.section.privacy')}</Text>
        <View style={styles.card}>
          <View style={styles.privacyRow}>
            <View style={styles.privacyHeader}>
              <Shield size={18} color={colors.text.secondary} />
              <Text style={styles.privacyTitle}>{t('profile.aiSharing.title')}</Text>
            </View>
            <Switch
              value={aiSharingEnabled}
              onValueChange={handleAiSharingToggle}
              disabled={aiSharingSaving || preferences === null}
              trackColor={{ false: colors.border.medium, true: colors.accent }}
              thumbColor={'#FFFFFF'}
              accessibilityLabel={t('profile.aiSharing.title')}
            />
          </View>
          <Text style={styles.privacySubtitle}>{t('profile.aiSharing.subtitle')}</Text>
          {aiSharingError ? <Text style={styles.errorText}>{aiSharingError}</Text> : null}
        </View>

        {/* Support Card */}
        <Text style={styles.sectionLabel}>{t('profile.support')}</Text>
        <View style={styles.card}>
          {renderRow(
            <FileText size={18} color={colors.text.secondary} />,
            t('profile.privacy'),
            <ChevronRight size={16} color={colors.text.placeholder} />,
            () => {}
          )}
          {renderRow(
            <ScrollText size={18} color={colors.text.secondary} />,
            t('profile.terms'),
            <ChevronRight size={16} color={colors.text.placeholder} />,
            () => {}
          )}
          {renderRow(
            <MessageCircle size={18} color={colors.text.secondary} />,
            t('profile.contact'),
            <ChevronRight size={16} color={colors.text.placeholder} />,
            () => {},
            true
          )}
        </View>

        {/* Danger Card */}
        <View style={[styles.card, { marginTop: spacing.xl }]}>
          {renderRow(
            <LogOut size={18} color={colors.text.secondary} />,
            t('profile.logout'),
            null,
            handleLogout
          )}
          {renderRow(
            <Trash2 size={18} color={colors.destructive} />,
            t('profile.deleteAccount'),
            null,
            handleDeleteAccount,
            true
          )}
        </View>

        <View style={{ height: spacing['3xl'] }} />
      </ScrollView>

      {/* Password Change Modal */}
      <Modal visible={passwordModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Change Password</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Current password"
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={currentPassword}
              onChangeText={(t) => { setCurrentPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="New password (min 6 chars)"
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={newPassword}
              onChangeText={(t) => { setNewPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="Confirm new password"
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={confirmPassword}
              onChangeText={(t) => { setConfirmPassword(t); setPasswordError(''); }}
            />
            {passwordError ? <Text style={styles.errorText}>{passwordError}</Text> : null}
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancel}
                onPress={() => {
                  setPasswordModalVisible(false);
                  setPasswordError('');
                  setCurrentPassword('');
                  setNewPassword('');
                  setConfirmPassword('');
                }}
              >
                <Text style={styles.modalCancelText}>{t('common.cancel')}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalSave, passwordLoading && { opacity: 0.6 }]}
                onPress={handleChangePassword}
                disabled={passwordLoading}
              >
                {passwordLoading ? (
                  <ActivityIndicator size="small" color={colors.bg.primary} />
                ) : (
                  <Text style={styles.modalSaveText}>Change Password</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.base,
  },
  screenTitle: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.xl,
  },
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    marginBottom: spacing.sm,
  },
  sectionLabel: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
    marginStart: spacing.xs,
  },
  // Profile account
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
    marginEnd: spacing.md,
  },
  avatarText: {
    ...typography.title,
    color: colors.bg.primary,
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  profileEmail: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: 2,
  },
  editLink: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
  },
  editNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  nameInput: {
    flex: 1,
    ...typography.body,
    color: colors.text.primary,
    borderBottomWidth: 1,
    borderBottomColor: colors.accent,
    paddingVertical: 2,
  },
  saveName: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    marginTop: spacing.xs,
  },
  // Privacy card
  privacyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  privacyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    flexShrink: 1,
  },
  privacyTitle: {
    ...typography.body,
    color: colors.text.primary,
    flexShrink: 1,
  },
  privacySubtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },
  // Rows
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
  },
  rowBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border.light,
  },
  rowStart: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  rowLabel: {
    ...typography.body,
    color: colors.text.primary,
  },
  // Language toggle
  langToggle: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: colors.border.light,
    borderRadius: radii.chip,
    overflow: 'hidden',
  },
  langOption: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  langOptionActive: {
    backgroundColor: colors.accent,
  },
  langText: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
  },
  langTextActive: {
    color: colors.bg.primary,
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.bg.primary,
    borderTopStartRadius: spacing.xl,
    borderTopEndRadius: spacing.xl,
    padding: spacing.lg,
    paddingBottom: spacing['3xl'],
  },
  modalHandle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: spacing.lg,
  },
  modalTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  modalInput: {
    borderWidth: 1,
    borderColor: colors.border.medium,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    paddingVertical: Platform.OS === 'ios' ? spacing.md : spacing.sm,
    ...typography.body,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  modalCancel: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  modalCancelText: {
    ...typography.body,
    color: colors.accent,
  },
  modalSave: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.button,
  },
  modalSaveText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
  },
});
