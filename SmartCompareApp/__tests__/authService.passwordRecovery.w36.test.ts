/**
 * W3-6 — `authService.completePasswordRecovery` is the client half of the
 * new unauthenticated completion endpoint.
 *
 * The recovery ACCESS token is the credential; the refresh token is
 * deliberately never sent (the backend needs only the access token, and
 * `sentry.ts:28-40` would not scrub a non-JWT-shaped refresh token if it
 * ever reached a breadcrumb). The endpoint is `/password-recovery`, NOT
 * `/reset-password` — `tests/test_auth_interceptor.py:1626` pins that
 * `/api/v1/auth/reset-password` does not exist.
 */

const mockPost = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
}));

jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

// eslint-disable-next-line @typescript-eslint/no-var-requires
const authService = require('../src/services/authService');

beforeEach(() => {
  mockPost.mockReset();
});

describe('completePasswordRecovery', () => {
  it('posts the access token and the new password to /api/v1/auth/password-recovery', async () => {
    mockPost.mockResolvedValue({ data: { success: true, message: 'Password updated' } });

    await authService.completePasswordRecovery('tok', 'NewPassw0rd!x');

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][0]).toBe('/api/v1/auth/password-recovery');
  });

  it('sends EXACTLY { access_token, new_password } — no refresh token rides along', async () => {
    mockPost.mockResolvedValue({ data: { success: true, message: 'Password updated' } });

    await authService.completePasswordRecovery('tok', 'NewPassw0rd!x');

    const body = mockPost.mock.calls[0][1];
    expect(body).toEqual({ access_token: 'tok', new_password: 'NewPassw0rd!x' });
    expect(Object.keys(body).sort()).toEqual(['access_token', 'new_password']);
  });

  it('rejects with the server error when the body reports success: false', async () => {
    mockPost.mockResolvedValue({
      data: { success: false, error: 'This reset link is no longer valid.' },
    });

    await expect(
      authService.completePasswordRecovery('tok', 'NewPassw0rd!x'),
    ).rejects.toThrow('This reset link is no longer valid.');
  });

  it('propagates the SAME axios error, response and code intact, so the screen can branch on RECOVERY_TOKEN_INVALID', async () => {
    // The backend's unified envelope for this 400 is
    // {success:false, error, code, request_id} — no `detail` key — so the
    // detail-unwrap arm must not fire and the original error (carrying
    // `.response.data.code`) must reach the screen. Re-wrapping it in a bare
    // Error would drop the code and the screen could no longer tell a dead
    // link from a transient failure.
    const httpError: any = new Error('Request failed with status code 400');
    httpError.response = {
      status: 400,
      data: {
        success: false,
        error: 'This reset link is no longer valid.',
        code: 'RECOVERY_TOKEN_INVALID',
        request_id: 'r1',
      },
    };
    mockPost.mockRejectedValue(httpError);

    const rejection = await authService
      .completePasswordRecovery('tok', 'NewPassw0rd!x')
      .then(
        () => null,
        (e: any) => e,
      );
    expect(rejection).toBe(httpError);
    expect(rejection.response.data.code).toBe('RECOVERY_TOKEN_INVALID');
  });
});
