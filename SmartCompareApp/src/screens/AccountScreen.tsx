/**
 * SmartCompare - Account Settings Screen
 * Name/email editing, password change, logout
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  Alert, ActivityIndicator, Modal, SafeAreaView, Platform,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../types';
import { updateProfile, updateEmail, changePassword } from '../services/api';
import { getSavedUser, logout, signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Account'>;
};

export default function AccountScreen({ navigation }: Props) {
  const [user, setUser] = useState<any>(null);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [nameLoading, setNameLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [nameError, setNameError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [nameSuccess, setNameSuccess] = useState('');
  const [emailSuccess, setEmailSuccess] = useState('');

  // Password modal state
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  // Social connect state
  const [socialLoading, setSocialLoading] = useState('');
  const [showApple, setShowApple] = useState(false);

  useEffect(() => {
    loadUser();
    if (Platform.OS === 'ios') {
      isAppleSignInAvailable().then(setShowApple);
    }
  }, []);

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    if (savedUser) {
      setUser(savedUser);
      setDisplayName((savedUser as any).display_name || savedUser.email?.split('@')[0] || '');
      setEmail(savedUser.email || '');
    }
  };

  // --- Validation helpers ---
  const validateName = (name: string): string | null => {
    const trimmed = name.trim();
    if (trimmed.length < 2) return 'Name must be at least 2 characters';
    if (trimmed.length > 100) return 'Name must be 100 characters or less';
    return null;
  };

  const validateEmailFormat = (emailStr: string): string | null => {
    const trimmed = emailStr.trim();
    if (!trimmed) return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) return 'Invalid email format';
    return null;
  };

  const validatePassword = (password: string): string | null => {
    if (password.length < 6) return 'Password must be at least 6 characters';
    return null;
  };

  // --- Handlers ---
  const handleUpdateName = async () => {
    const error = validateName(displayName);
    if (error) { setNameError(error); return; }
    setNameError('');
    setNameSuccess('');
    setNameLoading(true);
    try {
      const result = await updateProfile(displayName.trim());
      if (result.success) {
        setNameSuccess('Name updated');
        setTimeout(() => setNameSuccess(''), 3000);
      } else {
        setNameError(result.error || 'Update failed');
      }
    } catch (err: any) {
      setNameError(err.message || 'An error occurred');
    } finally {
      setNameLoading(false);
    }
  };

  const handleUpdateEmail = async () => {
    const error = validateEmailFormat(email);
    if (error) { setEmailError(error); return; }
    setEmailError('');
    setEmailSuccess('');
    setEmailLoading(true);
    try {
      const result = await updateEmail(email.trim());
      if (result.success) {
        setEmailSuccess('Verification email sent');
        setTimeout(() => setEmailSuccess(''), 5000);
      } else {
        setEmailError(result.error || 'Update failed');
      }
    } catch (err: any) {
      setEmailError(err.message || 'An error occurred');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword) { setPasswordError('Current password is required'); return; }
    const pwError = validatePassword(newPassword);
    if (pwError) { setPasswordError(pwError); return; }
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
      setPasswordError(err.message || 'An error occurred');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleLogout = async () => {
    Alert.alert('Log Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
          navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(displayName || email || '?')[0].toUpperCase()}
            </Text>
          </View>
          <Text style={styles.headerEmail}>{email}</Text>
        </View>

        {/* Display Name */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Display Name</Text>
          <View style={styles.fieldRow}>
            <TextInput
              style={styles.input}
              value={displayName}
              onChangeText={(text) => { setDisplayName(text); setNameError(''); setNameSuccess(''); }}
              placeholder="Your name"
              maxLength={100}
            />
            <TouchableOpacity style={styles.saveButton} onPress={handleUpdateName} disabled={nameLoading}>
              {nameLoading ? <ActivityIndicator size="small" color="#FFF" /> : <Text style={styles.saveButtonText}>Save</Text>}
            </TouchableOpacity>
          </View>
          {nameError ? <Text style={styles.errorText}>{nameError}</Text> : null}
          {nameSuccess ? <Text style={styles.successText}>{nameSuccess}</Text> : null}
        </View>

        {/* Email */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Email</Text>
          <View style={styles.fieldRow}>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={(text) => { setEmail(text); setEmailError(''); setEmailSuccess(''); }}
              placeholder="your@email.com"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <TouchableOpacity style={styles.saveButton} onPress={handleUpdateEmail} disabled={emailLoading}>
              {emailLoading ? <ActivityIndicator size="small" color="#FFF" /> : <Text style={styles.saveButtonText}>Save</Text>}
            </TouchableOpacity>
          </View>
          {emailError ? <Text style={styles.errorText}>{emailError}</Text> : null}
          {emailSuccess ? <Text style={styles.successText}>{emailSuccess}</Text> : null}
        </View>

        {/* Security */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Security</Text>
          <TouchableOpacity style={styles.menuItem} onPress={() => setPasswordModalVisible(true)}>
            <Text style={styles.menuItemText}>Change Password</Text>
            <Text style={styles.menuItemArrow}>{'\u203A'}</Text>
          </TouchableOpacity>
        </View>

        {/* Connected Accounts */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Connected Accounts</Text>
          <TouchableOpacity
            style={styles.socialConnectButton}
            onPress={async () => {
              setSocialLoading('google');
              try {
                const result = await signInWithGoogle();
                if (result.success) {
                  Alert.alert('Success', 'Google account connected');
                } else if (result.error !== 'Sign-in cancelled') {
                  Alert.alert('Error', result.error || 'Failed to connect Google');
                }
              } catch (err: any) {
                Alert.alert('Error', err.message || 'Failed to connect Google');
              } finally {
                setSocialLoading('');
              }
            }}
            disabled={!!socialLoading}
          >
            {socialLoading === 'google' ? (
              <ActivityIndicator size="small" color="#333" />
            ) : (
              <Text style={styles.socialConnectText}>Connect Google</Text>
            )}
          </TouchableOpacity>

          {showApple && (
            <TouchableOpacity
              style={[styles.socialConnectButton, { marginTop: 8 }]}
              onPress={async () => {
                setSocialLoading('apple');
                try {
                  const result = await signInWithApple();
                  if (result.success) {
                    Alert.alert('Success', 'Apple ID connected');
                  } else if (result.error !== 'Sign-in cancelled') {
                    Alert.alert('Error', result.error || 'Failed to connect Apple');
                  }
                } catch (err: any) {
                  Alert.alert('Error', err.message || 'Failed to connect Apple');
                } finally {
                  setSocialLoading('');
                }
              }}
              disabled={!!socialLoading}
            >
              {socialLoading === 'apple' ? (
                <ActivityIndicator size="small" color="#333" />
              ) : (
                <Text style={styles.socialConnectText}>Connect Apple ID</Text>
              )}
            </TouchableOpacity>
          )}
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Password Change Modal */}
      <Modal visible={passwordModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Change Password</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Current password"
              secureTextEntry
              value={currentPassword}
              onChangeText={(t) => { setCurrentPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="New password (min 6 chars)"
              secureTextEntry
              value={newPassword}
              onChangeText={(t) => { setNewPassword(t); setPasswordError(''); }}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="Confirm new password"
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
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalSave, passwordLoading && { opacity: 0.6 }]}
                onPress={handleChangePassword}
                disabled={passwordLoading}
              >
                {passwordLoading ? (
                  <ActivityIndicator size="small" color="#FFF" />
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
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  scrollContent: { padding: 16 },
  profileHeader: { alignItems: 'center', marginBottom: 24, marginTop: 8 },
  avatar: {
    width: 72, height: 72, borderRadius: 36, backgroundColor: '#007AFF',
    justifyContent: 'center', alignItems: 'center', marginBottom: 8,
  },
  avatarText: { fontSize: 28, fontWeight: '700', color: '#FFF' },
  headerEmail: { fontSize: 14, color: '#888' },
  section: { backgroundColor: '#FFF', borderRadius: 12, padding: 16, marginBottom: 16 },
  sectionTitle: {
    fontSize: 13, fontWeight: '600', color: '#888',
    textTransform: 'uppercase', marginBottom: 12,
  },
  fieldRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  input: {
    flex: 1, borderWidth: 1, borderColor: '#DDD', borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === 'ios' ? 12 : 8,
    fontSize: 16,
  },
  saveButton: {
    backgroundColor: '#007AFF', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8,
  },
  saveButtonText: { color: '#FFF', fontWeight: '600', fontSize: 14 },
  errorText: { color: '#FF3B30', fontSize: 13, marginTop: 6 },
  successText: { color: '#34C759', fontSize: 13, marginTop: 6 },
  menuItem: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', paddingVertical: 12,
  },
  menuItemText: { fontSize: 16, color: '#333' },
  menuItemArrow: { fontSize: 20, color: '#CCC' },
  socialConnectButton: {
    borderWidth: 1, borderColor: '#DDD', borderRadius: 8,
    paddingVertical: 12, alignItems: 'center', backgroundColor: '#FAFAFA',
  },
  socialConnectText: { fontSize: 15, color: '#333', fontWeight: '500' },
  logoutButton: {
    backgroundColor: '#FFF', borderRadius: 12, padding: 16,
    alignItems: 'center', marginTop: 8, marginBottom: 32,
  },
  logoutButtonText: { color: '#FF3B30', fontSize: 16, fontWeight: '600' },
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 24,
  },
  modalContent: { backgroundColor: '#FFF', borderRadius: 16, padding: 24 },
  modalTitle: { fontSize: 20, fontWeight: '700', marginBottom: 20, textAlign: 'center' },
  modalInput: {
    borderWidth: 1, borderColor: '#DDD', borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === 'ios' ? 12 : 8,
    fontSize: 16, marginBottom: 12,
  },
  modalButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  modalCancel: { paddingVertical: 12, paddingHorizontal: 20 },
  modalCancelText: { color: '#007AFF', fontSize: 16 },
  modalSave: {
    backgroundColor: '#007AFF', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8,
  },
  modalSaveText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
});
