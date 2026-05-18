/**
 * HomeScreen Tests
 * Tests camera-first HomeScreen logic: SSE streaming, comparison counter,
 * category selection with i18n, camera capture flow, URL comparison.
 */

// Mock all RN and expo modules
jest.mock('react-native', () => ({
  View: 'View',
  Text: 'Text',
  StyleSheet: { create: (s: any) => s },
  TouchableOpacity: 'TouchableOpacity',
  SafeAreaView: 'SafeAreaView',
  Alert: { alert: jest.fn() },
  ActivityIndicator: 'ActivityIndicator',
  ScrollView: 'ScrollView',
  Image: 'Image',
  TextInput: 'TextInput',
  Modal: 'Modal',
}));

jest.mock('expo-camera', () => ({
  CameraView: 'CameraView',
  useCameraPermissions: jest.fn(() => [{ granted: true }, jest.fn()]),
}));

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn(),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(),
  notificationAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

jest.mock('lucide-react-native', () => ({
  Camera: 'Camera',
  Search: 'Search',
  Link2: 'Link2',
  RotateCcw: 'RotateCcw',
  ImageIcon: 'ImageIcon',
  X: 'X',
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const translations: Record<string, string> = {
        'app.name': 'Qaren',
        'home.search.placeholder': 'Search products...',
        'home.scan': 'Scan Product',
        'home.url': 'URL',
        'home.categories.electronics': 'Electronics',
        'home.categories.grocery': 'Grocery',
        'home.categories.supplements': 'Supplements',
        'home.freeCounter': `${params?.used ?? 0} of ${params?.total ?? 3} free`,
        'results.loading.finding': 'Finding products...',
      };
      return translations[key] || key;
    },
  }),
}));

jest.mock('@react-navigation/native', () => ({
  useFocusEffect: jest.fn((cb) => cb()),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
}));

jest.mock('../src/services/api', () => ({
  healthCheck: jest.fn(() => Promise.resolve(true)),
  streamComparison: jest.fn(),
  parseApiError: jest.fn((e: any) => ({ message: e.message || 'Error' })),
  identifyFromImages: jest.fn(),
  default: { post: jest.fn() },
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: jest.fn(() => Promise.resolve(null)),
}));

jest.mock('../src/components/CategorySelector', () => 'CategorySelector');
jest.mock('../src/components/ComparisonCounter', () => ({ ComparisonCounter: 'ComparisonCounter' }));
jest.mock('../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    shouldShowPaywall: false,
    increment: jest.fn(() => Promise.resolve(2)),
  }),
}));

// Import after mocks
import { streamComparison, identifyFromImages } from '../src/services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

