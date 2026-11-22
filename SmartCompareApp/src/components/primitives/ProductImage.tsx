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
 * INC-C1b T7-09: the first onError shows the placeholder at once and arms ONE
 * retry 1.5 s later (a fresh <Image> of the same uri; a slow first byte or a
 * CDN blip no longer leaves the placeholder for the life of the mount). An
 * error on the retry is final and leaves one host-only Sentry breadcrumb.
 * A url change or an unmount clears a pending retry; a new url gets its own.
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
import {
  Image,
  ImageResizeMode,
  ImageStyle,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';
import Svg, { Line, Rect } from 'react-native-svg';

import { colors } from '../../theme';
import { addImageLoadBreadcrumb } from '../../services/sentry';

const DEFAULT_TONE = '#EEEFF4';
// INC-C1b T7-09: the one retry of a failed image waits this long.
const RETRY_DELAY_MS = 1500;

interface Props {
  imageUrl?: string | null;
  placeholderTone?: string;
  aspectRatio?: number;
  borderRadius?: number;
  /**
   * How the loaded image should fit inside its square tile. Defaults to
   * `'cover'` (matches previous behavior) — pass `'contain'` for product
   * hero cards where the full photo must fit without crop and the
   * placeholder tone is intended to show as a neutral letterbox.
   */
  resizeMode?: ImageResizeMode;
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
  resizeMode = 'cover',
  testID,
  style,
}: Props) {
  const [errored, setErrored] = React.useState(false);
  // INC-C1b T7-09: 0 = the first load, 1 = the one retry; the pending retry
  // timer (one at most). Refs, so a late or doubled onError reads them live.
  const attemptRef = React.useRef(0);
  const retryTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset error state when the imageUrl prop changes — a new URL deserves
  // a fresh attempt (race: a SSE update arrives after an earlier broken URL).
  // INC-C1b: the new URL gets its own retry; the cleanup (a url change or an
  // unmount) clears a pending retry timer.
  React.useEffect(() => {
    setErrored(false);
    attemptRef.current = 0;
    const timerRef = retryTimerRef;
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [imageUrl]);

  const onImageError = () => {
    // A doubled native error while the retry is pending arms nothing more.
    if (retryTimerRef.current !== null) return;
    setErrored(true);
    if (attemptRef.current === 0) {
      // The placeholder shows now; one fresh <Image> of the same uri later.
      retryTimerRef.current = setTimeout(() => {
        retryTimerRef.current = null;
        attemptRef.current = 1;
        setErrored(false);
      }, RETRY_DELAY_MS);
      return;
    }
    // The retry failed too: the placeholder stays for good.
    try {
      addImageLoadBreadcrumb(imageUrl as string);
    } catch {
      // A breadcrumb (or a test mock without it) must never break the tile.
    }
  };

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
      <View
        testID={testID}
        style={[styles.host, { aspectRatio, borderRadius, backgroundColor: placeholderTone, overflow: 'hidden' }]}
      >
        <Image
          testID={testID ? `${testID}-img` : undefined}
          source={{ uri: imageUrl as string }}
          accessibilityRole="image"
          onError={onImageError}
          resizeMode={resizeMode}
          // M21 MB-perf-08 — og:image sources are routinely 1000-2400px
          // while every consumer renders a 64-160px tile. On Android,
          // Fresco only downsamples the DECODE when resizeMethod="resize"
          // is set; the default decodes the full bitmap and GPU-scales it,
          // so a History screen could hold ~100 multi-megapixel bitmaps.
          // iOS ignores the prop (no-op).
          resizeMethod="resize"
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
    height: '100%',
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
