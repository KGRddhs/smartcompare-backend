/**
 * SmartCompare - Register Screen
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { register, signInWithGoogle, signInWithApple, isAppleSignInAvailable } from '../services/authService';
import { AuthStackParamList } from '../types';

type RegisterScreenProps = {
  navigation: NativeStackNavigationProp<AuthStackParamList, 'Register'>;
  onRegisterSuccess: () => void;
};

export default function RegisterScreen({ navigation, onRegisterSuccess }: RegisterScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmError, setConfirmError] = useState('');
  const [socialLoading, setSocialLoading] = useState('');
  const [showApple, setShowApple] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'ios') {
      isAppleSignInAvailable().then(setShowApple);
    }
  }, []);

  const handleGoogleSignIn = async () => {
    setSocialLoading('google');
    setError('');
    try {
      const result = await signInWithGoogle();
      if (result.success) {
        onRegisterSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || 'Google sign-in failed');
      }
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed');
    } finally {
      setSocialLoading('');
    }
  };

  const handleAppleSignIn = async () => {
    setSocialLoading('apple');
    setError('');
    try {
      const result = await signInWithApple();
      if (result.success) {
        onRegisterSuccess();
      } else if (result.error !== 'Sign-in cancelled') {
        setError(result.error || 'Apple sign-in failed');
      }
    } catch (err: any) {
      setError(err.message || 'Apple sign-in failed');
    } finally {
      setSocialLoading('');
    }
  };

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleRegister = async () => {
    let hasError = false;
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      setEmailError('Email is required');
      hasError = true;
    } else if (!validateEmail(trimmedEmail)) {
      setEmailError('Invalid email format');
      hasError = true;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError('Password is required');
      hasError = true;
    } else if (password.length < 6) {
      setPasswordError('Password must be at least 6 characters');
      hasError = true;
    } else {
      setPasswordError('');
    }

    if (!confirmPassword) {
      setConfirmError('Please confirm your password');
      hasError = true;
    } else if (password !== confirmPassword) {
      setConfirmError('Passwords do not match');
      hasError = true;
    } else {
      setConfirmError('');
    }

    if (hasError) return;

    setLoading(true);
    setError('');

    try {
      const result = await register(email.trim().toLowerCase(), password);

      if (result.success) {
        onRegisterSuccess();
      } else {
        setError(result.error || 'Registration failed');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.content}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.logo}>SmartCompare</Text>
              <Text style={styles.subtitle}>Create your account</Text>
            </View>

            {/* Register Form */}
            <View style={styles.form}>
              <Text style={styles.title}>Sign Up</Text>

              {error ? (
                <View style={styles.errorContainer}>
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              ) : null}

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Email</Text>
                <TextInput
                  style={[styles.input, emailError ? styles.inputError : null]}
                  placeholder="Enter your email"
                  placeholderTextColor="#999"
                  value={email}
                  onChangeText={(text) => { setEmail(text); setEmailError(''); }}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  editable={!loading}
                />
                {emailError ? <Text style={styles.fieldError}>{emailError}</Text> : null}
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Password</Text>
                <TextInput
                  style={[styles.input, passwordError ? styles.inputError : null]}
                  placeholder="Create a password (min 6 characters)"
                  placeholderTextColor="#999"
                  value={password}
                  onChangeText={(text) => { setPassword(text); setPasswordError(''); }}
                  secureTextEntry
                  editable={!loading}
                />
                {passwordError ? <Text style={styles.fieldError}>{passwordError}</Text> : null}
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Confirm Password</Text>
                <TextInput
                  style={[styles.input, confirmError ? styles.inputError : null]}
                  placeholder="Confirm your password"
                  placeholderTextColor="#999"
                  value={confirmPassword}
                  onChangeText={(text) => { setConfirmPassword(text); setConfirmError(''); }}
                  secureTextEntry
                  editable={!loading}
                />
                {confirmError ? <Text style={styles.fieldError}>{confirmError}</Text> : null}
              </View>

              <TouchableOpacity
                style={[styles.registerButton, loading && styles.buttonDisabled]}
                onPress={handleRegister}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#FFF" />
                ) : (
                  <Text style={styles.registerButtonText}>Create Account</Text>
                )}
              </TouchableOpacity>

              {/* Social Sign-In */}
              <View style={styles.dividerRow}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>or</Text>
                <View style={styles.dividerLine} />
              </View>

              <TouchableOpacity
                style={styles.socialButton}
                onPress={handleGoogleSignIn}
                disabled={!!socialLoading || loading}
              >
                {socialLoading === 'google' ? (
                  <ActivityIndicator size="small" color="#333" />
                ) : (
                  <Text style={styles.socialButtonText}>Continue with Google</Text>
                )}
              </TouchableOpacity>

              {showApple && (
                <TouchableOpacity
                  style={[styles.socialButton, styles.appleSocialButton]}
                  onPress={handleAppleSignIn}
                  disabled={!!socialLoading || loading}
                >
                  {socialLoading === 'apple' ? (
                    <ActivityIndicator size="small" color="#FFF" />
                  ) : (
                    <Text style={[styles.socialButtonText, styles.appleSocialText]}>Continue with Apple</Text>
                  )}
                </TouchableOpacity>
              )}

              {/* Benefits */}
              <View style={styles.benefits}>
                <Text style={styles.benefitsTitle}>Free Account Includes:</Text>
                <Text style={styles.benefitItem}>✓ 5 comparisons per day</Text>
                <Text style={styles.benefitItem}>✓ AI-powered product identification</Text>
                <Text style={styles.benefitItem}>✓ Live price comparison</Text>
                <Text style={styles.benefitItem}>✓ Comparison history</Text>
              </View>
            </View>

            {/* Login Link */}
            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account?</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                <Text style={styles.loginLink}>Login</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logo: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  form: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 24,
    textAlign: 'center',
  },
  errorContainer: {
    backgroundColor: '#FFEBEE',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#C62828',
    fontSize: 14,
    textAlign: 'center',
  },
  inputContainer: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#1A1A1A',
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  inputError: {
    borderColor: '#FF3B30',
  },
  fieldError: {
    color: '#FF3B30',
    fontSize: 12,
    marginTop: 4,
  },
  registerButton: {
    backgroundColor: '#34C759',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  registerButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  benefits: {
    marginTop: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#EEE',
  },
  benefitsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  benefitItem: {
    fontSize: 13,
    color: '#666',
    marginBottom: 4,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
  },
  footerText: {
    color: '#666',
    fontSize: 14,
  },
  loginLink: {
    color: '#007AFF',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 4,
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#DDD',
  },
  dividerText: {
    marginHorizontal: 12,
    color: '#888',
    fontSize: 14,
  },
  socialButton: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    marginBottom: 10,
    backgroundColor: '#FFF',
  },
  socialButtonText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  appleSocialButton: {
    backgroundColor: '#000',
    borderColor: '#000',
  },
  appleSocialText: {
    color: '#FFF',
  },
});
