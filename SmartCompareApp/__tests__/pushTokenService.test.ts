/**
 * pushTokenService tests (F5.4)
 *
 * Verifies the contract: register a real token via PUT, swallow every
 * failure mode (no module / permission denied / no token / network), and
 * coalesce concurrent calls.
 */

const mockPut = jest.fn();
jest.mock('../src/services/api', () => ({
  api: { put: (...args: any[]) => mockPut(...args) },
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// Mock factory for expo-notifications — overridden per test via
// `jest.doMock('expo-notifications', () => ...)` because some tests need
// the module to throw on require, others need different success/denial paths.
const setExpoNotificationsMock = (impl: any) => {
  jest.doMock('expo-notifications', () => impl, { virtual: true });
};

const FIVE_FAILURE_CODES = ['no_module', 'permission_denied', 'no_token', 'network_error', 'already_registered'];

describe('pushTokenService.tryRegisterPushToken', () => {
  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  it('returns no_module when expo-notifications fails to load', async () => {
    // Make require('expo-notifications') throw
    jest.doMock('expo-notifications', () => {
      throw new Error('native module missing');
    }, { virtual: true });
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(false);
    expect(result.reason).toBe('no_module');
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('returns permission_denied when user rejects the prompt', async () => {
    setExpoNotificationsMock({
      getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'undetermined' }),
      requestPermissionsAsync: jest.fn().mockResolvedValue({ status: 'denied' }),
      getExpoPushTokenAsync: jest.fn(),
    });
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(false);
    expect(result.reason).toBe('permission_denied');
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('returns no_token when getExpoPushTokenAsync returns empty', async () => {
    setExpoNotificationsMock({
      getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
      requestPermissionsAsync: jest.fn(),
      getExpoPushTokenAsync: jest.fn().mockResolvedValue({ data: '' }),
    });
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(false);
    expect(result.reason).toBe('no_token');
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('PUTs the token and returns registered:true on the happy path', async () => {
    setExpoNotificationsMock({
      getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
      requestPermissionsAsync: jest.fn(),
      getExpoPushTokenAsync: jest.fn().mockResolvedValue({
        data: 'ExponentPushToken[abc123]',
      }),
    });
    mockPut.mockResolvedValue({ data: { success: true } });
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(true);
    expect(mockPut).toHaveBeenCalledWith('/api/v1/auth/push-token', {
      expo_push_token: 'ExponentPushToken[abc123]',
    });
  });

  it('returns network_error when PUT throws', async () => {
    setExpoNotificationsMock({
      getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
      requestPermissionsAsync: jest.fn(),
      getExpoPushTokenAsync: jest.fn().mockResolvedValue({
        data: 'ExponentPushToken[abc123]',
      }),
    });
    mockPut.mockRejectedValueOnce(new Error('connection refused'));
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(false);
    expect(result.reason).toBe('network_error');
  });

  it('coalesces concurrent calls — second call returns first call result', async () => {
    setExpoNotificationsMock({
      getPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
      requestPermissionsAsync: jest.fn(),
      getExpoPushTokenAsync: jest.fn().mockResolvedValue({
        data: 'ExponentPushToken[abc123]',
      }),
    });
    mockPut.mockResolvedValue({ data: { success: true } });
    const { tryRegisterPushToken } = require('../src/services/pushTokenService');
    const [a, b] = await Promise.all([
      tryRegisterPushToken(),
      tryRegisterPushToken(),
    ]);
    expect(a.registered).toBe(true);
    expect(b.registered).toBe(true);
    // Both calls share the same in-flight promise — only ONE PUT
    expect(mockPut).toHaveBeenCalledTimes(1);
  });
});