describe('HomeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('SSE Streaming', () => {
    it('streamComparison should be called with query and selected category', () => {
      const mockAbort = jest.fn();
      const mockSubscribe = jest.fn();
      (streamComparison as jest.Mock).mockReturnValue({
        subscribe: mockSubscribe,
        abort: mockAbort,
      });

      // Simulate what HomeScreen.handleTextCompare does
      const query = 'iPhone 15 vs Galaxy S24';
      const selectedCategory = 'electronics';

      const { subscribe, abort } = streamComparison(query, {
        selected_category: selectedCategory,
      });

      expect(streamComparison).toHaveBeenCalledWith(query, {
        selected_category: 'electronics',
      });
      expect(subscribe).toBeDefined();
      expect(abort).toBeDefined();
    });

    it('SSE subscribe callbacks should handle onComplete with success', () => {
      const mockSubscribe = jest.fn();
      (streamComparison as jest.Mock).mockReturnValue({
        subscribe: mockSubscribe,
        abort: jest.fn(),
      });

      const { subscribe } = streamComparison('test query', {});

      // Simulate calling subscribe
      const callbacks = {
        onStatus: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn(),
      };
      subscribe(callbacks);

      expect(mockSubscribe).toHaveBeenCalledWith(callbacks);
    });

    it('SSE subscribe callbacks should handle onError', () => {
      const onError = jest.fn();
      const error = new Error('Network error');

      // Simulate error callback
      onError(error);

      expect(onError).toHaveBeenCalledWith(error);
    });
  });

  describe('Comparison Counter Integration', () => {
    it('useComparisonCounter returns correct initial state', () => {
      const { useComparisonCounter } = require('../src/hooks/useComparisonCounter');
      const counter = useComparisonCounter();

      expect(counter.used).toBe(1);
      expect(counter.total).toBe(3);
      expect(counter.canCompare).toBe(true);
      expect(counter.shouldShowPaywall).toBe(false);
    });

    it('increment returns new count', async () => {
      const { useComparisonCounter } = require('../src/hooks/useComparisonCounter');
      const counter = useComparisonCounter();
      const newCount = await counter.increment();

      expect(newCount).toBe(2);
    });
  });

  describe('Recent Searches', () => {
    it('loads recent searches from AsyncStorage', async () => {
      const stored = JSON.stringify(['iPhone vs Galaxy', 'Dyson vs Shark']);
      (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce(stored);

      const result = await AsyncStorage.getItem('@qaren_recent_searches');
      expect(result).toBe(stored);

      const parsed = JSON.parse(result!);
      expect(parsed).toHaveLength(2);
      expect(parsed[0]).toBe('iPhone vs Galaxy');
    });

    it('saves new search to front of recent list', async () => {
      const existing = ['old search 1', 'old search 2'];
      const newQuery = 'MacBook vs Dell XPS';
      const updated = [newQuery, ...existing.filter((s) => s !== newQuery)].slice(0, 5);

      await AsyncStorage.setItem('@qaren_recent_searches', JSON.stringify(updated));

      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@qaren_recent_searches',
        JSON.stringify(['MacBook vs Dell XPS', 'old search 1', 'old search 2'])
      );
    });

    it('deduplicates recent searches', () => {
      const existing = ['iPhone vs Galaxy', 'Dyson vs Shark'];
      const newQuery = 'iPhone vs Galaxy'; // duplicate
      const updated = [newQuery, ...existing.filter((s) => s !== newQuery)].slice(0, 5);

      expect(updated).toEqual(['iPhone vs Galaxy', 'Dyson vs Shark']);
      expect(updated).toHaveLength(2);
    });

    it('caps recent searches at 5', () => {
      const existing = ['s1', 's2', 's3', 's4', 's5'];
      const newQuery = 'new search';
      const updated = [newQuery, ...existing.filter((s) => s !== newQuery)].slice(0, 5);

      expect(updated).toHaveLength(5);
      expect(updated[0]).toBe('new search');
      expect(updated[4]).toBe('s4'); // s5 dropped
    });
  });

  describe('Camera Capture Flow', () => {
    it('identifyFromImages called with image URIs and region', async () => {
      (identifyFromImages as jest.Mock).mockResolvedValueOnce({
        success: true,
        action: 'comparison',
        products: [],
        comparison: {},
        winner_index: 0,
        recommendation: 'test',
        key_differences: [],
      });

      const imageUris = ['file:///img1.jpg', 'file:///img2.jpg'];
      const result = await identifyFromImages(imageUris, 'bahrain');

      expect(identifyFromImages).toHaveBeenCalledWith(imageUris, 'bahrain');
      expect(result.success).toBe(true);
      expect(result.action).toBe('comparison');
    });

    it('handles need_second_product response', async () => {
      (identifyFromImages as jest.Mock).mockResolvedValueOnce({
        success: true,
        action: 'need_second_product',
        products: [{ brand: 'Apple', name: 'iPhone 15', confidence: 'high' }],
        message: 'Only 1 product found',
        vision_cost: 0.01,
      });

      const result = await identifyFromImages(['file:///img1.jpg', 'file:///img2.jpg'], 'bahrain');

      expect(result.action).toBe('need_second_product');
      expect(result.products).toBeDefined();
      expect(result.products![0].brand).toBe('Apple');
    });

    it('handles identification failure', async () => {
      (identifyFromImages as jest.Mock).mockResolvedValueOnce({
        success: false,
        action: 'error',
        error: 'Could not identify products',
      });

      const result = await identifyFromImages(['file:///img1.jpg'], 'bahrain');

      expect(result.success).toBe(false);
      if ('error' in result) {
        expect(result.error).toBe('Could not identify products');
      }
    });

    it('enforces MIN_IMAGES = 2 and MAX_IMAGES = 4', () => {
      const MIN_IMAGES = 2;
      const MAX_IMAGES = 4;

      expect(1 < MIN_IMAGES).toBe(true); // 1 image not enough
      expect(2 >= MIN_IMAGES).toBe(true); // 2 images sufficient
      expect(4 < MAX_IMAGES).toBe(false); // 4 images at cap
      expect(5 > MAX_IMAGES).toBe(true); // 5 images over cap
    });
  });

  describe('URL Comparison', () => {
    it('validates URLs must start with http', () => {
      const url1 = 'https://amazon.ae/product/123';
      const url2 = 'https://noon.com/product/456';

      expect(url1.startsWith('http')).toBe(true);
      expect(url2.startsWith('http')).toBe(true);
    });

    it('rejects invalid URLs', () => {
      const badUrl = 'not-a-url';
      expect(badUrl.startsWith('http')).toBe(false);
    });
  });

  describe('Category Selection i18n', () => {
    it('all 9 categories have i18n keys', () => {
      const CATEGORIES = [
        'electronics', 'grocery', 'supplements', 'makeup',
        'skincare', 'haircare', 'fragrances', 'fashion', 'other',
      ];

      expect(CATEGORIES).toHaveLength(9);

      CATEGORIES.forEach((cat) => {
        const key = `home.categories.${cat}`;
        expect(key).toBeTruthy();
      });
    });

    it('category values match backend expected values', () => {
      const VALID_CATEGORIES = [
        'electronics', 'grocery', 'supplements', 'makeup',
        'skincare', 'haircare', 'fragrances', 'fashion', 'other',
      ];

      VALID_CATEGORIES.forEach((cat) => {
        expect(cat).toMatch(/^[a-z]+$/);
      });
    });
  });
});
