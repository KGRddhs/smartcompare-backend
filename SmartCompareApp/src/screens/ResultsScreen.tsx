/**
 * ResultsScreen - Comparison results with verified ratings
 * Shows "No verified rating available" if rating is null
 * Includes link to source when rating is verified
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Share,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RatingSource {
  name: string;
  url: string;
  retrieved_at: string;
  extract_method?: 'google_shopping' | 'json_ld' | 'microdata' | 'meta_tags' | 'css_selector';
  confidence?: 'high' | 'medium' | 'low';
}

interface Product {
  name: string;
  brand: string;
  full_name?: string;
  category?: string;
  price?: {
    amount: number | null;
    currency: string;
    retailer?: string;
    estimated?: boolean;
    note?: string;
    unavailable?: boolean;
  };
  specs?: Record<string, any>;
  rating?: number | null;
  review_count?: number | null;
  rating_verified?: boolean;
  rating_source?: RatingSource | null;
  pros?: string[];
  cons?: string[];
  confidence?: number;
  _rating_debug?: any;
}

interface Comparison {
  winner_index: number;
  winner_reason: string;
  recommendation: string;
  key_differences: string[];
  value_scores?: number[];
  best_for?: Record<string, number>;
  price_comparison?: {
    cheaper_index: number | null;
    price_difference: string;
    better_value_index: number;
  };
  specs_comparison?: {
    product_0_advantages: string[];
    product_1_advantages: string[];
    similar_features: string[];
  };
}

interface ResultsScreenProps {
  route: {
    params: {
      result: {
        success: boolean;
        products: Product[];
        comparison: Comparison;
        winner_index: number;
        recommendation: string;
        key_differences: string[];
        metadata?: {
          elapsed_seconds: number;
          total_cost: number;
          api_calls: number;
          cache_hits: number;
        };
      };
    };
  };
  navigation: any;
}

type TabType = 'overview' | 'specs' | 'reviews';

export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { result } = route.params;
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const { products, comparison, winner_index, recommendation, key_differences, metadata } = result;

  const formatPrice = (price?: Product['price']) => {
    if (!price || price.unavailable || price.amount === null) {
      return 'Price N/A';
    }
    return `${price.currency} ${price.amount.toLocaleString()}`;
  };

  const handleShare = async () => {
    try {
      const message = `Comparing ${products[0]?.name} vs ${products[1]?.name}\n\nWinner: ${products[winner_index]?.name}\n\n${recommendation}`;
      await Share.share({ message });
    } catch (error) {
      console.error('Share error:', error);
    }
  };

  const openRatingSource = (source: RatingSource | null | undefined, product?: Product) => {
    // Build a clean Google Shopping search URL instead of using the
    // internal redirect URL which crashes Chrome on Android
    const productName = product?.full_name || product?.name || '';
    if (productName) {
      const query = encodeURIComponent(productName);
      Linking.openURL(`https://www.google.com/search?q=${query}&tbm=shop`);
    } else if (source?.url) {
      Linking.openURL(source.url);
    }
  };

  // Rating display component with provenance
  const RatingDisplay = ({ product }: { product: Product }) => {
    const { rating, review_count, rating_verified, rating_source } = product;

    // If no rating or not verified, show "No verified rating"
    if (rating === null || rating === undefined || !rating_verified || !rating_source?.url) {
      return (
        <View style={styles.ratingContainer}>
          <Text style={styles.noRatingText}>No verified rating</Text>
          <Text style={styles.noRatingSubtext}>
            Rating could not be verified from retailers
          </Text>
        </View>
      );
    }

    // Confidence indicator
    const getConfidenceColor = () => {
      if (rating_source?.extract_method === 'google_shopping') return '#4CAF50'; // High
      if (rating_source?.extract_method === 'json_ld') return '#4CAF50'; // High
      if (rating_source?.extract_method === 'microdata') return '#4CAF50'; // High
      return '#FFC107'; // Medium
    };

    const getMethodLabel = () => {
      switch (rating_source?.extract_method) {
        case 'google_shopping': return 'Verified';
        case 'json_ld': return 'Verified';
        case 'microdata': return 'Verified';
        case 'meta_tags': return 'Extracted';
        case 'css_selector': return 'Parsed';
        default: return 'Verified';
      }
    };

    // Show verified rating with source
    return (
      <View style={styles.ratingContainer}>
        <View style={styles.ratingRow}>
          <Ionicons name="star" size={16} color="#FFD700" />
          <Text style={styles.ratingText}>{rating.toFixed(1)}</Text>
          {review_count && review_count > 0 && (
            <Text style={styles.reviewCount}>({review_count.toLocaleString()} reviews)</Text>
          )}
        </View>
        
        {/* Source attribution with link */}
        <TouchableOpacity
          onPress={() => openRatingSource(rating_source, product)}
          style={styles.sourceLink}
        >
          <View style={[styles.verifiedBadge, { backgroundColor: getConfidenceColor() }]}>
            <Text style={styles.verifiedBadgeText}>{getMethodLabel()}</Text>
          </View>
          <Text style={styles.sourceText}>
            {rating_source.name}
          </Text>
          <Ionicons name="open-outline" size={12} color="#2196F3" />
        </TouchableOpacity>
      </View>
    );
  };

  // Product card component
  const ProductCard = ({ product, index }: { product: Product; index: number }) => {
    const isWinner = index === winner_index;
    const valueScore = comparison.value_scores?.[index];

    return (
      <View style={[styles.productCard, isWinner && styles.winnerCard]}>
        {isWinner && (
          <View style={styles.winnerBadge}>
            <Text style={styles.winnerBadgeText}>🏆 WINNER</Text>
          </View>
        )}
        
        <Text style={styles.brandText}>{product.brand}</Text>
        <Text style={styles.productName}>{product.name}</Text>
        
        {/* Price */}
        <Text style={[
          styles.priceText,
          product.price?.unavailable && styles.priceUnavailable
        ]}>
          {formatPrice(product.price)}
        </Text>
        {product.price?.estimated && (
          <Text style={styles.priceNote}>*Converted price</Text>
        )}
        {product.price?.retailer && !product.price?.unavailable && (
          <Text style={styles.retailerText}>{product.price.retailer}</Text>
        )}
        
        {/* Rating with source */}
        <RatingDisplay product={product} />
        
        {/* Value Score */}
        {valueScore !== undefined && (
          <View style={styles.valueScoreContainer}>
            <Text style={styles.valueScoreLabel}>Value Score</Text>
            <Text style={styles.valueScoreText}>{valueScore}/10</Text>
          </View>
        )}
      </View>
    );
  };

  // Specs comparison tab - unified table with both products side by side
  const SpecsTab = () => {
    // Merge all spec keys from both products, preserving order
    const allKeys: string[] = [];
    const seen = new Set<string>();
    products.forEach((product) => {
      if (product.specs) {
        Object.keys(product.specs).forEach((key) => {
          if (!seen.has(key)) {
            seen.add(key);
            allKeys.push(key);
          }
        });
      }
    });

    return (
      <View style={styles.tabContent}>
        {/* Unified specs comparison table */}
        <View style={styles.specsCard}>
          {/* Table header */}
          <View style={styles.specsTableHeader}>
            <View style={styles.specsTableHeaderLabel}>
              <Text style={styles.specsTableHeaderText}>Spec</Text>
            </View>
            {products.map((product, index) => (
              <View key={index} style={styles.specsTableHeaderCell}>
                <Text style={styles.specsTableHeaderText} numberOfLines={1}>
                  {product.name}
                </Text>
              </View>
            ))}
          </View>

          {/* Table rows */}
          {allKeys.map((key, rowIndex) => (
            <View
              key={key}
              style={[
                styles.specsTableRow,
                rowIndex % 2 === 0 && styles.specsTableRowAlt,
              ]}
            >
              <View style={styles.specsTableLabel}>
                <Text style={styles.specKey}>{key.replace(/_/g, ' ')}</Text>
              </View>
              {products.map((product, colIndex) => {
                const val = product.specs?.[key];
                return (
                  <View key={colIndex} style={styles.specsTableCell}>
                    <Text style={val ? styles.specValue : styles.specMissing}>
                      {val ? String(val) : '-'}
                    </Text>
                  </View>
                );
              })}
            </View>
          ))}
        </View>

        {/* Advantages comparison */}
        {comparison.specs_comparison && (
          <View style={styles.advantagesSection}>
            <Text style={styles.sectionTitle}>Advantages</Text>

            {comparison.specs_comparison.product_0_advantages?.length > 0 && (
              <View style={styles.advantageCard}>
                <Text style={styles.advantageTitle}>{products[0]?.name}</Text>
                {comparison.specs_comparison.product_0_advantages.map((adv, i) => (
                  <Text key={i} style={styles.advantageItem}>+ {adv}</Text>
                ))}
              </View>
            )}

            {comparison.specs_comparison.product_1_advantages?.length > 0 && (
              <View style={styles.advantageCard}>
                <Text style={styles.advantageTitle}>{products[1]?.name}</Text>
                {comparison.specs_comparison.product_1_advantages.map((adv, i) => (
                  <Text key={i} style={styles.advantageItem}>+ {adv}</Text>
                ))}
              </View>
            )}
          </View>
        )}
      </View>
    );
  };

  // Reviews tab (pros/cons)
  const ReviewsTab = () => (
    <View style={styles.tabContent}>
      {products.map((product, index) => (
        <View key={index} style={styles.reviewCard}>
          <Text style={styles.reviewCardTitle}>{product.name}</Text>
          
          {/* Rating info */}
          <View style={styles.reviewRatingSection}>
            <RatingDisplay product={product} />
          </View>
          
          {/* Pros */}
          {product.pros && product.pros.length > 0 && (
            <View style={styles.prosConsSection}>
              <Text style={styles.prosTitle}>👍 Pros</Text>
              {product.pros.map((pro, i) => (
                <Text key={i} style={styles.proItem}>• {pro}</Text>
              ))}
            </View>
          )}
          
          {/* Cons */}
          {product.cons && product.cons.length > 0 && (
            <View style={styles.prosConsSection}>
              <Text style={styles.consTitle}>👎 Cons</Text>
              {product.cons.map((con, i) => (
                <Text key={i} style={styles.conItem}>• {con}</Text>
              ))}
            </View>
          )}
        </View>
      ))}
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Comparison</Text>
        <TouchableOpacity onPress={handleShare} style={styles.shareButton}>
          <Text style={styles.shareText}>Share</Text>
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={styles.tabBar}>
        {(['overview', 'specs', 'reviews'] as TabType[]).map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.activeTab]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.activeTabText]}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.content}>
        {activeTab === 'overview' && (
          <>
            {/* Product Cards */}
            <View style={styles.productsRow}>
              {products.map((product, index) => (
                <ProductCard key={index} product={product} index={index} />
              ))}
            </View>

            {/* Recommendation */}
            <View style={styles.recommendationSection}>
              <Text style={styles.sectionTitle}>💡 Recommendation</Text>
              <Text style={styles.recommendationText}>{recommendation}</Text>
            </View>

            {/* Key Differences */}
            <View style={styles.differencesSection}>
              <Text style={styles.sectionTitle}>🔍 Key Differences</Text>
              {key_differences?.map((diff, index) => (
                <Text key={index} style={styles.differenceItem}>• {diff}</Text>
              ))}
            </View>

            {/* Best For */}
            {comparison.best_for && (
              <View style={styles.bestForSection}>
                <Text style={styles.sectionTitle}>Best For</Text>
                <View style={styles.bestForGrid}>
                  {Object.entries(comparison.best_for).map(([category, winnerIdx]) => (
                    <View key={category} style={styles.bestForItem}>
                      <Text style={styles.bestForCategory}>
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </Text>
                      <Text style={styles.bestForWinner}>
                        {products[winnerIdx]?.name || 'N/A'}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Metadata */}
            {metadata && (
              <View style={styles.metadataSection}>
                <Text style={styles.metadataText}>
                  Comparison took {metadata.elapsed_seconds?.toFixed(1)}s • 
                  Cost: ${metadata.total_cost?.toFixed(4)} • 
                  {metadata.cache_hits > 0 ? `${metadata.cache_hits} cached` : 'Fresh data'}
                </Text>
              </View>
            )}
          </>
        )}

        {activeTab === 'specs' && <SpecsTab />}
        {activeTab === 'reviews' && <ReviewsTab />}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#2196F3',
    paddingTop: 50,
    paddingBottom: 15,
    paddingHorizontal: 15,
  },
  backButton: {
    padding: 5,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFF',
  },
  shareButton: {
    padding: 5,
  },
  shareText: {
    color: '#FFF',
    fontSize: 16,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  tab: {
    flex: 1,
    paddingVertical: 15,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#2196F3',
  },
  tabText: {
    fontSize: 14,
    color: '#666',
  },
  activeTabText: {
    color: '#2196F3',
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  productsRow: {
    flexDirection: 'row',
    padding: 10,
    gap: 10,
  },
  productCard: {
    flex: 1,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  winnerCard: {
    borderColor: '#4CAF50',
    borderWidth: 2,
  },
  winnerBadge: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  winnerBadgeText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: 'bold',
  },
  brandText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  productName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  priceText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 2,
  },
  priceUnavailable: {
    color: '#999',
    fontSize: 14,
  },
  priceNote: {
    fontSize: 10,
    color: '#999',
    fontStyle: 'italic',
  },
  retailerText: {
    fontSize: 11,
    color: '#666',
    marginBottom: 8,
  },
  
  // Rating styles
  ratingContainer: {
    marginVertical: 8,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  ratingText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  reviewCount: {
    fontSize: 12,
    color: '#666',
  },
  noRatingText: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
  },
  noRatingSubtext: {
    fontSize: 10,
    color: '#BBB',
  },
  sourceLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  sourceText: {
    fontSize: 11,
    color: '#2196F3',
    fontWeight: '500',
  },
  verifiedBadge: {
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 3,
    marginRight: 4,
  },
  verifiedBadgeText: {
    fontSize: 9,
    color: '#FFF',
    fontWeight: 'bold',
  },
  
  valueScoreContainer: {
    marginTop: 8,
  },
  valueScoreLabel: {
    fontSize: 11,
    color: '#666',
  },
  valueScoreText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  
  // Sections
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  recommendationSection: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 15,
    borderRadius: 12,
  },
  recommendationText: {
    fontSize: 14,
    color: '#555',
    lineHeight: 22,
  },
  differencesSection: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 15,
    borderRadius: 12,
  },
  differenceItem: {
    fontSize: 13,
    color: '#555',
    marginBottom: 8,
    lineHeight: 20,
  },
  bestForSection: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 15,
    borderRadius: 12,
  },
  bestForGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  bestForItem: {
    backgroundColor: '#F5F5F5',
    padding: 10,
    borderRadius: 8,
    minWidth: '45%',
  },
  bestForCategory: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  bestForWinner: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  metadataSection: {
    padding: 15,
    alignItems: 'center',
  },
  metadataText: {
    fontSize: 11,
    color: '#999',
  },
  
  // Specs tab
  tabContent: {
    padding: 10,
  },
  specsCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
  },
  specsCardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  specsTableHeader: {
    flexDirection: 'row',
    borderBottomWidth: 2,
    borderBottomColor: '#2196F3',
    paddingBottom: 8,
    marginBottom: 4,
  },
  specsTableHeaderLabel: {
    flex: 1,
  },
  specsTableHeaderCell: {
    flex: 1,
    alignItems: 'center',
  },
  specsTableHeaderText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#2196F3',
  },
  specsTableRow: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  specsTableRowAlt: {
    backgroundColor: '#FAFAFA',
  },
  specsTableLabel: {
    flex: 1,
    justifyContent: 'center',
    paddingRight: 4,
  },
  specsTableCell: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 2,
  },
  specKey: {
    fontSize: 12,
    color: '#666',
    textTransform: 'capitalize',
  },
  specValue: {
    fontSize: 12,
    color: '#333',
    fontWeight: '500',
    textAlign: 'center',
  },
  specMissing: {
    fontSize: 12,
    color: '#CCC',
    textAlign: 'center',
  },
  advantagesSection: {
    marginTop: 10,
  },
  advantageCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
  },
  advantageTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  advantageItem: {
    fontSize: 13,
    color: '#4CAF50',
    marginBottom: 4,
  },
  
  // Reviews tab
  reviewCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
  },
  reviewCardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  reviewRatingSection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  prosConsSection: {
    marginBottom: 15,
  },
  prosTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4CAF50',
    marginBottom: 8,
  },
  consTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F44336',
    marginBottom: 8,
  },
  proItem: {
    fontSize: 13,
    color: '#555',
    marginBottom: 4,
    marginLeft: 8,
  },
  conItem: {
    fontSize: 13,
    color: '#555',
    marginBottom: 4,
    marginLeft: 8,
  },
});
