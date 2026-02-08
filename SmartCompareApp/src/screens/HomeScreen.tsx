/**
 * SmartCompare - Home Screen (with Auth)
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { RootStackParamList, SubscriptionStatus } from '../types';
import { getSubscriptionStatus, healthCheck } from '../services/api';
import { logout, getSavedUser, User } from '../services/authService';

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout: () => void;
};

export default function HomeScreen({ navigation, onLogout }: HomeScreenProps) {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [serverOnline, setServerOnline] = useState(false);

  useFocusEffect(
    useCallback(() => {
      checkServer();
      loadUser();
    }, [])
  );

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    setUser(savedUser);
  };

  const checkServer = async () => {
    setLoading(true);
    try {
      const isHealthy = await healthCheck();
      setServerOnline(isHealthy);

      if (isHealthy) {
        const subStatus = await getSubscriptionStatus();
        setStatus(subStatus);
      }
    } catch (error) {
      console.log('Server check failed:', error);
      setServerOnline(false);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = () => {
    if (!serverOnline) {
      Alert.alert('Server Offline', 'Please check your internet connection and try again.');
      return;
    }

    if (status && status.remaining_comparisons === 0) {
      Alert.alert(
        'Daily Limit Reached',
        'You\'ve used all your free comparisons today. Upgrade to Premium for unlimited access!',
        [
          { text: 'OK', style: 'cancel' },
          { text: 'Upgrade', onPress: () => Alert.alert('Coming Soon', 'Premium subscriptions coming soon!') }
        ]
      );
      return;
    }

    navigation.navigate('Camera');
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
            onLogout();
          }
        }
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Header with user info */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>SmartCompare</Text>
            <Text style={styles.subtitle}>AI-Powered Shopping Intelligence</Text>
          </View>
          <TouchableOpacity style={styles.profileButton} onPress={handleLogout}>
            <Text style={styles.profileEmoji}>👤</Text>
          </TouchableOpacity>
        </View>

        {/* User Card */}
        {user && (
          <View style={styles.userCard}>
            <View style={styles.userInfo}>
              <Text style={styles.userEmail}>{user.email}</Text>
              <View style={styles.tierBadge}>
                <Text style={styles.tierText}>
                  {status?.subscription_tier === 'premium' ? '⭐ Premium' : '🆓 Free'}
                </Text>
              </View>
            </View>
            <TouchableOpacity onPress={handleLogout}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Status Card */}
        <View style={styles.statusCard}>
          {loading ? (
            <ActivityIndicator size="small" color="#007AFF" />
          ) : serverOnline ? (
            <>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Server</Text>
                <Text style={[styles.statusValue, styles.online]}>● Online</Text>
              </View>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Today's Usage</Text>
                <Text style={styles.statusValue}>
                  {status?.daily_usage || 0} / {status?.daily_limit || '∞'}
                </Text>
              </View>
              {status?.remaining_comparisons !== null && (
                <View style={styles.statusRow}>
                  <Text style={styles.statusLabel}>Remaining</Text>
                  <Text style={[
                    styles.statusValue,
                    status?.remaining_comparisons === 0 && styles.warning
                  ]}>
                    {status?.remaining_comparisons} comparisons
                  </Text>
                </View>
              )}
            </>
          ) : (
            <View style={styles.offlineContainer}>
              <Text style={[styles.statusValue, styles.offline]}>● Server Offline</Text>
              <Text style={styles.offlineHint}>
                Check your internet connection
              </Text>
              <TouchableOpacity style={styles.retryButton} onPress={checkServer}>
                <Text style={styles.retryText}>Retry</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Main Action Button */}
        <TouchableOpacity
          style={[styles.compareButton, !serverOnline && styles.buttonDisabled]}
          onPress={handleCompare}
          disabled={!serverOnline}
        >
          <Text style={styles.compareButtonText}>📷 Compare Products</Text>
        </TouchableOpacity>

        {/* Secondary Actions */}
        <View style={styles.secondaryActions}>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => navigation.navigate('History')}
          >
            <Text style={styles.secondaryButtonText}>📜 History</Text>
          </TouchableOpacity>
        </View>

        {/* Instructions */}
        <View style={styles.instructions}>
          <Text style={styles.instructionsTitle}>How it works:</Text>
          <Text style={styles.instructionStep}>1. Take photos of 2-4 products</Text>
          <Text style={styles.instructionStep}>2. AI identifies products & finds prices</Text>
          <Text style={styles.instructionStep}>3. Get instant comparison & winner</Text>
        </View>

        {/* Premium Upsell */}
        {status?.subscription_tier !== 'premium' && (
          <TouchableOpacity style={styles.premiumBanner}>
            <Text style={styles.premiumText}>⭐ Upgrade to Premium</Text>
            <Text style={styles.premiumSubtext}>Unlimited comparisons • Coming Soon</Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginTop: 20,
    marginBottom: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  profileButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#FFF',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  profileEmoji: {
    fontSize: 20,
  },
  userCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  userInfo: {
    flex: 1,
  },
  userEmail: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  tierBadge: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  tierText: {
    fontSize: 12,
    color: '#1976D2',
    fontWeight: '600',
  },
  logoutText: {
    color: '#FF3B30',
    fontSize: 14,
    fontWeight: '600',
  },
  statusCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  statusLabel: {
    fontSize: 14,
    color: '#666',
  },
  statusValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  online: {
    color: '#34C759',
  },
  offline: {
    color: '#FF3B30',
  },
  warning: {
    color: '#FF9500',
  },
  offlineContainer: {
    alignItems: 'center',
    padding: 10,
  },
  offlineHint: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
  },
  retryButton: {
    marginTop: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#007AFF',
    borderRadius: 8,
  },
  retryText: {
    color: '#FFF',
    fontWeight: '600',
  },
  compareButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonDisabled: {
    backgroundColor: '#CCC',
  },
  compareButtonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 24,
  },
  secondaryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#FFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#DDD',
  },
  secondaryButtonText: {
    color: '#333',
    fontSize: 14,
    fontWeight: '600',
  },
  instructions: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#1A1A1A',
  },
  instructionStep: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    paddingLeft: 8,
  },
  premiumBanner: {
    backgroundColor: '#FFF9C4',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  premiumText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#F57C00',
  },
  premiumSubtext: {
    fontSize: 12,
    color: '#FF8F00',
    marginTop: 4,
  },
});
