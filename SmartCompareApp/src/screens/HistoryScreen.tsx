/**
 * SmartCompare - History Screen
 * Display past comparisons with view, delete, and re-compare options
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Modal,
  ScrollView,
  TextInput,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { RootStackParamList, Product } from '../types';
import { getComparisonHistory, deleteComparison } from '../services/api';

type HistoryScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'History'>;
};

interface HistoryItem {
  id: string;
  full_response: any;  // Complete API response blob
  query: string;
  input_type: string;
  product_names: string[];
  created_at: string;
}

export default function HistoryScreen({ navigation }: HistoryScreenProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [total, setTotal] = useState(0);
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Reload history when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadHistory();
    }, [])
  );

  const loadHistory = async () => {
    try {
      const data = await getComparisonHistory(50, 0, searchQuery || undefined);
      setHistory(data.comparisons || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error loading history:', error);
      // Don't show alert for auth errors — user may not be logged in
      if ((error as any)?.response?.status !== 401) {
        Alert.alert('Error', 'Failed to load history');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadHistory();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  const formatPrice = (product: any) => {
    if (!product || product.price === null || product.price === undefined) {
      return 'N/A';
    }
    if (typeof product.price === 'object') {
      if (product.price.amount === null || product.price.amount === undefined) {
        return 'N/A';
      }
      return `${product.price.amount.toFixed(2)} ${product.price.currency || 'BHD'}`;
    }
    return `${(product.price as number).toFixed(2)} BHD`;
  };

  const openDetails = (item: HistoryItem) => {
    setSelectedItem(item);
    setModalVisible(true);
  };

  const viewAsResult = (item: HistoryItem) => {
    setModalVisible(false);
    // Pass the full stored blob directly — same shape as live response
    navigation.navigate('Results', {
      result: item.full_response,
    });
  };

  const handleDelete = async (item: HistoryItem) => {
    Alert.alert(
      'Delete Comparison',
      'Are you sure you want to delete this comparison?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteComparison(item.id);
              setHistory((prev) => prev.filter((h) => h.id !== item.id));
              setTotal((prev) => prev - 1);
              setModalVisible(false);
            } catch (error) {
              Alert.alert('Error', 'Failed to delete comparison');
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: HistoryItem }) => {
    const products = item.full_response?.products || [];
    const winner_index = item.full_response?.comparison?.winner_index ?? item.full_response?.winner_index ?? 0;
    const winner = products[winner_index];

    return (
      <TouchableOpacity style={styles.historyCard} onPress={() => openDetails(item)}>
        <View style={styles.cardHeader}>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
          <View style={[
            styles.sourceBadge,
            { backgroundColor: item.input_type === 'camera' ? '#5856D6' : '#34C759' }
          ]}>
            <Text style={styles.sourceBadgeText}>{item.input_type || 'text'}</Text>
          </View>
        </View>

        <View style={styles.vsContainer}>
          <View style={styles.productSummary}>
            <Text style={styles.productLabel}>Product 1</Text>
            <Text style={styles.productSummaryName} numberOfLines={1}>
              {products[0]?.brand} {products[0]?.name}
            </Text>
            <Text style={styles.productSummaryPrice}>{formatPrice(products[0])}</Text>
          </View>

          <Text style={styles.vsText}>VS</Text>

          <View style={styles.productSummary}>
            <Text style={styles.productLabel}>Product 2</Text>
            <Text style={styles.productSummaryName} numberOfLines={1}>
              {products[1]?.brand} {products[1]?.name}
            </Text>
            <Text style={styles.productSummaryPrice}>{formatPrice(products[1])}</Text>
          </View>
        </View>

        {winner && (
          <View style={styles.winnerRow}>
            <Text style={styles.winnerEmoji}>🏆</Text>
            <Text style={styles.winnerName} numberOfLines={1}>
              {winner?.brand} {winner?.name}
            </Text>
            <Text style={styles.winnerPrice}>{formatPrice(winner)}</Text>
          </View>
        )}

        <View style={styles.tapHint}>
          <Text style={styles.tapHintText}>Tap to view details</Text>
        </View>
      </TouchableOpacity>
    );
  };

  const renderModal = () => {
    if (!selectedItem) return null;

    const products = selectedItem.full_response?.products || [];
    const comparison = selectedItem.full_response?.comparison || {};
    const winner_index = comparison.winner_index ?? 0;
    const recommendation = comparison.recommendation || '';
    const key_differences = comparison.key_differences || [];

    return (
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Comparison Details</Text>
                <TouchableOpacity onPress={() => setModalVisible(false)}>
                  <Text style={styles.closeButton}>✕</Text>
                </TouchableOpacity>
              </View>

              <Text style={styles.modalDate}>
                {new Date(selectedItem.created_at).toLocaleString()}
              </Text>

              {/* Winner Banner */}
              {products[winner_index] && (
                <View style={styles.modalWinnerBanner}>
                  <Text style={styles.modalWinnerEmoji}>🏆</Text>
                  <Text style={styles.modalWinnerLabel}>Winner</Text>
                  <Text style={styles.modalWinnerName}>
                    {products[winner_index]?.brand}{' '}
                    {products[winner_index]?.name}
                  </Text>
                  <Text style={styles.modalWinnerPrice}>
                    {formatPrice(products[winner_index])}
                  </Text>
                </View>
              )}

              {/* Products */}
              <Text style={styles.modalSectionTitle}>Products Compared</Text>
              {products.map((product: any, index: number) => (
                <View
                  key={index}
                  style={[
                    styles.modalProductCard,
                    index === winner_index && styles.modalProductWinner
                  ]}
                >
                  {index === winner_index && (
                    <View style={styles.winnerBadge}>
                      <Text style={styles.winnerBadgeText}>WINNER</Text>
                    </View>
                  )}
                  <Text style={styles.modalProductBrand}>{product.brand}</Text>
                  <Text style={styles.modalProductName}>{product.name}</Text>
                  <Text style={styles.modalProductPrice}>{formatPrice(product)}</Text>
                </View>
              ))}

              {/* Recommendation */}
              {recommendation ? (
                <>
                  <Text style={styles.modalSectionTitle}>Recommendation</Text>
                  <View style={styles.modalRecommendation}>
                    <Text style={styles.modalRecommendationText}>
                      {recommendation}
                    </Text>
                  </View>
                </>
              ) : null}

              {/* Key Differences */}
              {key_differences.length > 0 && (
                <>
                  <Text style={styles.modalSectionTitle}>Key Differences</Text>
                  <View style={styles.modalDifferences}>
                    {key_differences.map((diff: string, index: number) => (
                      <Text key={index} style={styles.modalDifferenceItem}>
                        {'\u2022'} {diff}
                      </Text>
                    ))}
                  </View>
                </>
              )}

              {/* Actions */}
              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.modalActionButton}
                  onPress={() => viewAsResult(selectedItem)}
                >
                  <Text style={styles.modalActionText}>View Full Results</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.modalActionButton, { backgroundColor: '#FF3B30' }]}
                  onPress={() => handleDelete(selectedItem)}
                >
                  <Text style={styles.modalActionText}>Delete</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.modalActionButton, styles.modalActionSecondary]}
                  onPress={() => setModalVisible(false)}
                >
                  <Text style={styles.modalActionTextSecondary}>Close</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    );
  };

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyTitle}>No Comparisons Yet</Text>
      <Text style={styles.emptyText}>
        Your comparison history will appear here after you compare products.
      </Text>
      <TouchableOpacity
        style={styles.startButton}
        onPress={() => navigation.navigate('Camera')}
      >
        <Text style={styles.startButtonText}>Start Comparing</Text>
      </TouchableOpacity>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading history...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Comparison History</Text>
        <Text style={styles.headerSubtitle}>{total} comparison{total !== 1 ? 's' : ''}</Text>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search comparisons..."
          placeholderTextColor="#999"
          value={searchQuery}
          onChangeText={setSearchQuery}
          onSubmitEditing={() => { setLoading(true); loadHistory(); }}
          returnKeyType="search"
        />
      </View>

      <FlatList
        data={history}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={renderEmpty}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />

      {renderModal()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    padding: 20,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#FFF',
  },
  searchInput: {
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    color: '#333',
  },
  listContent: {
    padding: 16,
    flexGrow: 1,
  },
  historyCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dateText: {
    fontSize: 12,
    color: '#999',
  },
  sourceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  sourceBadgeText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  vsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  productSummary: {
    flex: 1,
  },
  productLabel: {
    fontSize: 10,
    color: '#999',
    textTransform: 'uppercase',
  },
  productSummaryName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    marginTop: 2,
  },
  productSummaryPrice: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#007AFF',
    marginTop: 2,
  },
  vsText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#999',
    marginHorizontal: 10,
  },
  winnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E8F5E9',
    padding: 10,
    borderRadius: 8,
  },
  winnerEmoji: {
    fontSize: 16,
    marginRight: 8,
  },
  winnerName: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    color: '#2E7D32',
  },
  winnerPrice: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E7D32',
  },
  tapHint: {
    marginTop: 10,
    alignItems: 'center',
  },
  tapHintText: {
    fontSize: 11,
    color: '#999',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#666',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
  },
  startButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  startButtonText: {
    color: '#FFF',
    fontWeight: '600',
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '85%',
    padding: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  closeButton: {
    fontSize: 24,
    color: '#999',
    padding: 4,
  },
  modalDate: {
    fontSize: 12,
    color: '#999',
    marginBottom: 16,
  },
  modalWinnerBanner: {
    backgroundColor: '#34C759',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 20,
  },
  modalWinnerEmoji: {
    fontSize: 32,
  },
  modalWinnerLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    textTransform: 'uppercase',
    marginTop: 4,
  },
  modalWinnerName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFF',
    textAlign: 'center',
    marginTop: 4,
  },
  modalWinnerPrice: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFF',
    marginTop: 4,
  },
  modalSectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginTop: 16,
    marginBottom: 10,
  },
  modalProductCard: {
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  modalProductWinner: {
    borderWidth: 2,
    borderColor: '#34C759',
  },
  winnerBadge: {
    position: 'absolute',
    top: -8,
    right: 8,
    backgroundColor: '#34C759',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  winnerBadgeText: {
    color: '#FFF',
    fontSize: 9,
    fontWeight: 'bold',
  },
  modalProductBrand: {
    fontSize: 12,
    color: '#666',
  },
  modalProductName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  modalProductPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
    marginTop: 4,
  },
  modalRecommendation: {
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    padding: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#007AFF',
  },
  modalRecommendationText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  modalDifferences: {
    backgroundColor: '#F5F5F5',
    borderRadius: 10,
    padding: 12,
  },
  modalDifferenceItem: {
    fontSize: 13,
    color: '#333',
    marginBottom: 6,
    lineHeight: 18,
  },
  modalActions: {
    marginTop: 20,
    marginBottom: 20,
  },
  modalActionButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  modalActionText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  modalActionSecondary: {
    backgroundColor: '#F5F5F5',
  },
  modalActionTextSecondary: {
    color: '#666',
    fontSize: 16,
    fontWeight: '600',
  },
});
