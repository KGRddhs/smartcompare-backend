/**
 * ContactUsScreen — Bundle A Task 4.5
 *
 * Contract (Bundle A design §4.2 + plan Task 2.9):
 * - submit blocked with empty message
 * - submit blocked with <10 char message
 * - selecting a category chip updates state (active style + a11y selected)
 * - submit POSTs to /api/v1/feedback with the category encoded inline in
 *   change_suggestion (operators grep `[Bug]%` etc. without backend schema
 *   changes)
 * - M18 CD-uncovered-02 / MB-flows-09: the prefix is the STABLE ENGLISH enum
 *   tag, never the localized label — the `t` mock below returns raw keys
 *   (a stand-in for any non-English locale), so these tests fail if the
 *   prefix is ever derived from t() again. Also: `useful` derives from the
 *   category (bug -> false), and MAX_MESSAGE fits the backend's 1000-char
 *   change_suggestion cap so nothing is silently truncated.
 * - success state replaces the form
 * - "Send another" returns to the form
 * - rate-limit guard prevents a 2nd submission within RATE_LIMIT_MS
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';

const mockPost = jest.fn();
jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: (...args: any[]) => mockPost(...args) },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

jest.mock('lucide-react-native', () => ({ ChevronLeft: 'ChevronLeft' }));

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'success' },
}));

import ContactUsScreen from '../src/screens/ContactUsScreen';

function renderScreen() {
  return render(
    <ContactUsScreen
      navigation={{ goBack: jest.fn() } as any}
      route={{ params: undefined, key: 'k', name: 'ContactUs' } as any}
    />,
  );
}

describe('ContactUsScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPost.mockResolvedValue({ data: { ok: true } });
  });

  // The TouchableOpacity passes `disabled` to props, which React Native's
  // runtime uses to block the press. RNTL's fireEvent.press bypasses the
  // disabled check, so we assert the contract that user-visible state
  // (`accessibilityState.disabled` + `props.disabled`) reflects the gate.

  it('marks submit button as disabled when message is empty', () => {
    const { getByText } = renderScreen();
    const submitTxt = getByText('contact.submit');
    let node: any = submitTxt;
    while (node && (!node.props?.accessibilityState || !('disabled' in node.props.accessibilityState))) {
      node = node.parent;
    }
    expect(node?.props.accessibilityState.disabled).toBe(true);
  });

  it('marks submit button as disabled when message < 10 chars', () => {
    const { getByPlaceholderText, getByText } = renderScreen();
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'short',
    );
    // submit text node's nearest accessibilityState (on the TouchableOpacity)
    // should still be disabled
    const submitTxt = getByText('contact.submit');
    // Walk up to find the nearest a11y-disabled ancestor
    let node: any = submitTxt;
    while (node && (!node.props?.accessibilityState || !('disabled' in node.props.accessibilityState))) {
      node = node.parent;
    }
    expect(node?.props.accessibilityState.disabled).toBe(true);
  });

  it('selecting a non-default category routes the STABLE ENGLISH prefix into change_suggestion', async () => {
    const { getByPlaceholderText, getByText } = renderScreen();
    fireEvent.press(getByText('contact.category.suggestion'));
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'A long enough message body for the submit',
    );
    fireEvent.press(getByText('contact.submit'));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    // The t mock returns raw keys — if the prefix were localized (built from
    // t()), it would be "[contact.category.suggestion]" here, which is exactly
    // the Arabic-cohort triage-loss bug. It must be the English enum tag.
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/feedback',
      expect.objectContaining({
        // Suggestion/business/other contact is not a negative signal
        useful: true,
        change_suggestion: expect.stringMatching(/^\[Suggestion\] /),
      }),
    );
  });

  it('POSTs to /api/v1/feedback with the stable [Bug] prefix regardless of locale', async () => {
    const { getByPlaceholderText, getByText } = renderScreen();
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'A long enough message body for the submit',
    );
    fireEvent.press(getByText('contact.submit'));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/feedback',
      expect.objectContaining({
        // A bug report must not register as positive feedback
        useful: false,
        mattered_most: [],
        change_suggestion: expect.stringMatching(/^\[Bug\] /),
      }),
    );
  });

  it('message input cap matches what survives the backend 1000-char limit (no silent truncation)', () => {
    const { getByPlaceholderText, getByText } = renderScreen();
    // Backend FeedbackRequest.change_suggestion has max_length=1000.
    // Worst-case overhead: "[Suggestion] " (13) + subject 120 + "\n\n" (2) = 135,
    // so the honest message cap is 865 — not the old 2000, which silently
    // dropped up to ~1135 chars of a long report.
    const messageInput = getByPlaceholderText('contact.message.placeholder');
    expect(messageInput.props.maxLength).toBe(865);
    // The char counter must advertise the same honest cap
    expect(getByText('0 / 865')).toBeTruthy();
  });

  it('a max-length report with a max-length subject survives untruncated', async () => {
    const { getByPlaceholderText, getByText } = renderScreen();
    const subject = 's'.repeat(120);
    const body = 'b'.repeat(865);
    fireEvent.changeText(getByPlaceholderText('contact.subject.placeholder'), subject);
    fireEvent.changeText(getByPlaceholderText('contact.message.placeholder'), body);
    fireEvent.press(getByText('contact.submit'));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    const payload = mockPost.mock.calls[0][1];
    // Fits the backend cap AND the full body arrived intact — no silent slice
    expect(payload.change_suggestion.length).toBeLessThanOrEqual(1000);
    expect(payload.change_suggestion.endsWith(body)).toBe(true);
    expect(payload.change_suggestion.startsWith(`[Bug] ${subject}`)).toBe(true);
  });

  it('replaces the form with success state after a successful submission', async () => {
    const { getByPlaceholderText, getByText, queryByText, findByText } = renderScreen();
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'A long enough message body for the submit',
    );
    fireEvent.press(getByText('contact.submit'));
    await findByText('contact.success.title');
    expect(queryByText('contact.submit')).toBeNull();
  });

  it('"Send another" returns to the form', async () => {
    const { getByPlaceholderText, getByText, findByText } = renderScreen();
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'A long enough message body for the submit',
    );
    fireEvent.press(getByText('contact.submit'));
    await findByText('contact.success.title');
    fireEvent.press(getByText('contact.submit.again'));
    await findByText('contact.submit');
  });

  it('rate-limit guard prevents a 2nd submission within the window', async () => {
    const { getByPlaceholderText, getByText, findByText } = renderScreen();
    // Submit 1
    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'A long enough message body for the submit',
    );
    fireEvent.press(getByText('contact.submit'));
    await findByText('contact.success.title');

    // Return to form via "Send another"
    fireEvent.press(getByText('contact.submit.again'));
    await findByText('contact.submit');

    fireEvent.changeText(
      getByPlaceholderText('contact.message.placeholder'),
      'Another message body that is long enough',
    );

    mockPost.mockClear();
    fireEvent.press(getByText('contact.submit'));
    await findByText('contact.error.rateLimit');
    expect(mockPost).not.toHaveBeenCalled();
  });
});
