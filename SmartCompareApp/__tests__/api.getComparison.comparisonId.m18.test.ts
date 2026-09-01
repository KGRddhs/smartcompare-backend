/**
 * M18 MB-contract-03 (comparison-id unit) — getComparison must surface the
 * persisted row id (`wrapper.comparison.id`, returned by
 * GET /api/v1/comparisons/{id}, history_routes.py:156-166) on the payload it
 * hands back, as `comparison_id`.
 *
 * Why: prior code unwrapped `wrapper.comparison.full_response` and DISCARDED
 * `wrapper.comparison.id`, so ResultsScreen's `sharableComparisonId` was
 * permanently undefined (share/referral Loop-1 unreachable from Results) and
 * the screen fell back to metadata.query — a raw query string the backend's
 * M13-29 UUID validators 422-reject on /events and /feedback.
 *
 * Mock pattern mirrors api.demographics.test.ts (the precedent for importing
 * out of src/services/api.ts without the network surface).
 */

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

import axios from 'axios';
import { getComparison } from '../src/services/api';

const axiosInstance = (axios as any).__instance;

const ROW_ID = '3f2b8c1d-9a4e-4f6b-8c2d-1e5a7b9c0d2f';

const FULL_RESPONSE = {
  success: true,
  products: [{ name: 'iPhone 15' }, { name: 'Galaxy S24' }],
  metadata: { query: 'iPhone 15 vs Galaxy S24', region: 'bahrain' },
};

const WRAPPER = {
  success: true,
  comparison: {
    id: ROW_ID,
    query: 'iPhone 15 vs Galaxy S24',
    full_response: FULL_RESPONSE,
  },
};

describe('getComparison — comparison_id surfacing (M18 MB-contract-03)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('GETs /api/v1/comparisons/{id} and returns the full_response shape', async () => {
    axiosInstance.get.mockResolvedValueOnce({ data: WRAPPER });
    const result = await getComparison(ROW_ID);
    expect(axiosInstance.get).toHaveBeenCalledWith(`/api/v1/comparisons/${ROW_ID}`);
    expect(result.products).toHaveLength(2);
    expect(result.metadata.query).toBe('iPhone 15 vs Galaxy S24');
  });

  it('surfaces wrapper.comparison.id as comparison_id on the returned payload', async () => {
    axiosInstance.get.mockResolvedValueOnce({ data: WRAPPER });
    const result = await getComparison(ROW_ID);
    // THE fix: the persisted row UUID must ride the payload so ResultsScreen
    // can use it for share + events + feedback. Base code discards it.
    expect(result.comparison_id).toBe(ROW_ID);
  });

  it('comparison_id is a UUID, never the query string (M13-29 contract)', async () => {
    axiosInstance.get.mockResolvedValueOnce({ data: WRAPPER });
    const result = await getComparison(ROW_ID);
    expect(result.comparison_id).not.toBe('iPhone 15 vs Galaxy S24');
    expect(result.comparison_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('still throws the 404-shaped error when full_response is missing (Path A R2 contract preserved)', async () => {
    axiosInstance.get.mockResolvedValueOnce({
      data: { success: true, comparison: { id: ROW_ID, full_response: null } },
    });
    await expect(getComparison(ROW_ID)).rejects.toMatchObject({
      response: { status: 404 },
    });
  });
});
