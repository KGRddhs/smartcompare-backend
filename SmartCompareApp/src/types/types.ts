/**
 * SmartCompare - TypeScript Types
 */

export interface Product {
  brand: string;
  name: string;
  size?: string;
  price?: number;
  currency?: string;
  source?: 'live' | 'cached' | 'estimated';
  confidence?: string;
  retailer?: string;
  note?: string;
}

export interface ComparisonResult {
  success: boolean;
  products: Product[];
  winner_index: number;
  recommendation: string;
  key_differences: string[];
  total_cost: number;
  data_freshness: 'live' | 'cached' | 'mixed' | 'estimated';
  errors?: string[];
}

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

export interface CapturedImage {
  uri: string;
  base64?: string;
  width: number;
  height: number;
}

// Auth types
export interface User {
  id: string;
  email: string;
  subscription_tier?: 'free' | 'premium';
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
}

// Navigation types
export type RootStackParamList = {
  Home: undefined;
  Camera: undefined;
  Results: { result: ComparisonResult };
  History: undefined;
  Profile: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};
