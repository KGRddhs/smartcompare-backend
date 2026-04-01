import React from 'react';

const createElement = React.createElement;

// Simple mock components that render as divs with props
function createMockComponent(name: string) {
  const component = ({ children, ...props }: any) => createElement('mock-' + name, props, children);
  component.displayName = name;
  return component;
}

export const View = createMockComponent('View');
export const Text = createMockComponent('Text');
export const TouchableOpacity = ({ children, onPress, disabled, ...props }: any) =>
  createElement('mock-TouchableOpacity', { ...props, onPress, disabled }, children);
export const TextInput = React.forwardRef(({ ...props }: any, ref: any) =>
  createElement('mock-TextInput', { ...props, ref }));
export const SafeAreaView = createMockComponent('SafeAreaView');
export const KeyboardAvoidingView = createMockComponent('KeyboardAvoidingView');
export const FlatList = createMockComponent('FlatList');
export const ActivityIndicator = createMockComponent('ActivityIndicator');
export const Platform = { OS: 'ios', select: (obj: any) => obj.ios };

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

export default {
  View,
  Text,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  KeyboardAvoidingView,
  FlatList,
  ActivityIndicator,
  Platform,
  StyleSheet,
  I18nManager,
};
