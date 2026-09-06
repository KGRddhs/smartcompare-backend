import React from 'react';

const createElement = React.createElement;

// Map mock components to canonical RN host names so @testing-library/react-native
// queries (getByText/getByPlaceholderText/etc.) recognize them.
function createHostComponent(hostName: string) {
  const component = ({ children, ...props }: any) =>
    createElement(hostName, props, children);
  component.displayName = hostName;
  return component;
}

export const View = createHostComponent('View');
export const Text = createHostComponent('Text');
export const Image = ({ source, ...props }: any) =>
  createElement('Image', { ...props, source });
export const TouchableOpacity = ({ children, onPress, disabled, ...props }: any) =>
  createElement('View', { ...props, onPress, disabled, accessible: true }, children);
export const TextInput = React.forwardRef(({ ...props }: any, ref: any) =>
  createElement('TextInput', { ...props, ref }));
export const SafeAreaView = createHostComponent('View');
export const KeyboardAvoidingView = createHostComponent('View');
export const FlatList = createHostComponent('View');
export const ScrollView = ({ children, contentContainerStyle, ...props }: any) =>
  createElement('RCTScrollView', { ...props, contentContainerStyle }, children);
export const Modal = ({ children, visible, ...props }: any) => {
  if (visible === false) return null;
  return createElement('Modal', { ...props, visible }, children);
};
export const ActivityIndicator = createHostComponent('View');
// M21 mobile-jank — RefreshControl is passed as an element to list
// `refreshControl` props; a null-rendering component keeps the tree valid.
export const RefreshControl = (_props: any) => null;
// M21 mobile-jank — minimal non-virtualized SectionList: renders every
// section header + row via the real renderItem/renderSectionHeader so
// row-level render behavior (memoization, entering-animation props) is
// observable in jest. Virtualization is deliberately not simulated.
export const SectionList = ({
  sections = [],
  renderItem,
  renderSectionHeader,
  keyExtractor,
  refreshControl,
  ...props
}: any) =>
  createElement(
    'View',
    props,
    refreshControl ?? null,
    ...sections.map((section: any, si: number) =>
      createElement(
        React.Fragment,
        { key: section?.title ?? si },
        renderSectionHeader ? renderSectionHeader({ section }) : null,
        ...(section?.data ?? []).map((item: any, index: number) =>
          createElement(
            React.Fragment,
            { key: keyExtractor ? keyExtractor(item, index) : index },
            renderItem({ item, index, section })
          )
        )
      )
    )
  );
export const Switch = ({ value, onValueChange, ...props }: any) =>
  createElement('RCTSwitch', { ...props, value, onValueChange });
export const Pressable = ({ children, onPress, disabled, ...props }: any) =>
  createElement('View', { ...props, onPress, disabled, accessible: true }, children);
export const Platform = { OS: 'ios', select: (obj: any) => obj.ios };

export const Dimensions = {
  get: (_dim: 'window' | 'screen') => ({ width: 390, height: 844, scale: 2, fontScale: 1 }),
  addEventListener: jest.fn(() => ({ remove: jest.fn() })),
};

export const StyleSheet = {
  create: <T extends Record<string, any>>(styles: T): T => styles,
  flatten: (style: any) => {
    if (Array.isArray(style)) {
      return Object.assign({}, ...style.filter(Boolean));
    }
    return style || {};
  },
};

export const I18nManager = {
  isRTL: false,
  allowRTL: jest.fn(),
  forceRTL: jest.fn(),
};

// M21 onboarding-retry (MB-flows-04) — onboardingDraft.ts arms a
// foreground replay via AppState while a completion draft is pending.
// Minimal listener registry so tests can drive 'change' events.
type AppStateListener = (state: string) => void;
const appStateListeners = new Set<AppStateListener>();
export const AppState = {
  currentState: 'active',
  addEventListener: jest.fn((_type: string, listener: AppStateListener) => {
    appStateListeners.add(listener);
    return {
      remove: () => {
        appStateListeners.delete(listener);
      },
    };
  }),
  // Test helper (not part of the RN API): fire a state change.
  __emit: (state: string) => {
    appStateListeners.forEach((listener) => listener(state));
  },
};

// Bundle E S1 — screens use Alert.alert for "Coming soon" placeholder
// CTAs (PaywallScreen subscribe, restore, terms, etc.). jest.spyOn(Alert,
// 'alert') in test scaffolds requires Alert to be a real exported object.
export const Alert = {
  alert: jest.fn(),
};

// B5 — HomeScreen pushes its two consumer-less boot calls (the /health
// telemetry ping and the compare_entry_view analytics POST) behind the
// interaction queue so they stop racing the first paint. The real
// InteractionManager runs the task AFTER the current interactions/animations
// settle, i.e. never in the same synchronous turn as the effect that
// scheduled it — this shim reproduces exactly that asynchrony (a macrotask),
// which is what lets a test tell "deferred" apart from "called inline".
type InteractionTask = () => void;
export const InteractionManager = {
  runAfterInteractions: (task?: InteractionTask) => {
    const handle = setTimeout(() => {
      task?.();
    }, 0);
    return {
      cancel: () => clearTimeout(handle),
      then: (onDone: () => void) => Promise.resolve().then(onDone),
      done: (onDone: () => void) => Promise.resolve().then(onDone),
    };
  },
  createInteractionHandle: jest.fn(() => 1),
  clearInteractionHandle: jest.fn(),
};

export default {
  View,
  Text,
  Image,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  KeyboardAvoidingView,
  FlatList,
  SectionList,
  RefreshControl,
  ScrollView,
  Modal,
  Switch,
  Pressable,
  ActivityIndicator,
  Platform,
  Dimensions,
  StyleSheet,
  I18nManager,
  AppState,
  Alert,
  InteractionManager,
};
