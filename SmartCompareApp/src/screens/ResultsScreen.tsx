/**
 * SmartCompare - Results Screen
 * Display comparison results with winner and share option
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  Share,
  Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList, Product } from '../types';

type ResultsScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Results'>;
  route: RouteProp<RootStackParamList, 'Results'>;
};

export default function ResultsScreen({ navigation, route }: ResultsScreenProps) {
  const { result } = route.params;
  const { products, winner_index, recommendation, key_differences, data_freshness, total_cost } = result;

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'live':
        return '#34C759';
      case 'cached':
        return '#FF9500';
      case 'estimated':
        return '#FF3B30';
      default:
        return '#999';
    }
  };

  const formatPrice = (product: Product) => {
    if (product.price === null || product.price === undefined) {
      return 'Price unavailable';
    }
    return `${product.price.toFixed(2)} ${product.currency || 'BHD'}`;
  };

  const handleShare = async () => {
    try {
      const winner = products[winner_index];
      
      // Build share message
      let message = `🏆 SmartCompare Results\n\n`;
      message += `Winner: ${winner?.brand} ${winner?.name}\n`;
      message += `Best Price: ${formatPrice(winner)}\n\n`;
      
      message += `📊 Compared Products:\n`;
      products.forEach((product: Product, index: number) => {
        const isWinner = index === winner_index;
        message += `${isWinner ? '✅' : '•'} ${product.brand} ${product.name}: ${formatPrice(product)}\n`;
      });
      
      message += `\n💡 ${recommendation}\n`;
      
      if (key_differences && key_differences.length > 0) {
        message += `\n📋 Key Differences:\n`;
        key_differences.slice(0, 3).forEach((diff: string) => {
          message += `• ${diff}\n`;
        });
      }
      
      message += `\n---\nCompared with SmartCompare 📱`;

      await Share.share({
        message: message,
        title: 'SmartCompare Results',
      });
    } catch (error: any) {
      if (error.message !== 'User dismissed the dialog') {
        Alert.alert('Error', 'Could not share results');
      }
    }
  };

  const handleCopyToClipboard = async () => {
    try {
      const winner = products[winner_index];
      let text = `Winner: ${winner?.brand} ${winner?.name} - ${formatPrice(winner)}`;
      
      // Note: For full clipboard support, you'd need expo-clipboard
      // For now, we'll just use share
      await Share.share({ message: text });
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Comparison Results</Text>
          <View style={styles.headerActions}>
            <View style={[styles.freshnessBadge, { backgroundColor: getSourceBadgeColor(data_freshness) }]}>
              <Text style={styles.freshnessText}>
                {data_freshness === 'live' ? '🔴 Live' : 
                 data_freshness === 'cached' ? '📦 Cached' : 
                 data_freshness === 'mixed' ? '🔄 Mixed' : '📊 Est.'}
              </Text>
            </View>
            <TouchableOpacity style={styles.shareButton} onPress={handleShare}>
              <Text style={styles.shareButtonText}>📤 Share</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Winner Banner */}
        <View style={styles.winnerBanner}>
          <Text style={styles.winnerEmoji}>🏆</Text>
          <Text style={styles.winnerTitle}>Best Value</Text>
          <Text style={styles.winnerName}>
            {products[winner_index]?.brand} {products[winner_index]?.name}
          </Text>
          <Text style={styles.winnerPrice}>
            {formatPrice(products[winner_index])}
          </Text>
          {products[winner_index]?.size && (
            <Text style={styles.winnerSize}>{products[winner_index]?.size}</Text>
          )}
        </View>

        {/* Quick Share Banner */}
        <TouchableOpacity style={styles.quickShareBanner} onPress={handleShare}>
          <Text style={styles.quickShareText}>📱 Share this comparison with friends</Text>
        </TouchableOpacity>

        {/* Products Comparison */}
        <View style={styles.productsSection}>
          <Text style={styles.sectionTitle}>Products Compared</Text>
          
          {products.map((product: Product, index: number) => (
            <View 
              key={index} 
              style={[
                styles.productCard,
                index === winner_index && styles.productCardWinner
              ]}
            >
              {index === winner_index && (
                <View style={styles.winnerTag}>
                  <Text style={styles.winnerTagText}>WINNER</Text>
                </View>
              )}
              
              <View style={styles.productHeader}>
                <Text style={styles.productNumber}>#{index + 1}</Text>
                <View 
                  style={[
                    styles.sourceBadge, 
                    { backgroundColor: getSourceBadgeColor(product.source || 'unknown') }
                  ]}
                >
                  <Text style={styles.sourceBadgeText}>{product.source || 'unknown'}</Text>
                </View>
              </View>
              
              <Text style={styles.productBrand}>{product.brand}</Text>
              <Text style={styles.productName}>{product.name}</Text>
              
              {product.size && (
                <Text style={styles.productSize}>Size: {product.size}</Text>
              )}
              
              <View style={styles.priceRow}>
                <Text style={styles.priceLabel}>Price:</Text>
                <Text style={styles.priceValue}>{formatPrice(product)}</Text>
              </View>
              
              {product.retailer && (
                <Text style={styles.retailer}>From: {product.retailer}</Text>
              )}
              
              {product.note && (
                <Text style={styles.note}>{product.note}</Text>
              )}
            </View>
          ))}
        </View>

        {/* Recommendation */}
        <View style={styles.recommendationSection}>
          <Text style={styles.sectionTitle}>💡 AI Recommendation</Text>
          <View style={styles.recommendationCard}>
            <Text style={styles.recommendationText}>{recommendation}</Text>
          </View>
        </View>

        {/* Key Differences */}
        {key_differences && key_differences.length > 0 && (
          <View style={styles.differencesSection}>
            <Text style={styles.sectionTitle}>📋 Key Differences</Text>
            <View style={styles.differencesList}>
              {key_differences.map((diff: string, index: number) => (
                <View key={index} style={styles.differenceItem}>
                  <Text style={styles.differenceBullet}>•</Text>
                  <Text style={styles.differenceText}>{diff}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Cost Info */}
        <View style={styles.costSection}>
          <Text style={styles.costText}>
            API Cost: ${total_cost.toFixed(6)} (~{(total_cost * 100).toFixed(3)}¢)
          </Text>
        </View>

        {/* Actions */}
        <View style={styles.actionsSection}>
          <TouchableOpacity
            style={styles.newCompareButton}
            onPress={() => navigation.navigate('Camera')}
          >
            <Text style={styles.newCompareButtonText}>📷 New Comparison</Text>
          </TouchableOpacity>
          
          <View style={styles.secondaryActions}>
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={handleShare}
            >
              <Text style={styles.secondaryButtonText}>📤 Share</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={() => navigation.navigate('History')}
            >
              <Text style={styles.secondaryButtonText}>📜 History</Text>
            </TouchableOpacity>
          </View>
          
          <TouchableOpacity
            style={styles.homeButton}
            onPress={() => navigation.navigate('Home')}
          >
            <Text style={styles.homeButtonText}>🏠 Back to Home</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1A1A1A',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  freshnessBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  freshnessText: {
    color: '#FFF',
    fontSize: 11,
    fontWeight: '600',
  },
  shareButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  shareButtonText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600',
  },
  winnerBanner: {
    backgroundColor: '#34C759',
    marginHorizontal: 20,
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
  },
  winnerEmoji: {
    fontSize: 48,
    marginBottom: 8,
  },
  winnerTitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  winnerName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    textAlign: 'center',
    marginTop: 4,
  },
  winnerPrice: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFF',
    marginTop: 8,
  },
  winnerSize: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  quickShareBanner: {
    backgroundColor: '#E3F2FD',
    marginHorizontal: 20,
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    marginBottom: 20,
  },
  quickShareText: {
    color: '#1976D2',
    fontSize: 14,
    fontWeight: '500',
  },
  productsSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  productCard: {
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
  productCardWinner: {
    borderWidth: 2,
    borderColor: '#34C759',
  },
  winnerTag: {
    position: 'absolute',
    top: -10,
    right: 10,
    backgroundColor: '#34C759',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  winnerTagText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: 'bold',
  },
  productHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  productNumber: {
    fontSize: 14,
    fontWeight: 'bold',
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
  productBrand: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600',
  },
  productName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 4,
  },
  productSize: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  priceLabel: {
    fontSize: 14,
    color: '#666',
  },
  priceValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
    marginLeft: 8,
  },
  retailer: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  note: {
    fontSize: 12,
    color: '#FF9500',
    marginTop: 4,
    fontStyle: 'italic',
  },
  recommendationSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  recommendationCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  recommendationText: {
    fontSize: 15,
    color: '#333',
    lineHeight: 22,
  },
  differencesSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  differencesList: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
  },
  differenceItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  differenceBullet: {
    fontSize: 14,
    color: '#007AFF',
    marginRight: 8,
    fontWeight: 'bold',
  },
  differenceText: {
    fontSize: 14,
    color: '#333',
    flex: 1,
    lineHeight: 20,
  },
  costSection: {
    alignItems: 'center',
    marginBottom: 20,
  },
  costText: {
    fontSize: 12,
    color: '#999',
  },
  actionsSection: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  newCompareButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  newCompareButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  secondaryActions: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: '#FFF',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DDD',
  },
  secondaryButtonText: {
    color: '#333',
    fontSize: 14,
    fontWeight: '600',
  },
  homeButton: {
    backgroundColor: '#F5F5F5',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DDD',
  },
  homeButtonText: {
    color: '#666',
    fontSize: 14,
    fontWeight: '600',
  },
});
