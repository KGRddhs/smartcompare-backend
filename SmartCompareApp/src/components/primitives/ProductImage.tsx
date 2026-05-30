/**
 * ProductImage — Bundle E S3 A4 image-rendering primitive.
 *
 * Single source of truth for product-image slots across ResultsScreen card,
 * HistoryScreen mini-VS rows, and HomeScreen SmartPick tiles. Renders <Image>
 * with onError fallback to an inline placeholder (tone-color square + dimmed
 * phone-shaped SVG glyph).
 *
 * Backend contract (A3 lane):
 *   products[*].image_url: string | null
 *
 * Rendering states:
 *   1. imageUrl is a non-empty string → <Image source={{uri}} />
 *   2. imageUrl is null               → placeholder
 *   3. imageUrl is undefined          → placeholder
 *   4. <Image> onError fires          → swap to placeholder, preserve tone
 *
 * Visual spec from ResultsScreen.jsx:39-66 + HomeScreen.jsx:503-525:
 *   - aspectRatio default 1 (square tile)
 *   - borderRadius default 14 (Results); SmartPick uses 12, History row tile 12
 *   - placeholder background = `placeholderTone` (per-product tone color)
 *     fallback when omitted: neutral cool grey #EEEFF4 matching ResultsScreen.jsx
 *
 * No new native deps — uses react-native built-in <Image>.
 */

import React from 'react';
import { Image, ImageStyle, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import Svg, { Line, Rect } from 'react-native-svg';

import { colors } from '../../theme';

const DEFAULT_TONE = '#EEEFF4';

interface Props {
  imageUrl?: string | null;
  placeholderTone?: string;
  aspectRatio?: number;
  borderRadius?: number;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

function isUsableUrl(value: string | null | undefined): value is string {
  if (typeof value !== 'string') return false;
  return value.trim().length > 0;
}

export function ProductImage({
  imageUrl,
  placeholderTone = DEFAULT_TONE,
  aspectRatio = 1,
  borderRadius = 14,
  testID,
  style,
}: Props) {
  const [errored, setErrored] = React.useState(false);

  // Reset error state when the imageUrl prop changes — a new URL deserves
  // a fresh attempt (race: a SSE update arrives after an earlier broken URL).
  React.useEffect(() => {
    setErrored(false);
  }, [imageUrl]);

  const usable = isUsableUrl(imageUrl) && !errored;
  const tileStyle = { aspectRatio, borderRadius };

  if (usable) {
    const imageStyle: StyleProp<ImageStyle> = [
      styles.tileImage,
      tileStyle,
      style as StyleProp<ImageStyle>,
    ];
    // Wrap in a host View so the base testID lands on a stable parent
    // regardless of which branch (img vs placeholder) renders. Existing
    // testID queries from upstream consumers (A2 slot contract) keep
    // working; the inner -img / -placeholder suffix is the discriminator.
    return (
      <View testID={testID} style={styles.host}>
        <Image
          testID={testID ? `${testID}-img` : undefined}
          source={{ uri: imageUrl as string }}
          accessibilityRole="image"
          onError={() => setErrored(true)}
          style={imageStyle}
        />
      </View>
    );
  }

  return (
    <View
      testID={testID}
      style={styles.host}
    >
      <View
        testID={testID ? `${testID}-placeholder` : undefined}
        accessibilityRole="image"
        style={[styles.tile, styles.placeholder, tileStyle, { backgroundColor: placeholderTone }, style]}
      >
      <View testID={testID ? `${testID}-placeholder-icon` : undefined} style={styles.iconWrap}>
        <Svg width={28} height={28} viewBox="0 0 24 24">
          <Rect
            x={5}
            y={2}
            width={14}
            height={20}
            rx={2.5}
            fill="none"
            stroke={colors.text.placeholder}
            strokeWidth={1.5}
          />
          <Line
            x1={12}
            y1={18}
            x2={12.01}
            y2={18}
            stroke={colors.text.placeholder}
            strokeWidth={1.5}
            strokeLinecap="round"
          />
        </Svg>
      </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // Host wrapper exists purely to carry the base testID stably so
  // upstream consumers (A2's slot contract) keep working regardless of
  // which branch (img / placeholder) renders. No layout side-effect.
  host: {
    width: '100%',
  },
  tile: {
    width: '100%',
    overflow: 'hidden',
  },
  tileImage: {
    width: '100%',
    overflow: 'hidden',
  },
  placeholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrap: {
    opacity: 0.6,
  },
});

export default ProductImage;
