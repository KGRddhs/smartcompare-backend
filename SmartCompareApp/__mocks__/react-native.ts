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

// Bundle E S1 — screens use Alert.alert for "Coming soon" placeholder
// CTAs (PaywallScreen subscribe, restore, terms, etc.). jest.spyOn(Alert,
// 'alert') in test scaffolds requires Alert to be a real exported object.
export const Alert = {
  alert: jest.fn(),
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
  ScrollView,
  Modal,
  Switch,
  Pressable,
  ActivityIndicator,
  Platform,
  Dimensions,
  StyleSheet,
  I18nManager,
  Alert,
};
