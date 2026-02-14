/**
 * SmartCompare - Home Screen
 * Multi-input: Camera, Text, URL
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  TextInput,
  ActivityIndicator,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { RootStackParamList } from '../types';
import { healthCheck } from '../services/api';
import { logout, getSavedUser, User } from '../services/authService';
import api from '../services/api';

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout: () => void;
};

type InputMethod = 'camera' | 'text' | 'url';

export default function HomeScreen({ navigation, onLogout }: HomeScreenProps) {
  const [user, setUser] = useState<User | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Input states
  const [inputMethod, setInputMethod] = useState<InputMethod>('camera');
  const [textQuery, setTextQuery] = useState('');
  const [url1, setUrl1] = useState('');
  const [url2, setUrl2] = useState('');

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
    try {
      const isHealthy = await healthCheck();
      setServerOnline(isHealthy);
    } catch (error) {
      setServerOnline(false);
    }
  };

  // Camera comparison
  const handleCameraCompare = () => {
    if (!serverOnline) {
      Alert.alert('Server Offline', 'Please check your connection.');
      return;
    }
    navigation.navigate('Camera');
  };

  // Text comparison
  const handleTextCompare = async () => {
    if (!textQuery.trim()) {
      Alert.alert('Enter Products', 'Example: "iPhone 15 vs Galaxy S24"');
      return;
    }
    
    setLoading(true);
    try {
      // nocache until Feb 15 to let stale 24h cache entries expire (created ~Feb 14 evening)
      const needsCacheBust = new Date() < new Date('2026-02-16');
      const response = await api.get('/api/v1/text/compare', {
        params: {
          q: textQuery.trim(),
          region: 'bahrain',
          ...(needsCacheBust && { nocache: true }),
        }
      });

      // Debug: log price data from API response
      (response.data?.products || []).forEach((p: any) => {
        console.log(`[PRICE DEBUG] ${p.name}: ${p.price?.currency} ${p.price?.amount} from ${p.price?.retailer}`);
      });

      if (response.data.success) {
        navigation.navigate('Results', { result: response.data });
      } else {
        Alert.alert('Error', response.data.error || 'Comparison failed');
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  // URL comparison
  const handleUrlCompare = async () => {
    if (!url1.trim() || !url2.trim()) {
      Alert.alert('Enter URLs', 'Paste product URLs from Amazon, Noon, etc.');
      return;
    }
    
    if (!url1.startsWith('http') || !url2.startsWith('http')) {
      Alert.alert('Invalid URL', 'URLs must start with http:// or https://');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post('/api/v1/url/compare', {
        url1: url1.trim(),
        url2: url2.trim(),
        region: 'bahrain',
      });
      
      if (response.data.success) {
        navigation.navigate('Results', { result: response.data });
      } else {
        Alert.alert('Error', response.data.error || 'Comparison failed');
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Logout',
        style: 'destructive',
        onPress: async () => {
          await logout();
          onLogout();
        }
      }
    ]);
  };

  const renderInputMethod = () => {
    switch (inputMethod) {
      case 'camera':
        return (
          <View style={styles.inputSection}>
            <Text style={styles.inputDescription}>
              Take photos of 2-4 products to compare
            </Text>
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={handleCameraCompare}
              disabled={!serverOnline || loading}
            >
              <Text style={styles.primaryButtonText}>📷 Open Camera</Text>
            </TouchableOpacity>
          </View>
        );
      
      case 'text':
        return (
          <View style={styles.inputSection}>
            <Text style={styles.inputDescription}>
              Type products to compare
            </Text>
            <TextInput
              style={styles.textInput}
              placeholder='e.g., "iPhone 15 vs Galaxy S24"'
              placeholderTextColor="#999"
              value={textQuery}
              onChangeText={setTextQuery}
              editable={!loading}
            />
            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.buttonDisabled]}
              onPress={handleTextCompare}
              disabled={!serverOnline || loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={styles.primaryButtonText}>⚡ Compare</Text>
              )}
            </TouchableOpacity>
          </View>
        );
      
      case 'url':
        return (
          <View style={styles.inputSection}>
            <Text style={styles.inputDescription}>
              Paste product URLs from any store
            </Text>
            <TextInput
              style={styles.textInput}
              placeholder="Product 1 URL (Amazon, Noon, etc.)"
              placeholderTextColor="#999"
              value={url1}
              onChangeText={setUrl1}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TextInput
              style={styles.textInput}
              placeholder="Product 2 URL"
              placeholderTextColor="#999"
              value={url2}
              onChangeText={setUrl2}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.buttonDisabled]}
              onPress={handleUrlCompare}
              disabled={!serverOnline || loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={styles.primaryButtonText}>🔗 Compare URLs</Text>
              )}
            </TouchableOpacity>
          </View>
        );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>SmartCompare</Text>
              <Text style={styles.subtitle}>AI-Powered Product Comparison</Text>
            </View>
            <TouchableOpacity style={styles.profileButton} onPress={handleLogout}>
              <Text style={styles.profileEmoji}>👤</Text>
            </TouchableOpacity>
          </View>

          {/* Status */}
          <View style={styles.statusBar}>
            <Text style={[styles.statusDot, serverOnline ? styles.online : styles.offline]}>●</Text>
            <Text style={styles.statusText}>
              {serverOnline ? 'Online' : 'Offline'}
            </Text>
            {user && (
              <Text style={styles.userEmail}> • {user.email}</Text>
            )}
          </View>

          {/* Input Method Selector */}
          <View style={styles.methodSelector}>
            <TouchableOpacity
              style={[styles.methodTab, inputMethod === 'camera' && styles.methodTabActive]}
              onPress={() => setInputMethod('camera')}
            >
              <Text style={[styles.methodTabText, inputMethod === 'camera' && styles.methodTabTextActive]}>
                📷 Camera
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.methodTab, inputMethod === 'text' && styles.methodTabActive]}
              onPress={() => setInputMethod('text')}
            >
              <Text style={[styles.methodTabText, inputMethod === 'text' && styles.methodTabTextActive]}>
                ⌨️ Text
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.methodTab, inputMethod === 'url' && styles.methodTabActive]}
              onPress={() => setInputMethod('url')}
            >
              <Text style={[styles.methodTabText, inputMethod === 'url' && styles.methodTabTextActive]}>
                🔗 URL
              </Text>
            </TouchableOpacity>
          </View>

          {/* Input Area */}
          <View style={styles.inputCard}>
            {renderInputMethod()}
          </View>

          {/* Examples */}
          <View style={styles.examplesCard}>
            <Text style={styles.examplesTitle}>
              {inputMethod === 'camera' && '📷 How Camera Works:'}
              {inputMethod === 'text' && '⌨️ Text Examples:'}
              {inputMethod === 'url' && '🔗 Supported Stores:'}
            </Text>
            {inputMethod === 'camera' && (
              <>
                <Text style={styles.exampleItem}>1. Point at 2-4 products</Text>
                <Text style={styles.exampleItem}>2. AI identifies them automatically</Text>
                <Text style={styles.exampleItem}>3. Get comparison with prices</Text>
              </>
            )}
            {inputMethod === 'text' && (
              <>
                <Text style={styles.exampleItem}>• "iPhone 15 vs Galaxy S24"</Text>
                <Text style={styles.exampleItem}>• "MacBook Air vs Dell XPS 13"</Text>
                <Text style={styles.exampleItem}>• "Nido milk vs Almarai milk"</Text>
              </>
            )}
            {inputMethod === 'url' && (
              <>
                <Text style={styles.exampleItem}>• Amazon (amazon.ae, amazon.sa)</Text>
                <Text style={styles.exampleItem}>• Noon (noon.com)</Text>
                <Text style={styles.exampleItem}>• Carrefour, Sharaf DG, Lulu</Text>
              </>
            )}
          </View>

          {/* History Button */}
          <TouchableOpacity
            style={styles.historyButton}
            onPress={() => navigation.navigate('History')}
          >
            <Text style={styles.historyButtonText}>📜 View History</Text>
          </TouchableOpacity>
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
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginTop: 10,
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  subtitle: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  profileButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
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
    fontSize: 18,
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  statusDot: {
    fontSize: 12,
    marginRight: 4,
  },
  online: {
    color: '#34C759',
  },
  offline: {
    color: '#FF3B30',
  },
  statusText: {
    fontSize: 13,
    color: '#666',
  },
  userEmail: {
    fontSize: 13,
    color: '#666',
  },
  methodSelector: {
    flexDirection: 'row',
    backgroundColor: '#E5E5EA',
    borderRadius: 10,
    padding: 4,
    marginBottom: 16,
  },
  methodTab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  methodTabActive: {
    backgroundColor: '#FFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  methodTabText: {
    fontSize: 13,
    color: '#666',
    fontWeight: '500',
  },
  methodTabTextActive: {
    color: '#007AFF',
    fontWeight: '600',
  },
  inputCard: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  inputSection: {
    alignItems: 'center',
  },
  inputDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 16,
    textAlign: 'center',
  },
  textInput: {
    width: '100%',
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    padding: 14,
    fontSize: 15,
    color: '#1A1A1A',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  primaryButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 10,
    width: '100%',
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  primaryButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  examplesCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  examplesTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  exampleItem: {
    fontSize: 13,
    color: '#666',
    marginBottom: 4,
    paddingLeft: 8,
  },
  historyButton: {
    backgroundColor: '#FFF',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  historyButtonText: {
    color: '#333',
    fontSize: 15,
    fontWeight: '600',
  },
});
