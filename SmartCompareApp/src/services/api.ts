/**
 * SmartCompare - API Service
 * Connects to the FastAPI backend (with iOS fixes)
 */

import axios from 'axios';
import { ComparisonResult, RateLimitStatus, SubscriptionStatus } from '../types';

// IMPORTANT: Change this to your computer's local IP
// Find your IP: ipconfig (Windows) or ifconfig (Mac/Linux)
const API_BASE_URL = 'http://192.168.100.13:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for image processing
});

/**
 * Compare products from images (iOS & Android compatible)
 */
export async function compareProducts(
  imageUris: string[],
  country: string = 'Bahrain'
): Promise<ComparisonResult> {
  
  console.log('=== COMPARE PRODUCTS ===');
  console.log('Image URIs:', imageUris);
  
  const formData = new FormData();

  // Add images to form data
  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];
    console.log(`Processing image ${i + 1}: ${uri}`);
    
    // Get file name and extension
    const uriParts = uri.split('/');
    let fileName = uriParts[uriParts.length - 1];
    
    // Handle iOS photo library URIs
    if (uri.includes('ph://')) {
      fileName = `photo_${i + 1}.jpg`;
    }
    
    // Get extension
    const extensionMatch = fileName.match(/\.([^.]+)$/);
    let extension = extensionMatch ? extensionMatch[1].toLowerCase() : 'jpg';
    
    // Normalize extension
    if (extension === 'jpeg') extension = 'jpg';
    if (extension === 'heic' || extension === 'heif') extension = 'jpg';
    
    // Determine MIME type
    let mimeType = 'image/jpeg';
    if (extension === 'png') {
      mimeType = 'image/png';
    } else if (extension === 'webp') {
      mimeType = 'image/webp';
    }
    
    const finalFileName = `product_${i + 1}.${extension}`;
    
    console.log(`  -> filename: ${finalFileName}, type: ${mimeType}`);
    
    // Append to form data (React Native style)
    formData.append('images', {
      uri: uri,
      type: mimeType,
      name: finalFileName,
    } as any);
  }

  console.log('Sending request to:', `${API_BASE_URL}/api/v1/compare`);
  
  try {
    const response = await api.post<ComparisonResult>(
      `/api/v1/compare?country=${encodeURIComponent(country)}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        transformRequest: (data) => data, // Don't transform FormData
      }
    );
    
    console.log('Response status:', response.status);
    console.log('Response data:', JSON.stringify(response.data, null, 2));
    
    return response.data;
  } catch (error: any) {
    console.log('=== REQUEST ERROR ===');
    console.log('Error message:', error.message);
    
    if (error.response) {
      console.log('Response status:', error.response.status);
      console.log('Response data:', JSON.stringify(error.response.data, null, 2));
    }
    
    throw error;
  }
}

/**
 * Quick compare without images (text-based)
 */
export async function quickCompare(
  products: { brand: string; name: string; size?: string }[],
  country: string = 'Bahrain'
): Promise<ComparisonResult> {
  const response = await api.post<ComparisonResult>('/api/v1/compare/quick', {
    products,
    country,
  });

  return response.data;
}

/**
 * Get rate limit status
 */
export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const response = await api.get<RateLimitStatus>('/api/v1/rate-limit/status');
  return response.data;
}

/**
 * Get subscription status
 */
export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  const response = await api.get<SubscriptionStatus>('/api/v1/subscription/status');
  return response.data;
}

/**
 * Get comparison history
 */
export async function getComparisonHistory(limit: number = 20, offset: number = 0) {
  const response = await api.get('/api/v1/comparisons/history', {
    params: { limit, offset },
  });
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await api.get('/health', { timeout: 5000 });
    return response.data.status === 'healthy';
  } catch {
    return false;
  }
}

/**
 * Debug function to test image upload
 */
export async function debugUpload(imageUris: string[]): Promise<any> {
  console.log('=== DEBUG UPLOAD ===');
  
  const formData = new FormData();

  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];
    console.log(`Image ${i + 1} URI: ${uri}`);
    
    formData.append('images', {
      uri: uri,
      type: 'image/jpeg',
      name: `test_${i + 1}.jpg`,
    } as any);
  }

  const response = await api.post('/api/v1/debug/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  
  console.log('Debug response:', JSON.stringify(response.data, null, 2));
  return response.data;
}

export default api;
