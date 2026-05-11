/**
 * SmartCompare - TypeScript Types
 * Matches backend API response schema (verified Feb 14, 2026)
 */

// --- Product & Review types ---

export interface RatingSource {
  name: string;
  url: string | null;
  retrieved_at?: string;
  extract_method?: 'google_shopping' | 'json_ld' | 'microdata' | 'meta_tags' | 'css_selector' | 'gpt_review_aggregate';
  confidence?: 'high' | 'medium' | 'low' | 'expert';
}

export interface ReviewData {
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
  verified_rating?: {
    rating: number;
    review_count?: number | null;
    source?: string | null;
    verified?: boolean;
  } | null;
}

export interface ProductPrice {
  amount: number | null;
  currency: string;
  retailer?: string;
  url?: string;
  in_stock?: boolean;
  estimated?: boolean;
  confidence?: number;
  note?: string;
  unavailable?: boolean;
  source_method?: 'local_bhd' | 'converted_usd' | 'estimated' | 'page_scrape' | 'page_scrape_rendered';
}

export interface Product {
  brand: string;
  name: string;
  full_name?: string;
  variant?: string | null;
  category?: string;
  query?: string;
  specs?: Record<string, any>;
  price?: ProductPrice;
  best_price?: number;
  currency?: string;
  retailer?: string;
  reviews?: ReviewData | null;
  rating?: number | null;
  review_count?: number | null;
  rating_verified?: boolean;
  rating_source?: RatingSource | null;
  pros?: string[];
  cons?: string[];
  expert_pros?: string[];
  expert_cons?: string[];
  confidence?: number;
  data_freshness?: string;
  pros_cons?: { pros: string[]; cons: string[] };
}

// --- Comparison types ---

export interface Comparison {
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
    similar_features?: string[];
    similar?: string[];
  };
}

export interface PersonalizedInsight {
  focus_area: string;
  product_index: number;
  insight: string;
}

// --- New structured response types (Session 29) ---

export interface OverviewWinner {
  product_index: number;
  name: string;
  declaration: string;
  reason: string;
  key_tradeoff: string;
  margin: number;
}

export interface OverviewProduct {
  brand: string;
  name: string;
  price: ProductPrice;
  rating: number | null;
  review_count: number | null;
  overall_score: number | null;
  value_badge: 'great_value' | 'fair_price' | 'premium_price' | 'overpriced';
  value_context: string;
  pros: string[];
  cons: string[];
  best_for: string;
}

export interface TradeoffDimension {
  dimension: string;
  product: string;
  margin: number;
}

export interface TradeoffPair {
  winner_wins: TradeoffDimension;
  loser_wins: TradeoffDimension;
}

export interface ConfidenceIndicators {
  price: { source_count: number; method: string; freshness: string };
  rating: { review_count: number; source: string; verified: boolean };
  specs: { verified_pct: number; citation_count: number };
  overall: 'high' | 'medium' | 'low';
}

export interface OverviewSection {
  winner: OverviewWinner;
  products: OverviewProduct[];
  tradeoffs: TradeoffPair[];
  confidence: ConfidenceIndicators;
}

export interface SpecsProduct {
  brand: string;
  name: string;
  specs: Record<string, any>;
  spec_advantages: string[];
}

export interface SpecsSection {
  products: SpecsProduct[];
  specs_comparison: Record<string, any>;
}

export interface ReviewHighlight {
  point: string;
  sentiment: 'positive' | 'negative';
}

export interface ReviewSummary {
  overall_sentiment: 'positive' | 'mixed' | 'negative';
  consensus: string;
  highlights: ReviewHighlight[];
  review_volume: 'high' | 'moderate' | 'low' | 'minimal';
  agreement_level: 'strong' | 'moderate' | 'divided';
}

export interface ReviewProduct {
  brand: string;
  name: string;
  rating: number | null;
  review_count: number | null;
  rating_source: RatingSource | null;
  review_summary: ReviewSummary;
}

export interface ReviewsSection {
  products: ReviewProduct[];
}

export interface ScoringSection {
  scores: Record<string, ProductScores>;
  dimension_winners: Record<string, DimensionWinner>;
  price_tiers: Record<string, string>;
  is_cross_tier: boolean;
  scoring_method: 'category_weighted' | 'personalized';
  category_weights: Record<string, number>;
}

export interface PersonalizationSection {
  personalized: boolean;
  factors: string[];
  personalized_insights: PersonalizedInsight[];
}

export interface MetadataSection {
  query: string;
  region: string;
  elapsed_ms: number;
  elapsed_seconds: number;
  api_calls: number;
  total_cost: number;
  gpt_calls: number;
  serper_calls: number;
  cached: boolean;
  fact_check: Record<string, any>;
  timestamp: string;
}

