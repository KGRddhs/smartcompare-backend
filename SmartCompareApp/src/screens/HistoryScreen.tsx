/**
 * SmartCompare - History Screen
 * Display past comparisons
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../types';
import { getComparisonHistory } from '../services/api';

type HistoryScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'History'>;
};

interface HistoryItem {
  id: string;
  products: any[];
  winner_index: number;
  recommendation: string;
  data_source: string;
  total_cost: number;
  created_at: string;
}

export default function HistoryScreen({ navigation }: HistoryScreenProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getComparisonHistory(20, 0);
      setHistory(data.comparisons || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('Error loading history:', error);
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
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderItem = ({ item }: { item: HistoryItem }) => {
    const winner = item.products[item.winner_index];
    const productNames = item.products
      .map((p: any) => `${p.brand} ${p.name}`.substring(0, 20))
      .join(' vs ');

    return (
      <TouchableOpacity style={styles.historyCard}>
        <View style={styles.cardHeader}>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
          <View style={[
            styles.sourceBadge,
            { backgroundColor: item.data_source === 'live' ? '#34C759' : '#FF9500' }
          ]}>
            <Text style={styles.sourceBadgeText}>{item.data_source}</Text>
          </View>
        </View>
        
        <Text style={styles.productsText} numberOfLines={1}>
          {productNames}
        </Text>
        
        <View style={styles.winnerRow}>
          <Text style={styles.winnerLabel}>🏆 Winner:</Text>
          <Text style={styles.winnerName}>
            {winner?.brand} {winner?.name}
          </Text>
        </View>
        
        {winner?.price && (
          <Text style={styles.priceText}>
            Best Price: {winner.price} {winner.currency || 'BHD'}
          </Text>
        )}
        
        <Text style={styles.costText}>
          Cost: ${item.total_cost?.toFixed(6) || '0.00'}
        </Text>
      </TouchableOpacity>
    );
  };

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyEmoji}>📭</Text>
      <Text style={styles.emptyTitle}>No Comparisons Yet</Text>
      <Text style={styles.emptyText}>
        Your comparison history will appear here
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
        <Text style={styles.headerSubtitle}>{total} comparisons</Text>
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
    marginBottom: 8,
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
  productsText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 8,
  },
  winnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  winnerLabel: {
    fontSize: 14,
    color: '#666',
  },
  winnerName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#34C759',
    marginLeft: 4,
  },
  priceText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
    marginTop: 4,
  },
  costText: {
    fontSize: 11,
    color: '#999',
    marginTop: 8,
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
  emptyEmoji: {
    fontSize: 64,
    marginBottom: 16,
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
});
