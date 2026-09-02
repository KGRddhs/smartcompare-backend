/**
 * DirectionalIcon — RTL mirroring wrapper for direction-bearing icons.
 *
 * M21 W4 rtl-i18n (MB-i18n-rtl-03): the repo shipped two flip helpers
 * (utils/rtl.rtlFlip + icons/flipForRTL) with a single consumer between
 * them while ~11 screens rendered back-chevrons and directional arrows
 * unmirrored under RTL. This wrapper is the one wiring point those sites
 * now share.
 *
 * Use ONLY for icons whose glyph encodes a horizontal direction the user
 * reads as "forward/back" — ArrowLeft/Right, ChevronLeft/Right, send.
 * Do NOT wrap direction-agnostic icons (search, star, trash, settings)
 * or icons whose direction is semantic data (TrendingUp = growth).
 *
 * The flip reads I18nManager.isRTL at render time via rtlFlip(); RN
 * direction changes force an app restart, so render-time is fresh enough.
 * The wrapper is a plain View carrying only the scaleX transform — it
 * adds no layout, and pointerEvents="none" keeps touch handling on the
 * surrounding touchable.
 */
import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import { rtlFlip } from '../../utils/rtl';

interface DirectionalIconProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}

export function DirectionalIcon({ children, style, testID }: DirectionalIconProps) {
  return (
    <View testID={testID} pointerEvents="none" style={[rtlFlip(), style]}>
      {children}
    </View>
  );
}

export default DirectionalIcon;