export interface ComparisonResult {
  success: boolean;
  products: Product[];
  comparison: Comparison;
  winner_index: number;
  recommendation: string;
  key_differences: string[];
  category_used?: string;
  category_switched?: boolean;
  original_category?: string;
  personalized?: boolean;
  personalization_factors?: string[];
  personalized_insights?: PersonalizedInsight[];
  scoring?: ScoringResult;
  metadata?: {
    query: string;
    region: string;
    elapsed_seconds: number;
    total_cost: number;
    api_calls: number;
    cache_hits?: number;
    timestamp: string;
  };
  error?: string;
  // New structured response fields (optional for backward compat with history)
  overview?: OverviewSection;
  specs?: SpecsSection;
  reviews?: ReviewsSection;
  personalization?: PersonalizationSection;
}

// --- Scoring types ---

export interface ScoreBreakdown {
  price_score: number;
  spec_score: number;
  review_score: number;
  value_score: number;
  reliability_score: number;
  popularity_score: number;
}

export interface ProductScores {
  overall: number;
  breakdown: ScoreBreakdown;
  weights_used: Record<string, number>;
}

export interface DimensionWinner {
  winner: string;
  margin: number | null;
}

export interface ScoringResult {
  scores: Record<string, ProductScores>;
  winner_index: number;
  win_margin: number;
  scoring_method: 'personalized' | 'default' | 'category_weighted';
  dimension_winners?: Record<string, DimensionWinner>;
  price_tiers?: Record<string, string>;
  is_cross_tier?: boolean;
  category_weights?: Record<string, number>;
}

// --- Camera ---

export interface CapturedImage {
  uri: string;
  base64?: string;
  width: number;
  height: number;
}

export interface IdentifiedProduct {
  brand: string;
  name: string;
  visible_price?: string | null;
  confidence: 'high' | 'medium' | 'low';
}

export type ImageIdentifyResult =
  | {
      success: true;
      action: 'comparison';
      products: Product[];
      comparison: Comparison;
      winner_index: number;
      recommendation: string;
      key_differences: string[];
      metadata?: ComparisonResult['metadata'] & {
        input_method: 'camera';
        vision_cost: number;
        identified_products: IdentifiedProduct[];
      };
    }
  | {
      success: true;
      action: 'need_second_product';
      products: IdentifiedProduct[];
      message: string;
      vision_cost: number;
    }
  | {
      success: false;
      action: 'error' | 'comparison_failed';
      error: string;
      products?: IdentifiedProduct[];
      vision_cost?: number;
      message?: string;
    };

// --- Preferences ---

export interface NotificationTypes {
  decision_insight?: boolean;
  cohort_curiosity?: boolean;
  decision_retrospective?: boolean;
}

export interface UserPreferences {
  priorities: string[];
  budget: 'budget' | 'mid' | 'premium';
  lifestyle: string[];
  brand_attitude: 'brand_loyal' | 'function_first' | 'best_of_both';
  ai_sharing_enabled?: boolean;
  // F5.4 — re-engagement notification preferences. Master + 3 sub-toggles.
  // Missing keys default to ON server-side (matches re-engagement-cron
  // eligibility filter from design 9.2).
  notifications_enabled?: boolean;
  notification_types?: NotificationTypes;
}

// --- Auth types ---

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
}

// --- Navigation types ---

// Root stack with Auth, Onboarding, Main tabs, Results modal, and Referral
// landing flow (auth-OPTIONAL, reachable from deep links pre-auth).
export type RootStackParamList = {
  Auth: undefined;
  // mode='edit' opens preferences in edit mode (e.g. from Profile screen).
  // source='styleProfile' signals an "inferred preferences" banner is appropriate.
  Onboarding: { mode?: 'edit'; source?: 'styleProfile' } | undefined;
  Main: undefined;
  Results: { result: ComparisonResult };
  // F3.2/F3.3 — invitee landing flow (gradual commitment, no signup gate).
  ReferralLanding: { share_token: string; ref: string };
  InviteeQuiz: { share_token: string; invite_id: string; ref: string };
  // Legacy screen names for backward compatibility with screen components
  Home: undefined;
  History: undefined;
  Profile: undefined;
};

// Auth stack for login flow
export type AuthStackParamList = {
  Login: undefined;
  // invite_id is set when the user lands on Register from the invitee
  // quiz soft-signup CTA (F3.5) — forwarded to /auth/register so the
  // backend links redeemed_by_user_id on the pending referral invite.
  // `code` arrives via deep link (qaren://redeem?code=QR-XXXXXX or
  // qaren.app/r/QR-XXXXXX) and pre-fills the invite-code field on Register.
  Register: { invite_id?: string; code?: string } | undefined;
  ForgotPassword: undefined;
};

// Main tabs (inside Main screen)
export type MainTabParamList = {
  HomeTab: undefined;
  HistoryTab: undefined;
  ProfileTab: undefined;
};

// --- Onboarding types ---

export interface OnboardingData {
  language: 'en' | 'ar';
  region: 'bahrain' | 'saudi_arabia' | 'uae' | 'kuwait' | 'qatar' | 'oman';
  priorities: string[];
  budget: 'budget' | 'mid' | 'premium';
  lifestyle: string[];
  brand_attitude: 'brand_loyal' | 'function_first' | 'best_of_both';
}
