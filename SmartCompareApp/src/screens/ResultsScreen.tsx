/**
 * ResultsScreen - Comparison results with verified ratings
 * Shows "No verified rating available" if rating is null
 * Includes link to source when rating is verified
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Share,
  Linking,
} from 'react-native';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList, Product, Comparison, RatingSource, ComparisonResult, ScoringResult, ProductScores, ScoreBreakdown, PersonalizedInsight } from '../types';
import FeedbackCard from '../components/FeedbackCard';
import { trackEvents } from '../services/api';

type ResultsScreenProps = NativeStackScreenProps<RootStackParamList, 'Results'>;

type TabType = 'overview' | 'specs' | 'reviews';

export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { result } = route.params;
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const { products, comparison, winner_index, recommendation, key_differences, metadata } = result;

  // Event tracking
  const mountTimeRef = useRef(Date.now());
  const pendingEventsRef = useRef<Array<{ event_type: string; event_data?: Record<string, any>; comparison_id?: string }>>([]);
  const comparisonId = metadata?.query;

  const trackEvent = (eventType: string, eventData?: Record<string, any>) => {
    pendingEventsRef.current.push({
      event_type: eventType,
      event_data: eventData,
      comparison_id: comparisonId,
    });
  };

  useEffect(() => {
    return () => {
      // Send view duration + any pending events on unmount (fire-and-forget)
      const durationMs = Date.now() - mountTimeRef.current;
      pendingEventsRef.current.push({
        event_type: 'result_view_duration',
        event_data: { duration_ms: durationMs },
        comparison_id: comparisonId,
      });
      if (pendingEventsRef.current.length > 0) {
        trackEvents(pendingEventsRef.current);
      }
    };
  }, []);

  const handleTabSwitch = (tab: TabType) => {
    if (tab !== activeTab) {
      trackEvent('tab_switch', { from: activeTab, to: tab });
    }
    setActiveTab(tab);
  };

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

  const openRatingSource = (source: RatingSource | null | undefined) => {
    if (source?.url) {
      trackEvent('source_click', { source_name: source.name, url: source.url });
      Linking.openURL(source.url);
    }
  };

  // Scoring helpers
  const scoring = result.scoring;

  const getScoreColor = (score: number): string => {
    if (score > 70) return '#4CAF50';
    if (score >= 40) return '#FF9800';
    return '#F44336';
  };

  const SCORE_LABELS: Record<keyof ScoreBreakdown, string> = {
    price_score: 'Price',
    spec_score: 'Specs',
    review_score: 'Reviews',
    value_score: 'Value',
    reliability_score: 'Reliability',
    popularity_score: 'Popularity',
  };

  // Badge mapping: scoring dimension -> label + icon
  const BADGE_MAP: Record<keyof ScoreBreakdown, { label: string; icon: string }> = {
    price_score: { label: 'Best Price', icon: 'pricetag-outline' },
    spec_score: { label: 'Best Specs', icon: 'hardware-chip-outline' },
    review_score: { label: 'Top Rated', icon: 'star-outline' },
    value_score: { label: 'Best Value', icon: 'trophy-outline' },
    reliability_score: { label: 'Most Reliable', icon: 'shield-checkmark-outline' },
    popularity_score: { label: 'Most Popular', icon: 'trending-up-outline' },
  };

  const BADGE_THRESHOLD = 3;

  const getProductBadges = (index: number): Array<{ label: string; icon: string }> => {
    if (!scoring) return [];
    const myScores = getProductScores(index);
    const otherScores = getProductScores(index === 0 ? 1 : 0);
    if (!myScores || !otherScores) return [];

    const badges: Array<{ label: string; icon: string }> = [];
    for (const [dim, meta] of Object.entries(BADGE_MAP)) {
      const key = dim as keyof ScoreBreakdown;
      if (myScores.breakdown[key] - otherScores.breakdown[key] >= BADGE_THRESHOLD) {
        badges.push(meta);
      }
    }
    return badges;
  };

  const AspectBadges = ({ index }: { index: number }) => {
    const badges = getProductBadges(index);
    const isOverallWinner = scoring && scoring.winner_index === index;
    if (badges.length === 0 && !isOverallWinner) return null;

    return (
      <View style={styles.aspectBadgesRow}>
        {isOverallWinner && (
          <View style={[styles.aspectBadge, styles.overallBadge]}>
            <Ionicons name="ribbon-outline" size={10} color="#FFF" />
            <Text style={styles.overallBadgeText}>
              {result.personalized ? 'Best for You' : 'Best Overall'}
            </Text>
          </View>
        )}
        {badges.map((badge, i) => (
          <View key={i} style={[styles.aspectBadge, isOverallWinner ? styles.winnerAspectBadge : styles.otherAspectBadge]}>
            <Ionicons name={badge.icon as any} size={10} color={isOverallWinner ? '#2E7D32' : '#1565C0'} />
            <Text style={[styles.aspectBadgeText, { color: isOverallWinner ? '#2E7D32' : '#1565C0' }]}>
              {badge.label}
            </Text>
          </View>
        ))}
      </View>
    );
  };

  const getInsightIcon = (focusArea: string): string => {
    const lower = focusArea.toLowerCase();
    if (lower.includes('battery')) return 'battery-charging-outline';
    if (lower.includes('price') || lower.includes('budget') || lower.includes('value')) return 'cash-outline';
    if (lower.includes('camera') || lower.includes('photo')) return 'camera-outline';
    if (lower.includes('durability') || lower.includes('build')) return 'shield-checkmark-outline';
    if (lower.includes('display') || lower.includes('screen')) return 'phone-portrait-outline';
    if (lower.includes('performance') || lower.includes('speed')) return 'speedometer-outline';
    if (lower.includes('storage') || lower.includes('memory')) return 'server-outline';
    return 'information-circle-outline';
  };

  const InsightCard = ({ insight }: { insight: PersonalizedInsight }) => {
    return (
      <View style={styles.insightCard}>
        <View style={styles.insightIconRow}>
          <Ionicons name={getInsightIcon(insight.focus_area) as any} size={20} color="#2196F3" />
          <Text style={styles.insightFocusArea}>
            {insight.focus_area.replace(/_/g, ' ')}
          </Text>
        </View>
        <Text style={styles.insightText}>{insight.insight}</Text>
      </View>
    );
  };

  const PreferencePromptBanner = () => {
    if (result.personalized && result.personalized_insights && result.personalized_insights.length > 0) {
      return null;
    }
    return (
      <TouchableOpacity
        style={styles.preferencePromptBanner}
        onPress={() => navigation.navigate('Preferences', { mode: 'onboarding' })}
      >
        <Ionicons name="person-circle-outline" size={24} color="#2196F3" />
        <View style={styles.preferencePromptTextContainer}>
          <Text style={styles.preferencePromptTitle}>Get personalized guidance</Text>
          <Text style={styles.preferencePromptSubtext}>Set your preferences to see insights tailored to you</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#999" />
      </TouchableOpacity>
    );
  };

  const getProductScores = (index: number): ProductScores | null => {
    if (!scoring) return null;
    const key = `product_${index}`;
    return scoring.scores[key] ?? null;
  };

  // Score badge for product cards
  const ScoreBadge = ({ index }: { index: number }) => {
    const scores = getProductScores(index);
    if (!scores) return null;

    return (
      <View style={[styles.scoreBadge, { borderColor: getScoreColor(scores.overall) }]}>
        <Text style={[styles.scoreBadgeValue, { color: getScoreColor(scores.overall) }]}>
          {Math.round(scores.overall)}
        </Text>
        <Text style={styles.scoreBadgeLabel}>/100</Text>
      </View>
    );
  };

  // Score breakdown bar
  const ScoreBar = ({ label, value }: { label: string; value: number }) => (
    <View style={styles.scoreBarRow}>
      <Text style={styles.scoreBarLabel}>{label}</Text>
      <View style={styles.scoreBarTrack}>
        <View
          style={[
            styles.scoreBarFill,
            { width: `${Math.min(value, 100)}%`, backgroundColor: getScoreColor(value) },
          ]}
        />
      </View>
      <Text style={styles.scoreBarValue}>{Math.round(value)}</Text>
    </View>
  );

  // Full scoring section in overview
  const ScoringSection = () => {
    if (!scoring) return null;

    const winnerScores = getProductScores(scoring.winner_index);
    const winnerName = products[scoring.winner_index]?.name;

    return (
      <View style={styles.scoringSection}>
        <Text style={styles.sectionTitle}>Score Breakdown</Text>

        {scoring.win_margin > 0 && winnerName && (
          <View style={styles.winMarginBanner}>
            <Text style={styles.winMarginText}>
              {winnerName} wins by {Math.round(scoring.win_margin)} points
            </Text>
          </View>
        )}

        {products.map((product, index) => {
          const scores = getProductScores(index);
          if (!scores) return null;

          return (
            <View key={index} style={styles.scoreCard}>
              <View style={styles.scoreCardHeader}>
                <Text style={styles.scoreCardName}>{product.name}</Text>
                <View style={[styles.scoreOverallBadge, { backgroundColor: getScoreColor(scores.overall) }]}>
                  <Text style={styles.scoreOverallText}>{Math.round(scores.overall)}/100</Text>
                </View>
              </View>
              {(Object.keys(SCORE_LABELS) as (keyof ScoreBreakdown)[]).map((key) => (
                <ScoreBar key={key} label={SCORE_LABELS[key]} value={scores.breakdown[key]} />
              ))}
            </View>
          );
        })}

        {/* Weights info */}
        {winnerScores && (
          <Text style={styles.weightsText}>
            {scoring.scoring_method === 'personalized'
              ? 'Weighted for your preferences'
              : 'Default weights applied'}
          </Text>
        )}
      </View>
    );
  };

  // Rating display component — shows all ratings with source name + link
  const RatingDisplay = ({ product }: { product: Product }) => {
    const { rating, review_count, rating_source } = product;

    if (rating === null || rating === undefined) {
      return (
        <View style={styles.ratingContainer}>
          <Text style={styles.noRatingText}>No rating available</Text>
        </View>
      );
    }

    const hasLink = rating_source?.url != null;

    const ratingContent = (
      <>
        <View style={styles.ratingRow}>
          <Text style={styles.ratingText}>{rating.toFixed(1)}/5</Text>
          {review_count != null && (
            <Text style={styles.reviewCountText}>({review_count.toLocaleString()} reviews)</Text>
          )}
        </View>
        {rating_source?.name && (
          <View style={styles.sourceLink}>
            <Text style={styles.sourceText}>{rating_source.name}</Text>
            {hasLink && <Ionicons name="open-outline" size={12} color="#2196F3" />}
          </View>
        )}
      </>
    );

    if (hasLink) {
      return (
        <TouchableOpacity
          onPress={() => openRatingSource(rating_source!)}
          style={styles.ratingContainer}
        >
          {ratingContent}
        </TouchableOpacity>
      );
    }

    return <View style={styles.ratingContainer}>{ratingContent}</View>;
  };

  // Product card component
  const ProductCard = ({ product, index }: { product: Product; index: number }) => {
    const isWinner = index === winner_index;
    const valueScore = comparison.value_scores?.[index];

    return (
      <View style={[styles.productCard, isWinner && styles.winnerCard]}>
        <AspectBadges index={index} />

        {/* Score Badge */}
        <ScoreBadge index={index} />

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

  // Specs comparison tab
  const SpecsTab = () => (
    <View style={styles.tabContent}>
      {products.map((product, index) => (
        <View key={index} style={styles.specsCard}>
          <Text style={styles.specsCardTitle}>{product.name}</Text>
          {product.specs && Object.entries(product.specs).map(([key, value]) => (
            value && (
              <View key={key} style={styles.specRow}>
                <Text style={styles.specKey}>{key.replace(/_/g, ' ')}</Text>
                <Text style={styles.specValue}>{String(value)}</Text>
              </View>
            )
          ))}
        </View>
      ))}
      
      {/* Advantages comparison */}
      {comparison.specs_comparison && (
        <View style={styles.advantagesSection}>
          <Text style={styles.sectionTitle}>Advantages</Text>
          
          {comparison.specs_comparison.product_0_advantages?.length > 0 && (
            <View style={styles.advantageCard}>
              <Text style={styles.advantageTitle}>{products[0]?.name}</Text>
              {comparison.specs_comparison.product_0_advantages.map((adv, i) => (
                <Text key={i} style={styles.advantageItem}>✓ {adv}</Text>
              ))}
            </View>
          )}
          
          {comparison.specs_comparison.product_1_advantages?.length > 0 && (
            <View style={styles.advantageCard}>
              <Text style={styles.advantageTitle}>{products[1]?.name}</Text>
              {comparison.specs_comparison.product_1_advantages.map((adv, i) => (
                <Text key={i} style={styles.advantageItem}>✓ {adv}</Text>
              ))}
            </View>
          )}
        </View>
      )}
    </View>
  );

  // Reviews tab (pros/cons)
  const ReviewsTab = () => {
    const hasAnyReviews = products.some(p =>
      (p.pros && p.pros.length > 0) ||
      (p.cons && p.cons.length > 0) ||
      p.rating ||
      (p.reviews?.common_praises && p.reviews.common_praises.length > 0) ||
      (p.reviews?.common_complaints && p.reviews.common_complaints.length > 0) ||
      (p.reviews?.average_rating != null) ||
      (p.reviews?.detailed_praises && p.reviews.detailed_praises.length > 0)
    );

    if (!hasAnyReviews) {
      return (
        <View style={styles.tabContent}>
          <View style={styles.emptyStateCard}>
            <Ionicons name="chatbubble-ellipses-outline" size={40} color="#CCC" />
            <Text style={styles.emptyStateText}>Reviews not available for these products</Text>
          </View>
        </View>
      );
    }

    return (
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

            {/* Common Praises (when no pros available) */}
            {(!product.pros || product.pros.length === 0) && product.reviews?.common_praises && product.reviews.common_praises.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.prosTitle}>Praised For</Text>
                {product.reviews.common_praises.map((praise: string, i: number) => (
                  <Text key={i} style={styles.proItem}>• {praise}</Text>
                ))}
              </View>
            )}

            {/* Common Complaints (when no cons available) */}
            {(!product.cons || product.cons.length === 0) && product.reviews?.common_complaints && product.reviews.common_complaints.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.consTitle}>Criticized For</Text>
                {product.reviews.common_complaints.map((complaint: string, i: number) => (
                  <Text key={i} style={styles.conItem}>• {complaint}</Text>
                ))}
              </View>
            )}

            {/* Detailed praises with user quotes */}
            {product.reviews?.detailed_praises && product.reviews.detailed_praises.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.prosTitle}>What Users Love</Text>
                {product.reviews.detailed_praises.map((praise: any, i: number) => (
                  <View key={i}>
                    <Text style={styles.proItem}>• {praise.text}</Text>
                    {praise.quote && (
                      <Text style={[styles.proItem, { fontStyle: 'italic', color: '#666', marginLeft: 16 }]}>
                        "{praise.quote}"
                      </Text>
                    )}
                  </View>
                ))}
              </View>
            )}
          </View>
        ))}
      </View>
    );
  };

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
            onPress={() => handleTabSwitch(tab)}
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

            {/* Personalized Insight Cards (or preference prompt) */}
            {result.personalized_insights && result.personalized_insights.length > 0 ? (
              <View style={styles.insightsSection}>
                {result.personalized_insights.map((insight, index) => (
                  <InsightCard key={index} insight={insight} />
                ))}
              </View>
            ) : (
              <PreferencePromptBanner />
            )}

            {/* Scores */}
            <ScoringSection />

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
                  Comparison took {metadata.elapsed_seconds?.toFixed(1)}s •{' '}
                  {(metadata.cache_hits ?? 0) > 0 ? `${metadata.cache_hits} cached` : 'Fresh data'}
                </Text>
              </View>
            )}

            {/* Feedback */}
            <FeedbackCard comparisonId={comparisonId} />
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
  reviewCountText: {
    fontSize: 12,
    color: '#666',
  },
  noRatingText: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
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
  specRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  specKey: {
    fontSize: 13,
    color: '#666',
    textTransform: 'capitalize',
  },
  specValue: {
    fontSize: 13,
    color: '#333',
    fontWeight: '500',
    maxWidth: '60%',
    textAlign: 'right',
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

  // Scoring styles
  scoreBadge: {
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    flexDirection: 'row',
    alignItems: 'baseline',
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  scoreBadgeValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  scoreBadgeLabel: {
    fontSize: 11,
    color: '#999',
    marginLeft: 1,
  },
  scoringSection: {
    backgroundColor: '#FFF',
    margin: 10,
    padding: 15,
    borderRadius: 12,
  },
  winMarginBanner: {
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
    alignItems: 'center',
  },
  winMarginText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2E7D32',
  },
  scoreCard: {
    backgroundColor: '#FAFAFA',
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  scoreCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  scoreCardName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  scoreOverallBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  scoreOverallText: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#FFF',
  },
  scoreBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  scoreBarLabel: {
    fontSize: 11,
    color: '#666',
    width: 70,
  },
  scoreBarTrack: {
    flex: 1,
    height: 6,
    backgroundColor: '#E0E0E0',
    borderRadius: 3,
    marginHorizontal: 8,
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  scoreBarValue: {
    fontSize: 11,
    fontWeight: '600',
    color: '#333',
    width: 24,
    textAlign: 'right',
  },
  weightsText: {
    fontSize: 11,
    color: '#999',
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: 4,
  },
  // Aspect badges
  aspectBadgesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginBottom: 8,
  },
  aspectBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    gap: 3,
  },
  overallBadge: {
    backgroundColor: '#4CAF50',
  },
  overallBadgeText: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#FFF',
  },
  winnerAspectBadge: {
    backgroundColor: '#E8F5E9',
  },
  otherAspectBadge: {
    backgroundColor: '#E3F2FD',
  },
  aspectBadgeText: {
    fontSize: 9,
    fontWeight: '600',
  },
  // Insight cards
  insightsSection: {
    paddingHorizontal: 10,
    marginBottom: 5,
  },
  insightCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#2196F3',
  },
  insightIconRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  insightFocusArea: {
    fontSize: 12,
    fontWeight: '600',
    color: '#2196F3',
    textTransform: 'capitalize',
  },
  insightText: {
    fontSize: 13,
    color: '#555',
    lineHeight: 20,
  },
  // Preference prompt banner
  preferencePromptBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    marginHorizontal: 10,
    marginBottom: 5,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E3F2FD',
    gap: 10,
  },
  preferencePromptTextContainer: {
    flex: 1,
  },
  preferencePromptTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  preferencePromptSubtext: {
    fontSize: 11,
    color: '#999',
    marginTop: 2,
  },
  // Empty states
  emptyStateCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 30,
    alignItems: 'center',
    justifyContent: 'center',
    margin: 10,
  },
  emptyStateText: {
    fontSize: 14,
    color: '#999',
    marginTop: 10,
    textAlign: 'center',
  },
});

