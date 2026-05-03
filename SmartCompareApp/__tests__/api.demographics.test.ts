/**
 * Unit tests for demographics API client methods.
 * Backend dependency: PUT /api/v1/auth/demographics, GET /api/v1/auth/cohort-profile
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
import {
  putDemographics,
  getCohortProfile,
} from '../src/services/api';

const axiosInstance = (axios as any).__instance;

describe('putDemographics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('PUTs to /api/v1/auth/demographics with payload', async () => {
    axiosInstance.put.mockResolvedValueOnce({
      data: {
        success: true,
        cohort_match: {
          cohort_key: '25-34|Female|Northern|Arabic',
          match_quality: 'exact',
          confidence: 'high',
          n: 23,
          persona_label: 'Quality-first focused buyer',
        },
      },
    });

    const result = await putDemographics({
      age_group: '25-34',
      gender: 'Female',
      governorate: 'Northern',
      language: 'Arabic',
    });

    expect(axiosInstance.put).toHaveBeenCalledWith(
      '/api/v1/auth/demographics',
      expect.objectContaining({
        age_group: '25-34',
        gender: 'Female',
        governorate: 'Northern',
        language: 'Arabic',
      })
    );
    expect(result.success).toBe(true);
    expect(result.cohort_match?.match_quality).toBe('exact');
  });

  it('handles all-skip payload (Prefer not to say)', async () => {
    axiosInstance.put.mockResolvedValueOnce({
      data: {
        success: true,
        cohort_match: { match_quality: 'population', confidence: 'high', n: 397 },
      },
    });

    const result = await putDemographics({
      age_group: 'Prefer not to say',
      gender: 'Prefer not to say',
      governorate: 'Prefer not to say',
    });

    expect(result.success).toBe(true);
    expect(result.cohort_match?.match_quality).toBe('population');
  });

  it('throws on backend error', async () => {
    axiosInstance.put.mockRejectedValueOnce(new Error('500 server error'));
    await expect(
      putDemographics({ age_group: '25-34' })
    ).rejects.toThrow('500 server error');
  });
});

describe('getCohortProfile', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('GETs from /api/v1/auth/cohort-profile and returns display payload', async () => {
    axiosInstance.get.mockResolvedValueOnce({
      data: {
        display: {
          persona_label: 'Quality-first focused buyer',
          n: 23,
          confidence: 'high',
          modal: {
            top_deciding_factor: 'Quality',
            second_deciding_factor: 'Price',
            spend_bracket: '25-50 BHD',
            preferred_assistance_style: 'Show me 2 or 3 suitable options',
          },
        },
      },
    });

    const result = await getCohortProfile();

    expect(axiosInstance.get).toHaveBeenCalledWith('/api/v1/auth/cohort-profile');
    expect(result.display?.persona_label).toBe('Quality-first focused buyer');
    expect(result.display?.n).toBe(23);
  });

  it('returns null display when confidence below threshold', async () => {
    axiosInstance.get.mockResolvedValueOnce({ data: { display: null } });
    const result = await getCohortProfile();
    expect(result.display).toBeNull();
  });

  it('returns null display on network error (graceful)', async () => {
    axiosInstance.get.mockRejectedValueOnce(new Error('network down'));
    const result = await getCohortProfile();
    expect(result.display).toBeNull();
  });
});
