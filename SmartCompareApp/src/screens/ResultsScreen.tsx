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

interface ReviewData {
  average_rating?: number | null;
  total_reviews?: number | null;
  positive_percentage?: number | null;
  summary?: string | null;
  rating_distribution?: Record<string, number> | null;
  category_scores?: Record<string, number> | null;
  source_ratings?: Array<{ source: string; rating: number; review_count?: number | null }>;
  detailed_praises?: Array<{ text: string; frequency?: string; quote?: string }>;
  detailed_complaints?: Array<{ text: string; frequency?: string; quote?: string }>;
  user_quotes?: Array<{ text: string; sentiment?: string; source?: string; aspect?: string }>;
  common_praises?: string[];
  common_complaints?: string[];
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
  reviews?: ReviewData | null;
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

// Fixed display order and labels for spec keys
const SPEC_DISPLAY_CONFIG: Record<string, { label: string; order: number }> = {
  // Electronics
  display: { label: 'Display', order: 1 },
  processor: { label: 'Processor', order: 2 },
  ram: { label: 'RAM', order: 3 },
  storage: { label: 'Storage', order: 4 },
  battery: { label: 'Battery', order: 5 },
  rear_camera: { label: 'Rear Camera', order: 6 },
  front_camera: { label: 'Front Camera', order: 7 },
  os: { label: 'OS', order: 8 },
  connectivity: { label: 'Connectivity', order: 9 },
  weight: { label: 'Weight', order: 10 },
  water_resistance: { label: 'Water Resistance', order: 11 },
  // Grocery
  size: { label: 'Size', order: 1 },
  ingredients: { label: 'Ingredients', order: 2 },
  nutrition_calories: { label: 'Calories', order: 3 },
  nutrition_protein: { label: 'Protein', order: 4 },
  nutrition_fat: { label: 'Fat', order: 5 },
  nutrition_carbs: { label: 'Carbs', order: 6 },
  origin: { label: 'Origin', order: 7 },
  organic: { label: 'Organic', order: 8 },
  allergens: { label: 'Allergens', order: 9 },
  shelf_life: { label: 'Shelf Life', order: 10 },
  halal: { label: 'Halal', order: 11 },
  // Other
  dimensions: { label: 'Dimensions', order: 1 },
  material: { label: 'Material', order: 3 },
  color: { label: 'Color', order: 4 },
  warranty: { label: 'Warranty', order: 5 },
  power: { label: 'Power', order: 6 },
  features: { label: 'Features', order: 7 },
  included: { label: 'Included', order: 8 },
  compatibility: { label: 'Compatibility', order: 9 },
  certifications: { label: 'Certifications', order: 11 },
};

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
          <Text style={styles.priceNote}>*Estimated price</Text>
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

