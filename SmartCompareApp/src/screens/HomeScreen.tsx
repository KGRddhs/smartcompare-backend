/**
 * SmartCompare - Home Screen
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, SubscriptionStatus } from '../types';
import { getSubscriptionStatus, healthCheck } from '../services/api';

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
};

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [serverOnline, setServerOnline] = useState(false);

  useEffect(() => {
    checkServer();
  }, []);

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
      alert('Server is offline. Please make sure the backend is running.');
      return;
    }

    if (status && status.remaining_comparisons === 0) {
      alert('Daily limit reached! Upgrade to Premium for unlimited comparisons.');
      return;
    }

    navigation.navigate('Camera');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Logo/Title */}
        <View style={styles.header}>
          <Text style={styles.title}>SmartCompare</Text>
          <Text style={styles.subtitle}>AI-Powered Shopping Intelligence</Text>
        </View>

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
                <Text style={styles.statusLabel}>Plan</Text>
                <Text style={styles.statusValue}>
                  {status?.subscription_tier === 'premium' ? '⭐ Premium' : 'Free'}
                </Text>
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
                  <Text style={styles.statusValue}>
                    {status?.remaining_comparisons} comparisons
                  </Text>
                </View>
              )}
            </>
          ) : (
            <View style={styles.offlineContainer}>
              <Text style={[styles.statusValue, styles.offline]}>● Server Offline</Text>
              <Text style={styles.offlineHint}>
                Make sure backend is running:{'\n'}
                poetry run uvicorn app.main:app --reload
              </Text>
              <TouchableOpacity style={styles.retryButton} onPress={checkServer}>
                <Text style={styles.retryText}>Retry Connection</Text>
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
    alignItems: 'center',
    marginTop: 40,
    marginBottom: 30,
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 8,
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
  offlineContainer: {
    alignItems: 'center',
    padding: 10,
  },
  offlineHint: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    fontFamily: 'monospace',
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
    marginBottom: 30,
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
});
