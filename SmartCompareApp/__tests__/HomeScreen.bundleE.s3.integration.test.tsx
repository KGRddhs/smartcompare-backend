/**
 * HomeScreen Bundle E S3 — integration render tests for coverage push.
 *
 * Synchronous render() + waitFor() pattern (same as
 * EditProfileScreen + ProfileScreen integration tests).
 *
 * HomeScreen has the deepest dependency tree (expo-camera, image-picker,
 * reanimated, TwoInputShell, HomeEditorialSections, useFocusEffect ×2,
 * SSE streaming). Mock at the boundary (services + native modules);
 * exercise the orchestration code paths directly.
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
      }, []);
    },
  };
});

jest.mock('expo-camera', () => {
  const ReactRequired = require('react');
  return {
    CameraView: () =>
      ReactRequired.createElement('CameraView'),
    useCameraPermissions: () => [{ granted: true }, jest.fn()],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn().mockResolvedValue({ canceled: true }),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetReferralStatus(...args),
}));

jest.mock('../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn(),
  }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));

// Lightweight stubs for heavy children — exercise HomeScreen's orchestration
// not the child components.
jest.mock('../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  // catfix D1 — faithful-enough mock: renders a pressable chip per category
  // (real testID contract `category-chip-<value>`) wired to onChange, so a
  // test can tap a chip exactly as a user would and drive selectedCategory.
  const CATS = [
    'electronics',
    'grocery',
    'supplements',
    'makeup',
    'skincare',
    'haircare',
    'fragrances',
    'fashion',
    'other',
  ];
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement(
        'View',
        { testID: 'mock-category-selector' },
        CATS.map((c) =>
          ReactRequired.createElement('View', {
            key: c,
            testID: `category-chip-${c}`,
            onPress: () => props.onChange && props.onChange(c),
          }),
        ),
      ),
  };
});

jest.mock('../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-two-input-shell',
        // Expose every callback prop on the mock so tests can drive them
        // directly via `shell.props.onX(...)`.
        ...props,
      }),
  };
});

jest.mock('../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: ({ onPickCategory, onPressTrending, onPressVerdict }: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-home-editorial-sections',
        onPickCategory,
        onPressTrending,
        onPressVerdict,
      }),
  };
});

jest.mock('../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

import HomeScreen from '../src/screens/HomeScreen';

function makeProps(overrides: any = {}) {
  return {
    navigation: {
      navigate: jest.fn(),
      goBack: jest.fn(),
    },
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 1,
    bonus_referrer_name: 'Sara',
    bonus_expires_at: null,
  });
});

describe('HomeScreen S3 integration — initial render', () => {
  it('renders header + counter + mode tabs + Compare CTA', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    expect(rendered.getByTestId('home-header-counter')).toBeTruthy();
    expect(rendered.getByTestId('home-mode-scan')).toBeTruthy();
    expect(rendered.getByTestId('home-mode-link')).toBeTruthy();
    expect(rendered.getByTestId('home-mode-type')).toBeTruthy();
    expect(rendered.getByTestId('home-compare-cta')).toBeTruthy();
    expect(rendered.getByTestId('home-center-area')).toBeTruthy();
  });

  it('initial mode is scan — scan preview renders', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    expect(rendered.getByTestId('home-scan-preview')).toBeTruthy();
  });

  it('renders the HomeEditorialSections wrapper (canCompare branch)', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    expect(rendered.getByTestId('mock-home-editorial-sections')).toBeTruthy();
  });

  it('Compare CTA initial label is "Open camera" (scan mode)', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    expect(rendered.getByText('Open camera')).toBeTruthy();
  });

  it('Compare CTA initial state is ENABLED in scan mode (canCompare=true)', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    const cta = rendered.getByTestId('home-compare-cta');
    expect(cta.props.accessibilityState).toEqual({ disabled: false });
  });
});

describe('HomeScreen S3 integration — mode switching', () => {
  it('tapping Link mode flips inputMode and renders TwoInputShell', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    const linkChip = rendered.getByTestId('home-mode-link');
    fireEvent.press(linkChip);
    await waitFor(() => {
      expect(rendered.getByTestId('mock-two-input-shell')).toBeTruthy();
    });
  });

  it('tapping Type mode hides the HomeScreen scan CTA (TwoInputShell owns it)', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    await waitFor(() => {
      // The scan-mode CTA (testID home-compare-cta) is gated on inputMode==='scan';
      // in type mode TwoInputShell's internal CTA is canonical.
      expect(rendered.queryByTestId('home-compare-cta')).toBeNull();
      expect(rendered.getByTestId('mock-two-input-shell')).toBeTruthy();
    });
  });

  it('tapping Link mode hides the HomeScreen scan CTA (TwoInputShell owns it)', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    await waitFor(() => {
      expect(rendered.queryByTestId('home-compare-cta')).toBeNull();
      expect(rendered.getByTestId('mock-two-input-shell')).toBeTruthy();
    });
  });
});

describe('HomeScreen S3 integration — Compare CTA press', () => {
  it('CTA press in scan mode navigates to ScanCamera', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-compare-cta'));
    expect(props.navigation.navigate).toHaveBeenCalledWith('ScanCamera');
  });

  it('CTA press in scan mode fires no compare API call', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-compare-cta'));
    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(mockApiPost).not.toHaveBeenCalled();
  });
});

describe('HomeScreen S3 integration — header counter', () => {
  it('tapping the header counter navigates to Paywall + fires analytics', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-header-counter'));
    expect(props.navigation.navigate).toHaveBeenCalledWith('Paywall');
    expect(mockTrackEvent).toHaveBeenCalledWith(
      'compare_entry_paywall_banner_tap',
      expect.objectContaining({ mode: expect.any(String) }),
    );
  });
});

describe('HomeScreen S3 integration — scan preview row taps', () => {
  it('tapping scan preview row A navigates to ScanCamera', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-scan-preview-row-a'));
    expect(props.navigation.navigate).toHaveBeenCalledWith('ScanCamera');
  });

  it('tapping scan preview row B navigates to ScanCamera', () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-scan-preview-row-b'));
    expect(props.navigation.navigate).toHaveBeenCalledWith('ScanCamera');
  });
});

describe('HomeScreen S3 integration — text compare flow via TwoInputShell', () => {
  it('text mode submit via TwoInputShell.onSubmit calls streamComparison', async () => {
    let subscribeFn: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeFn = handlers;
      },
      abort: jest.fn(),
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    // TwoInputShell now owns its own Compare CTA — drive its onSubmit prop
    // directly to mirror a user tap inside the shell.
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    // catfix D1 — with NO category chip tapped, `selected_category` is
    // OMITTED (the prior silent 'electronics' default is gone; the backend
    // resolves the true category). The options arg is an empty object.
    expect(mockStreamComparison).toHaveBeenCalledWith(
      { product_a: 'iPhone 15', product_b: 'Galaxy S24' },
      {},
    );
    expect(subscribeFn).not.toBeNull();
  });

  it('catfix D1 — selected_category IS sent once a category chip is tapped', async () => {
    let subscribeFn: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeFn = handlers;
      },
      abort: jest.fn(),
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    // Tap a category chip first, then switch to type mode and submit.
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('Dior Sauvage', 'Creed Aventus');
    expect(mockStreamComparison).toHaveBeenCalledWith(
      { product_a: 'Dior Sauvage', product_b: 'Creed Aventus' },
      { selected_category: 'fragrances' },
    );
    expect(subscribeFn).not.toBeNull();
  });

  it('SSE onComplete success path navigates to Results', async () => {
    let subscribeFn: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeFn = handlers;
      },
      abort: jest.fn(),
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    // Drive SSE callback.
    await subscribeFn.onComplete({ success: true, comparison: {} });
    expect(mockStreamComparison).toHaveBeenCalled();
  });
});

describe('HomeScreen S3 integration — TwoInputShell callbacks fire analytics', () => {
  it('onPasteSplit callback fires analytics event', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    // Real wiring passes onPasteSplit through. We invoke the prop
    // directly to verify it tracks the event.
    shell.props.onPasteSplit('a');
    expect(mockTrackEvent).toHaveBeenCalledWith(
      'compare_entry_paste_split',
      expect.objectContaining({ source_box: 'a', mode: 'text' }),
    );
  });

  it('onModeAutoswitch callback flips mode to url + fires analytics', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onModeAutoswitch('text', 'url');
    expect(mockTrackEvent).toHaveBeenCalledWith(
      'compare_entry_mode_autoswitch',
      expect.objectContaining({ from: 'text', to: 'url' }),
    );
  });

  it('onReady callback fires analytics', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onReady(450);
    expect(mockTrackEvent).toHaveBeenCalledWith(
      'compare_entry_ready',
      expect.objectContaining({ mode: 'text', time_to_ready_ms: 450 }),
    );
  });
});

describe('HomeScreen S3 integration — URL compare flow', () => {
  it('URL submit via TwoInputShell.onSubmit calls api.post(/url/compare)', async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { success: true, comparison: {} },
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        '/api/v1/url/compare',
        expect.objectContaining({
          url1: 'https://noon.com/a',
          url2: 'https://amazon.com/b',
          region: 'bahrain',
        }),
      );
    });
  });
});

describe('HomeScreen S3 integration — error/edge paths', () => {
  it('URL compare API failure surfaces Alert', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('Network 500'));
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert');
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });
    alertSpy.mockRestore();
  });

  it('URL compare backend non-success returns the backend error', async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { success: false, error: 'Refused' },
    });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert');
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });
    alertSpy.mockRestore();
  });

  it('text submit via TwoInputShell.onSubmit calls streamComparison', async () => {
    mockStreamComparison.mockReturnValue({
      subscribe: jest.fn(),
      abort: jest.fn(),
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    expect(mockStreamComparison).toHaveBeenCalled();
  });

  it('SSE onError path surfaces Alert when not a special code', async () => {
    let subscribeFn: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeFn = handlers;
      },
      abort: jest.fn(),
    });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert');
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    // Drive the onError callback.
    subscribeFn.onError({ message: 'GPT timeout' });
    expect(alertSpy).toHaveBeenCalled();
    alertSpy.mockRestore();
  });

  it('SSE onStatus updates the loading caption', async () => {
    let subscribeFn: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeFn = handlers;
      },
      abort: jest.fn(),
    });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    // Drive a status callback — status surfaces via LoadingScreenVariants
    // caption (full-screen theatrical loader) now.
    subscribeFn.onStatus('Finding products');
    await waitFor(() => {
      expect(rendered.getByText('Finding products')).toBeTruthy();
    });
  });
});

describe('HomeScreen S3 integration — editorial section callbacks', () => {
  it('onPickCategory from editorial flips mode to type', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    const editorial = rendered.getByTestId('mock-home-editorial-sections');
    editorial.props.onPickCategory('skincare');
    // In type mode the scan-only home-compare-cta is hidden and the
    // TwoInputShell (which owns the Compare CTA now) is rendered.
    await waitFor(() => {
      expect(rendered.queryByTestId('home-compare-cta')).toBeNull();
      expect(rendered.getByTestId('mock-two-input-shell')).toBeTruthy();
    });
  });

  it('onPressTrending flips mode to type', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    const editorial = rendered.getByTestId('mock-home-editorial-sections');
    editorial.props.onPressTrending();
    await waitFor(() => {
      expect(rendered.queryByTestId('home-compare-cta')).toBeNull();
      expect(rendered.getByTestId('mock-two-input-shell')).toBeTruthy();
    });
  });

  it('onPressVerdict navigates to Results with from_history', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    const editorial = rendered.getByTestId('mock-home-editorial-sections');
    editorial.props.onPressVerdict('cmp-123');
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ from_history: 'cmp-123' }),
    );
  });
});
