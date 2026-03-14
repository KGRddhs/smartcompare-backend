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
  source_method?: 'local_bhd' | 'converted_usd' | 'estimated';
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

export interface ScoringResult {
  scores: Record<string, ProductScores>;
  winner_index: number;
  win_margin: number;
  scoring_method: 'personalized' | 'default';
}

// --- Rate limiting & subscription ---

export interface RateLimitStatus {
  allowed: boolean;
  current_usage: number;
  daily_limit: number | null;
  remaining: number | null;
}

export interface SubscriptionStatus {
  user_id: string;
  email: string;
  subscription_tier: 'free' | 'premium';
  daily_usage: number;
  daily_limit: number | null;
  remaining_comparisons: number | null;
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

export interface UserPreferences {
  priorities: string[];
  budget: 'budget' | 'mid' | 'premium';
  lifestyle: string[];
  brand_attitude: 'brand_loyal' | 'function_first' | 'best_of_both';
}

// --- Auth types ---

export interface User {
  id: string;
  email: string;
  subscription_tier?: 'free' | 'premium';
  preferences_completed?: boolean;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
}

// --- Navigation types ---

export type RootStackParamList = {
  Home: undefined;
  Camera: undefined;
  Results: { result: ComparisonResult };
  History: undefined;
  Profile: undefined;
  Account: undefined;
  Preferences: { mode: 'onboarding' | 'edit' };
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};
