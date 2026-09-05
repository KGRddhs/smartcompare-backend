/**
 * Qaren — ProfileScreen (Bundle E F-S1.5c REWRITE)
 *
 * Top-down per JSX docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx:36-322.
 * Element order inside ScrollView:
 *   1. ProfileHeaderRow  — Q logo + name + dynamic "Capital · GCC" subtitle
 *                          + 36px circular Settings icon (→ EditProfile)
 *   2. RecentDecisionsRow — marquee of last 3 mini-vs cards (silently hides
 *                           on empty / threshold-miss / network)
 *   3. PrioritiesInline   — 3 weighted priority bars + "Tune" CTA (sum=100
 *                           per Path A R2 backend fix 4aa9cff)
 *   4. MonthStrip         — 3-tile (decisions / BHD saved / bonus credits)
 *   5. FlatSettings       — ONE unified card with 4 eyebrow groups per
 *                           JSX:251-275: ACCOUNT / PRIVACY & NOTIFICATIONS
 *                           / HELP / DANGER ZONE
 *
 * Deleted from Bundle D editorial composition (3ad84b1):
 *   - brandTitleRow + screenTitle (no "Profile" h1 — header IS the brand
 *     moment per JSX)
 *   - StyleProfileCard (user info moves into ProfileHeaderRow)
 *   - ReferralStatusCard (not in JSX)
 *   - Standalone Account-card with avatar block (data moved into header)
 *   - B6 Upgrade card with Sparkles icon (replaced by discreet row inside
 *     FlatSettings ACCOUNT group)
 *   - 4 standalone sectionLabel + Card blocks (replaced by SettingsEyebrow
 *     + FlatSettings inline subcomponents)
 *
 * Preferences row removed from ACCOUNT group per JSX:259-261; the
 * EditPreferences route is now reached via EditProfile → "Edit style
 * profile" linkRow per JSX EditProfileScreen.jsx:189-190.
 */

