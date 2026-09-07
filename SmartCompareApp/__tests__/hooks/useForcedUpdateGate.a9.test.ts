/**
 * A9 — the gate hook that App.tsx consumes.
 *
 * The hook is the seam between "the backend said block" and "the root
 * component renders the blocking screen". What matters here is that it is
 * genuinely fire-and-forget (no render is ever held on the answer), that
 * it asks exactly once per mount, and that nothing except an affirmative
 * answer can ever produce a gate.
 *
 * NOT ASSERTED, deliberately: the `cancelled` latch in the cleanup. React
 * 19 no longer warns on a setState after unmount, so a stripped latch has
 * no observable effect from the outside and any test of it would be a test
 * of the mock rather than of behaviour. It stays in the source as cheap
 * hygiene.
 */
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { useForcedUpdateGate } from '../../src/hooks/useForcedUpdateGate';
import { checkForcedUpdate } from '../../src/services/appVersionService';

jest.mock('../../src/services/appVersionService', () => ({
  checkForcedUpdate: jest.fn(),
}));

const mockedCheck = checkForcedUpdate as jest.MockedFunction<typeof checkForcedUpdate>;

const GATE = {
  minVersion: '1.5.0',
  currentVersion: '1.2.0',
  updateUrl: 'https://apps.apple.com/app/id1',
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('useForcedUpdateGate', () => {
  it('returns null on the FIRST render even when the answer is already available', () => {
    mockedCheck.mockResolvedValue(GATE);

    const { result } = renderHook(() => useForcedUpdateGate());

    // Boot must never be gated on the version check: the first paint
    // happens with no gate regardless of how fast the backend answers.
    expect(result.current).toBeNull();
  });

  it('surfaces the gate once an affirmative answer lands', async () => {
    mockedCheck.mockResolvedValue(GATE);

    const { result } = renderHook(() => useForcedUpdateGate());

    await waitFor(() => expect(result.current).toEqual(GATE));
  });

  it('stays null when the service declines to gate (every fail-open path)', async () => {
    mockedCheck.mockResolvedValue(null);

    const { result } = renderHook(() => useForcedUpdateGate());

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current).toBeNull();
  });

  it('stays null — and raises no unhandled rejection — when the check rejects', async () => {
    const unhandled: unknown[] = [];
    const capture = (reason: unknown) => unhandled.push(reason);
    process.on('unhandledRejection', capture);

    try {
      mockedCheck.mockRejectedValue(new Error('the version check exploded'));

      const { result } = renderHook(() => useForcedUpdateGate());

      await act(async () => {
        // Two macrotask turns: enough for Node to have reported an
        // unhandled rejection if the .catch were missing.
        await new Promise((resolve) => setTimeout(resolve, 0));
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      expect(result.current).toBeNull();
      expect(unhandled).toEqual([]);
    } finally {
      process.off('unhandledRejection', capture);
    }
  });

  it('asks exactly once per mount, not once per render', async () => {
    mockedCheck.mockResolvedValue(null);

    const { rerender } = renderHook(() => useForcedUpdateGate());

    await act(async () => {
      await Promise.resolve();
    });
    rerender(undefined);
    rerender(undefined);
    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedCheck).toHaveBeenCalledTimes(1);
  });
});