  // Specs comparison tab - unified table with fixed order
  const SpecsTab = () => {
    // Merge all spec keys from both products
    const allKeysSet = new Set<string>();
    products.forEach((product) => {
      if (product.specs) {
        Object.keys(product.specs).forEach((key) => allKeysSet.add(key));
      }
    });

    // Sort keys by SPEC_DISPLAY_CONFIG order; unknown keys go to the end
    const sortedKeys = Array.from(allKeysSet)
      .sort((a, b) => {
        const orderA = SPEC_DISPLAY_CONFIG[a]?.order ?? 999;
        const orderB = SPEC_DISPLAY_CONFIG[b]?.order ?? 999;
        return orderA - orderB;
      })
      // Only show rows where BOTH products have real data
      .filter((key) => {
        const val0 = products[0]?.specs?.[key];
        const val1 = products[1]?.specs?.[key];
        const isNA = (v: any) => !v || v === 'N/A' || v === '-';
        return !isNA(val0) && !isNA(val1);
      });

    const getLabel = (key: string) =>
      SPEC_DISPLAY_CONFIG[key]?.label ?? key.replace(/_/g, ' ');

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
          {sortedKeys.map((key, rowIndex) => (
            <View
              key={key}
              style={[
                styles.specsTableRow,
                rowIndex % 2 === 0 && styles.specsTableRowAlt,
              ]}
            >
              <View style={styles.specsTableLabel}>
                <Text style={styles.specKey}>{getLabel(key)}</Text>
              </View>
              {products.map((product, colIndex) => {
                const val = product.specs?.[key];
                const isNA = !val || val === 'N/A' || val === '-';
                return (
                  <View key={colIndex} style={styles.specsTableCell}>
                    <Text style={isNA ? styles.specNA : styles.specValue}>
                      {isNA ? 'N/A' : String(val)}
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

  // Score bar for category scores
  const ScoreBar = ({ label, score }: { label: string; score: number }) => (
    <View style={styles.scoreBarRow}>
      <Text style={styles.scoreBarLabel}>{label}</Text>
      <View style={styles.scoreBarTrack}>
        <View style={[styles.scoreBarFill, { width: `${Math.min(score * 10, 100)}%` }]} />
      </View>
      <Text style={styles.scoreBarValue}>{score}/10</Text>
    </View>
  );

  // Star distribution bar
  const StarBar = ({ stars, pct }: { stars: string; pct: number }) => (
    <View style={styles.starBarRow}>
      <Text style={styles.starBarLabel}>{stars.replace('_star', '')}</Text>
      <Ionicons name="star" size={10} color="#FFD700" />
      <View style={styles.starBarTrack}>
        <View style={[styles.starBarFill, { width: `${Math.min(pct, 100)}%` }]} />
      </View>
      <Text style={styles.starBarPct}>{Math.round(pct)}%</Text>
    </View>
  );

  // Reviews tab — full enhanced layout
  const ReviewsTab = () => (
    <View style={styles.tabContent}>
      {products.map((product, index) => {
        const reviews = product.reviews;
        return (
          <View key={index} style={styles.reviewCard}>
            <Text style={styles.reviewCardTitle}>{product.name}</Text>

            {/* Rating info */}
            <View style={styles.reviewRatingSection}>
              <RatingDisplay product={product} />
            </View>

            {/* Summary */}
            {reviews?.summary ? (
              <View style={styles.reviewSummarySection}>
                <Text style={styles.reviewSummaryText}>{reviews.summary}</Text>
              </View>
            ) : null}

            {/* Category Scores */}
            {reviews?.category_scores && Object.keys(reviews.category_scores).length > 0 ? (
              <View style={styles.categoryScoresSection}>
                <Text style={styles.reviewSubTitle}>Category Scores</Text>
                {Object.entries(reviews.category_scores)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cat, score]) => (
                    <ScoreBar
                      key={cat}
                      label={cat.replace(/_/g, ' ')}
                      score={typeof score === 'number' ? score : 0}
                    />
                  ))}
              </View>
            ) : null}

            {/* Rating Distribution */}
            {reviews?.rating_distribution && Object.keys(reviews.rating_distribution).length > 0 ? (
              <View style={styles.ratingDistSection}>
                <Text style={styles.reviewSubTitle}>Rating Breakdown</Text>
                {['5_star', '4_star', '3_star', '2_star', '1_star'].map((key) => {
                  const pct = reviews.rating_distribution?.[key];
                  return pct !== undefined ? (
                    <StarBar key={key} stars={key} pct={pct} />
                  ) : null;
                })}
              </View>
            ) : null}

            {/* Source Ratings */}
            {reviews?.source_ratings && reviews.source_ratings.length > 0 ? (
              <View style={styles.sourceRatingsSection}>
                <Text style={styles.reviewSubTitle}>Ratings by Source</Text>
                {reviews.source_ratings.map((sr, i) => (
                  <View key={i} style={styles.sourceRatingRow}>
                    <Text style={styles.sourceRatingName}>{sr.source}</Text>
                    <View style={styles.sourceRatingRight}>
                      <Ionicons name="star" size={12} color="#FFD700" />
                      <Text style={styles.sourceRatingVal}>{sr.rating}</Text>
                      {sr.review_count ? (
                        <Text style={styles.sourceRatingCount}>
                          ({sr.review_count.toLocaleString()})
                        </Text>
                      ) : null}
                    </View>
                  </View>
                ))}
              </View>
            ) : null}

            {/* User Quotes */}
            {reviews?.user_quotes && reviews.user_quotes.length > 0 ? (
              <View style={styles.userQuotesSection}>
                <Text style={styles.reviewSubTitle}>What Users Say</Text>
                {reviews.user_quotes.map((q, i) => (
                  <View key={i} style={styles.quoteCard}>
                    <Text style={styles.quoteText}>"{q.text}"</Text>
                    <View style={styles.quoteMeta}>
                      {q.sentiment ? (
                        <View style={[
                          styles.sentimentBadge,
                          { backgroundColor: q.sentiment === 'positive' ? '#E8F5E9' : q.sentiment === 'negative' ? '#FFEBEE' : '#FFF3E0' }
                        ]}>
                          <Text style={[
                            styles.sentimentText,
                            { color: q.sentiment === 'positive' ? '#4CAF50' : q.sentiment === 'negative' ? '#F44336' : '#FF9800' }
                          ]}>
                            {q.sentiment}
                          </Text>
                        </View>
                      ) : null}
                      {q.source ? <Text style={styles.quoteSource}>{q.source}</Text> : null}
                      {q.aspect ? <Text style={styles.quoteAspect}>{q.aspect}</Text> : null}
                    </View>
                  </View>
                ))}
              </View>
            ) : null}

            {/* Pros */}
            {product.pros && product.pros.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.prosTitle}>Pros</Text>
                {product.pros.map((pro, i) => (
                  <Text key={i} style={styles.proItem}>+ {pro}</Text>
                ))}
              </View>
            )}

            {/* Cons */}
            {product.cons && product.cons.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.consTitle}>Cons</Text>
                {product.cons.map((con, i) => (
                  <Text key={i} style={styles.conItem}>- {con}</Text>
                ))}
              </View>
            )}
          </View>
        );
      })}
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
  specNA: {
    fontSize: 12,
    color: '#BDBDBD',
    textAlign: 'center',
    fontStyle: 'italic',
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
  reviewSummarySection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  reviewSummaryText: {
    fontSize: 14,
    color: '#444',
    lineHeight: 22,
    fontStyle: 'italic',
  },
  reviewSubTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },

  // Category scores
  categoryScoresSection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  scoreBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  scoreBarLabel: {
    width: 90,
    fontSize: 12,
    color: '#666',
    textTransform: 'capitalize',
  },
  scoreBarTrack: {
    flex: 1,
    height: 8,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    backgroundColor: '#2196F3',
    borderRadius: 4,
  },
  scoreBarValue: {
    width: 40,
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
    textAlign: 'right',
  },

  // Rating distribution
  ratingDistSection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  starBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  starBarLabel: {
    width: 14,
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textAlign: 'right',
    marginRight: 2,
  },
  starBarTrack: {
    flex: 1,
    height: 8,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  starBarFill: {
    height: '100%',
    backgroundColor: '#FFD700',
    borderRadius: 4,
  },
  starBarPct: {
    width: 36,
    fontSize: 11,
    color: '#999',
    textAlign: 'right',
  },

  // Source ratings
  sourceRatingsSection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  sourceRatingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#FAFAFA',
  },
  sourceRatingName: {
    fontSize: 13,
    color: '#555',
    flex: 1,
  },
  sourceRatingRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  sourceRatingVal: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  sourceRatingCount: {
    fontSize: 11,
    color: '#999',
  },

  // User quotes
  userQuotesSection: {
    marginBottom: 15,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  quoteCard: {
    backgroundColor: '#F9F9F9',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#2196F3',
  },
  quoteText: {
    fontSize: 13,
    color: '#444',
    lineHeight: 20,
    fontStyle: 'italic',
  },
  quoteMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
  },
  sentimentBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  sentimentText: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  quoteSource: {
    fontSize: 11,
    color: '#999',
  },
  quoteAspect: {
    fontSize: 11,
    color: '#2196F3',
  },

  // Pros/cons
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
    color: '#4CAF50',
    marginBottom: 4,
    marginLeft: 8,
  },
  conItem: {
    fontSize: 13,
    color: '#F44336',
    marginBottom: 4,
    marginLeft: 8,
  },
});