import React, { useState, useCallback, ReactNode } from 'react';
import { useFocusEffect } from '@react-navigation/native';
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
} from 'react-native';
import { useTranslation } from 'react-i18next';
import {
  Bell,
  ChevronRight,
  Settings,
  Shield,
} from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import {
  changePassword,
  parseApiError,
  getCohortProfile,
  CohortDisplayProfile,
  getPreferences,
  savePreferences,
  putReengagementSubs,
} from '../services/api';
import type { UserPreferences } from '../types';
import { getSavedUser, logout } from '../services/authService';
import QarenLogo from '../components/QarenLogo';
import ToggleRow from '../components/ToggleRow';
import { DirectionalIcon } from '../components/primitives/DirectionalIcon';
import {
  RecentDecisionsRow,
  PrioritiesInline,
  MonthStrip,
} from '../components/ProfileEditorialSections';

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

  // Password modal
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  // Cohort display feeds ProfileHeaderRow subtitle (governorate · GCC) via
  // loadCohortProfile → /auth/cohort-profile (B-S1.YELLOW 135d923 echoes
  // demographics.governorate through display.governorate).
  const [cohortDisplay, setCohortDisplay] = useState<CohortDisplayProfile | null>(null);

  // Preferences (round-trips through PUT /preferences)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [aiSharingSaving, setAiSharingSaving] = useState(false);
  const [aiSharingError, setAiSharingError] = useState('');
  const [notifsSaving, setNotifsSaving] = useState(false);
  const [notifsError, setNotifsError] = useState('');

  // F-S1.5k: useFocusEffect fires on mount AND every subsequent focus.
  // Replaces the previous mount-only useEffect so saves in EditProfile or
  // EditPreferences land on Profile immediately when the user navigates
  // back, instead of waiting for a full screen unmount/remount.
  useFocusEffect(
    useCallback(() => {
      loadUser();
      loadCohortProfile();
      loadPreferences();
    }, []),
  );

  const loadPreferences = async () => {
    const p = await getPreferences();
    setPreferences(p);
  };

  // Default OFF when undefined (Bundle D 1.F.6, R23). App-Store privacy
  // requires AI data sharing to be opt-IN.
  const aiSharingEnabled = preferences?.ai_sharing_enabled ?? false;

  const buildNextPrefs = (override: Partial<UserPreferences>): UserPreferences => {
    const previous = preferences;
    return {
      priorities: previous?.priorities ?? [],
      budget: previous?.budget ?? 'mid',
      lifestyle: previous?.lifestyle ?? [],
      brand_attitude: previous?.brand_attitude ?? 'best_of_both',
      ai_sharing_enabled: previous?.ai_sharing_enabled,
      notifications_enabled: previous?.notifications_enabled,
      notification_types: previous?.notification_types,
      ...override,
    };
  };

  const handleAiSharingToggle = async (value: boolean) => {
    if (aiSharingSaving) return;
    setAiSharingError('');
    const previous = preferences;
    const next = buildNextPrefs({ ai_sharing_enabled: value });
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

  // F5.4 — notifications master toggle ONLY. Sub-toggles route through
  // handleSubToggle → PUT /reengagement-subs.
  const handleNotificationsToggle = async (override: Partial<UserPreferences>) => {
    if (notifsSaving) return;
    setNotifsError('');
    const previous = preferences;
    const next = buildNextPrefs(override);
    setPreferences(next);
    setNotifsSaving(true);
    try {
      const result = await savePreferences(next);
      if (!result.success) {
        setPreferences(previous);
        setNotifsError(result.error || t('profile.notifs.errorSave'));
      }
    } catch (err: any) {
      setPreferences(previous);
      setNotifsError(parseApiError(err).message || t('profile.notifs.errorSave'));
    } finally {
      setNotifsSaving(false);
    }
  };

  // Bundle D 2.F.1 (R18) — re-engagement sub-toggles via PUT
  // /api/v1/auth/reengagement-subs (FE plural keys ↔ DB singular keys).
  // Opt-OUT default by design (re-engagement chosen at onboarding step 17).
  const handleSubToggle = async (
    key: 'decision_insight' | 'cohort_curiosity' | 'decision_retrospective',
    value: boolean
  ) => {
    if (notifsSaving) return;
    setNotifsError('');
    const previous = preferences;
    const next = buildNextPrefs({
      notification_types: {
        ...(previous?.notification_types ?? {}),
        [key]: value,
      },
    });
    setPreferences(next);
    setNotifsSaving(true);

    const nt = next.notification_types ?? {};
    const body = {
      decision_insights: nt.decision_insight !== false,
      peer_decision_updates: nt.cohort_curiosity !== false,
      decision_retrospectives: nt.decision_retrospective !== false,
    };

    try {
      const result = await putReengagementSubs(body);
      if (!result.success) {
        setPreferences(previous);
        const msg = result.error || t('profile.notifs.errorSave');
        setNotifsError(msg);
        Alert.alert(t('profile.notifs.errorTitle'), msg);
      }
    } catch (err: any) {
      setPreferences(previous);
      const msg = parseApiError(err).message || t('profile.notifs.errorSave');
      setNotifsError(msg);
      Alert.alert(t('profile.notifs.errorTitle'), msg);
    } finally {
      setNotifsSaving(false);
    }
  };

  const notificationsEnabled = preferences?.notifications_enabled !== false;
  const notifTypes = preferences?.notification_types ?? {};
  const insightEnabled = notifTypes.decision_insight !== false;
  const cohortEnabled = notifTypes.cohort_curiosity !== false;
  const retroEnabled = notifTypes.decision_retrospective !== false;

  // F-S1.5i: Backend Pydantic `priorities: min_length=1` rejects every
  // /preferences PUT that ships with an empty priorities array. The
  // five toggles below (AI sharing master + notifications master + 3
  // re-engagement sub-toggles) all flow through savePreferences /
  // putReengagementSubs, so when the user has no priorities yet, those
  // toggles would silently 422 every flip. Gate them visually (muted
  // row, disabled flip) and route a tap on the row to EditPreferences
  // so the user can pick a priority first. Once `preferences` itself
  // is null (fresh load / network blip), treat the same way — saver
  // path can't succeed either way.
  const hasPriorities = (preferences?.priorities?.length ?? 0) > 0;
  const togglesGated = preferences === null || !hasPriorities;

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

  // Bundle E F-S1.5c (c.2.i ruling): Both Profile→Tune AND EditProfile→
  // "Edit style profile" converge on EditPreferences. JSX EditProfileScreen
  // .jsx:189-190 subtitle "Update priorities, budget, and brand stance"
  // describes the lighter EditPreferencesFlow, not the 17-step Onboarding
  // re-run. Onboarding(mode='edit') remains in code for full re-onboarding
  // but no longer has a user-facing entry-point.
  const handleEditStyleProfile = () => {
    navigation.navigate('EditPreferences');
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
        Alert.alert(t('profile.password.success_title'), t('profile.password.success_body'));
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

  // -------------------------------------------------------------------------
  // Inline subcomponents (kept colocated — they're file-local recipes that
  // don't make sense outside the FlatSettings layout)
  // -------------------------------------------------------------------------

  // JSX:40 subtitle reads "{governorate} · GCC". Backend B-S1.YELLOW
  // (135d923) extended /auth/cohort-profile to echo demographics
  // governorate. Null/undefined when the user skipped onboarding Step 04
  // OR selected the "Prefer not to say" sentinel — backend null-resolves
  // both EN and AR forms, so any truthy string is safe to render.
  const regionSubtitle = cohortDisplay?.governorate
    ? `${cohortDisplay.governorate} · GCC`
    : 'GCC';

  const ProfileHeaderRow = () => (
    <View style={styles.headerRow}>
      <QarenLogo size={28} />
      <View style={styles.headerText}>
        <Text style={styles.headerName} numberOfLines={1}>
          {displayName || email?.split('@')[0] || ''}
        </Text>
        <Text style={styles.headerSubtitle} numberOfLines={1}>
          {regionSubtitle}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.headerSettingsBtn}
        onPress={() => navigation.navigate('EditProfile')}
        accessibilityRole="button"
        accessibilityLabel={t('profile.settings', { defaultValue: 'Settings' })}
        testID="profile-header-settings"
      >
        <Settings size={18} color={colors.text.primary} />
      </TouchableOpacity>
    </View>
  );

  const SettingsEyebrow = ({ children }: { children: ReactNode }) => (
    <View style={styles.eyebrow}>
      <Text style={styles.eyebrowText}>{children}</Text>
    </View>
  );

  interface SettingsRowProps {
    label: string;
    onPress?: () => void;
    right?: ReactNode;
    destructive?: boolean;
    last?: boolean;
    testID?: string;
  }

  const SettingsRow = ({
    label,
    onPress,
    right,
    destructive,
    last,
    testID,
  }: SettingsRowProps) => (
    <TouchableOpacity
      style={[styles.flatRow, !last && styles.flatRowBorder]}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={onPress ? 0.6 : 1}
      accessibilityRole="button"
      testID={testID}
    >
      <Text
        style={[
          styles.flatRowLabel,
          destructive && { color: colors.destructive },
        ]}
      >
        {label}
      </Text>
      {right
        ? right
        : !destructive && (
            <DirectionalIcon>
              <ChevronRight size={16} color={colors.text.placeholder} />
            </DirectionalIcon>
          )}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* 1. Header — Q logo + name + region + settings icon */}
        <ProfileHeaderRow />

        {/* 2. Recent decisions marquee — F-S1.5f always-render with
            invitational empty-state card that routes to the Home tab so
            the user's first decision flows directly into the compare
            surface. */}
        <RecentDecisionsRow
          onItemPress={(comparisonId) =>
            // A18 — same defect as HomeScreen's Smart-pick CTA: the
            // recent-decision tap passed an invented `from_history` param
            // that ResultsScreen never reads, so re-opening a decision from
            // Profile dead-ended on the empty state. `comparison_id` is the
            // param the fetch effect consumes.
            navigation.navigate('Results', { comparison_id: comparisonId })
          }
          onSeeAll={() => navigation.navigate('HistoryTab' as never)}
          onEmptyCompareTap={() => navigation.navigate('HomeTab' as never)}
        />

        {/* 3. Priorities — 3 weighted bars + "Tune" CTA (sum=100 per Path A R2) */}
        <PrioritiesInline onTunePress={handleEditStyleProfile} />

        {/* 4. Month strip — decisions / BHD saved / bonus credits */}
        <MonthStrip />

        {/* 5. FlatSettings — ONE unified card per JSX:251-275 */}
        <View style={styles.flatCard}>
          {/* ACCOUNT */}
          <SettingsEyebrow>
            {t('profile.section.account', { defaultValue: 'Account' })}
          </SettingsEyebrow>
          <SettingsRow
            label={t('profile.editProfile')}
            onPress={() => navigation.navigate('EditProfile')}
            testID="profile-row-edit"
          />
          <SettingsRow
            label={t('profile.upgrade', { defaultValue: 'Upgrade to Premium' })}
            onPress={() => navigation.navigate('Paywall')}
            testID="profile-row-upgrade"
          />
          <SettingsRow
            label={t('profile.changePassword')}
            onPress={() => setPasswordModalVisible(true)}
            testID="profile-row-password"
          />
          <SettingsRow
            label={t('profile.language')}
            testID="profile-row-language"
            right={
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
            }
          />

          {/* PRIVACY & NOTIFICATIONS */}
          <SettingsEyebrow>
            {t('profile.section.privacy_notifications', {
              defaultValue: 'Privacy & notifications',
            })}
          </SettingsEyebrow>
          {/* F-S1.5i: when togglesGated, wrap each host in a TouchableOpacity
              that routes to EditPreferences. Mute the row visually so the
              user sees the toggle is dormant without a red error or
              modal interrupting them. */}
          <TouchableOpacity
            style={[styles.flatRowToggleHost, togglesGated && styles.flatRowToggleHostMuted]}
            onPress={togglesGated ? handleEditStyleProfile : undefined}
            activeOpacity={togglesGated ? 0.6 : 1}
            disabled={!togglesGated}
            accessibilityRole={togglesGated ? 'button' : undefined}
            accessibilityLabel={
              togglesGated
                ? t('profile.toggle.disabledReason', {
                    defaultValue: 'Pick your priorities first',
                  })
                : undefined
            }
          >
            <ToggleRow
              icon={<Shield size={18} color={colors.text.secondary} />}
              label={t('profile.aiSharing.title')}
              subtitle={t('profile.aiSharing.subtitle')}
              value={aiSharingEnabled}
              onValueChange={handleAiSharingToggle}
              disabled={aiSharingSaving || togglesGated}
            />
            {aiSharingError ? <Text style={styles.errorText}>{aiSharingError}</Text> : null}
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.flatRowToggleHost,
              styles.flatRowToggleHostLast,
              togglesGated && styles.flatRowToggleHostMuted,
            ]}
            onPress={togglesGated ? handleEditStyleProfile : undefined}
            activeOpacity={togglesGated ? 0.6 : 1}
            disabled={!togglesGated}
            accessibilityRole={togglesGated ? 'button' : undefined}
            accessibilityLabel={
              togglesGated
                ? t('profile.toggle.disabledReason', {
                    defaultValue: 'Pick your priorities first',
                  })
                : undefined
            }
          >
            <ToggleRow
              icon={<Bell size={18} color={colors.text.secondary} />}
              label={t('profile.notifs.master.title')}
              subtitle={t('profile.notifs.master.subtitle')}
              value={notificationsEnabled}
              onValueChange={(v) => handleNotificationsToggle({ notifications_enabled: v })}
              disabled={notifsSaving || togglesGated}
            />
            {notificationsEnabled && !togglesGated ? (
              <View style={styles.subToggles}>
                <ToggleRow
                  label={t('profile.notifs.insight')}
                  value={insightEnabled}
                  onValueChange={(v) => handleSubToggle('decision_insight', v)}
                  disabled={notifsSaving}
                />
                <ToggleRow
                  label={t('profile.notifs.cohort')}
                  value={cohortEnabled}
                  onValueChange={(v) => handleSubToggle('cohort_curiosity', v)}
                  disabled={notifsSaving}
                />
                <ToggleRow
                  label={t('profile.notifs.retrospective')}
                  value={retroEnabled}
                  onValueChange={(v) => handleSubToggle('decision_retrospective', v)}
                  disabled={notifsSaving}
                />
              </View>
            ) : null}
            {notifsError ? <Text style={styles.errorText}>{notifsError}</Text> : null}
          </TouchableOpacity>
          {togglesGated ? (
            <Text style={styles.toggleGatedCaption}>
              {t('profile.toggle.disabledReason', {
                defaultValue: 'Pick your priorities first',
              })}
            </Text>
          ) : null}

          {/* HELP */}
          <SettingsEyebrow>
            {t('profile.section.help', { defaultValue: 'Help' })}
          </SettingsEyebrow>
          <SettingsRow
            label={t('profile.privacy')}
            onPress={() => navigation.navigate('Legal', { doc: 'privacy' })}
            testID="profile-row-privacy"
          />
          <SettingsRow
            label={t('profile.terms')}
            onPress={() => navigation.navigate('Legal', { doc: 'terms' })}
            testID="profile-row-terms"
          />
          <SettingsRow
            label={t('profile.contact')}
            onPress={() => navigation.navigate('ContactUs')}
            testID="profile-row-contact"
          />

          {/* DANGER ZONE */}
          <SettingsEyebrow>
            {t('profile.section.danger', { defaultValue: 'Danger zone' })}
          </SettingsEyebrow>
          <SettingsRow
            label={t('profile.logout')}
            onPress={handleLogout}
            destructive
            last
            testID="profile-row-logout"
          />
        </View>

        <View style={{ height: spacing['3xl'] }} />
      </ScrollView>

      {/* Password Change Modal */}
      <Modal visible={passwordModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>{t('profile.changePassword')}</Text>
            <TextInput
              style={styles.modalInput}
              placeholder={t('profile.password.current')}
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={currentPassword}
              onChangeText={(v) => { setCurrentPassword(v); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder={t('profile.password.new')}
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={newPassword}
              onChangeText={(v) => { setNewPassword(v); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder={t('profile.password.confirm')}
              placeholderTextColor={colors.text.placeholder}
              secureTextEntry
              value={confirmPassword}
              onChangeText={(v) => { setConfirmPassword(v); setPasswordError(''); }}
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
                  <Text style={styles.modalSaveText}>{t('profile.changePassword')}</Text>
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
    paddingTop: spacing.sm,
  },
  // 1. ProfileHeaderRow — JSX:36-51
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: 18,
  },
  headerText: {
    flex: 1,
    minWidth: 0,
  },
  headerName: {
    fontSize: 18,
    fontWeight: '700',
    lineHeight: 18 * 1.2,
    color: colors.text.primary,
  },
  headerSubtitle: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
    marginTop: 2,
  },
  headerSettingsBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // 5. FlatSettings card — JSX:251-275
  flatCard: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.lg,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    overflow: 'hidden',
  },
  // SettingsEyebrow — JSX:239-250
  eyebrow: {
    paddingVertical: 10,
    paddingHorizontal: spacing.base,
    backgroundColor: colors.bg.primary,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border.light,
  },
  eyebrowText: {
    fontSize: 10,
    fontWeight: '600',
    lineHeight: 14,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    color: colors.text.placeholder,
  },
  // SettingsRow — JSX:224-237
  flatRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: 52,
    paddingVertical: 13,
    paddingHorizontal: spacing.base,
    backgroundColor: 'transparent',
  },
  flatRowBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border.light,
  },
  flatRowLabel: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 14 * 1.3,
    color: colors.text.primary,
  },
  // Hosts the existing ToggleRow component inside the flat card. The
  // toggle row brings its own 56px min-height + 12px padding; the host
  // just supplies the hairline border + error caption slot so the
  // flat-card rhythm holds.
  flatRowToggleHost: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border.light,
  },
  flatRowToggleHostLast: {
    borderBottomWidth: 0,
  },
  // F-S1.5i: muted state when toggles are gated on priorities pickup.
  // Whole row tap routes to EditPreferences; 0.55 opacity makes the
  // dormant intent legible without scary red.
  flatRowToggleHostMuted: {
    opacity: 0.55,
  },
  toggleGatedCaption: {
    ...typography.small,
    color: colors.text.placeholder,
    paddingHorizontal: spacing.base,
    paddingBottom: spacing.sm,
  },
  // F5.4 — sub-toggles inside the notifications master row
  subToggles: {
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border.light,
    gap: spacing.xs,
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    marginTop: spacing.xs,
    paddingHorizontal: spacing.base,
    paddingBottom: spacing.sm,
  },
  // ACCOUNT row 4 — Language EN/عر toggle (right-slot content)
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
  // Modal (password change) — unchanged from pre-rewrite
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
