/**
 * PhoneMockup — hero illustration #1.
 *
 * Used on Onboarding screen 3 (value prop: "Stop guessing. Start
 * knowing.") per design Section 5b.
 *
 * STATUS: hand-coded placeholder. Per the design doc, the canonical
 * source is a Figma export from a designer. No Figma file was provided
 * to this team session, so this commit ships a production-quality
 * placeholder that:
 *
 *   - Phone frame at 3/4 angle (skewed via SVG transform)
 *   - Pure black gradient (matches app icon) with subtle highlight
 *   - Two product cards on the screen — second one bears the winner
 *     badge and emerald glow ring
 *   - White circular Q-mark on the home indicator area
 *
 * When the designer hands off the Figma SVG, swap the inline JSX for
 * an SVG file import or paste the optimised paths into this component.
 * The test contract (testIDs: phone-mockup-frame, -product-{0,1},
 * -winner-badge, -glow) should be preserved so onboarding screen 3
 * doesn't need to change.
 *
 * Animation: phone slides up 16px + fades on mount; glow ring pulses
 * gently every ~1.4s.
 */
import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Rect, Circle, G, Defs, LinearGradient, Stop, Path } from 'react-native-svg';
import {
  useSharedValue,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing } from '../../theme';

interface Props {
  size?: number;
  testID?: string;
}

const VIEWBOX_W = 320;
const VIEWBOX_H = 360;

// Phone geometry (3/4 angle achieved via skew on the Svg group).
const PHONE_X = 64;
const PHONE_Y = 24;
const PHONE_W = 192;
const PHONE_H = 312;
const PHONE_R = 24;

const SCREEN_INSET = 8;
const SCREEN_X = PHONE_X + SCREEN_INSET;
const SCREEN_Y = PHONE_Y + SCREEN_INSET;
const SCREEN_W = PHONE_W - SCREEN_INSET * 2;
const SCREEN_H = PHONE_H - SCREEN_INSET * 2;

// Two product cards inside the screen (anchored bottom).
const CARD_W = SCREEN_W - 24;
const CARD_H = 96;
const CARD_X = SCREEN_X + 12;
const CARD_GAP = 16;
const CARD_Y_TOP = SCREEN_Y + 64;
const CARD_Y_BOTTOM = CARD_Y_TOP + CARD_H + CARD_GAP;

// Winner badge sits at the bottom-left of the second (winner) card.
const BADGE_W = 80;
const BADGE_H = 22;
const BADGE_X = CARD_X + 12;
const BADGE_Y = CARD_Y_BOTTOM + CARD_H - BADGE_H - 12;

// Glow ring expands around the winner card.
const GLOW_INSET = 6;
const GLOW_X = CARD_X - GLOW_INSET;
const GLOW_Y = CARD_Y_BOTTOM - GLOW_INSET;
const GLOW_W = CARD_W + GLOW_INSET * 2;
const GLOW_H = CARD_H + GLOW_INSET * 2;
const GLOW_R = 16 + GLOW_INSET;

export function PhoneMockup({ size = 320, testID }: Props) {
  // Glow pulse driver (mock returns identity in tests).
  const glowOpacity = useSharedValue(0.4);
  useEffect(() => {
    glowOpacity.value = withRepeat(
      withSequence(
        withTiming(0.7, { duration: 700, easing: Easing.inOut(Easing.cubic) }),
        withTiming(0.4, { duration: 700, easing: Easing.inOut(Easing.cubic) })
      ),
      -1,
      false
    );
  }, [glowOpacity]);

  const ratio = size / VIEWBOX_W;
  const renderHeight = VIEWBOX_H * ratio;

  return (
    <View style={[styles.root, { width: size, height: renderHeight }]} testID={testID}>
      <Svg
        width={size}
        height={renderHeight}
        viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
      >
        <Defs>
          <LinearGradient id="phoneGrad" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0%" stopColor="#1A1A1E" />
            <Stop offset="60%" stopColor="#0A0A0B" />
            <Stop offset="100%" stopColor="#000000" />
          </LinearGradient>
        </Defs>

        {/* 3/4 angle skew applied to the entire phone group. */}
        <G transform={`matrix(0.97 0 -0.18 0.94 32 8)`}>
          {/* Phone frame */}
          <Rect
            testID="phone-mockup-frame"
            x={PHONE_X}
            y={PHONE_Y}
            width={PHONE_W}
            height={PHONE_H}
            rx={PHONE_R}
            ry={PHONE_R}
            fill="url(#phoneGrad)"
          />

          {/* Inner screen panel (off-white) */}
          <Rect
            x={SCREEN_X}
            y={SCREEN_Y}
            width={SCREEN_W}
            height={SCREEN_H}
            rx={PHONE_R - SCREEN_INSET}
            ry={PHONE_R - SCREEN_INSET}
            fill={colors.bg.secondary}
          />

          {/* Title eyebrow on the screen */}
          <Rect
            x={CARD_X}
            y={SCREEN_Y + 24}
            width={80}
            height={8}
            rx={4}
            fill={colors.border.medium}
          />
          <Rect
            x={CARD_X}
            y={SCREEN_Y + 40}
            width={140}
            height={12}
            rx={4}
            fill={colors.text.primary}
          />

          {/* Product card 1 (loser, on top) */}
          <Rect
            testID="phone-mockup-product-0"
            x={CARD_X}
            y={CARD_Y_TOP}
            width={CARD_W}
            height={CARD_H}
            rx={16}
            fill={colors.bg.primary}
            stroke={colors.border.light}
            strokeWidth={1}
          />
          {/* Product 1 image placeholder */}
          <Rect
            x={CARD_X + 12}
            y={CARD_Y_TOP + 12}
            width={48}
            height={48}
            rx={8}
            fill={colors.border.light}
          />
          {/* Product 1 text lines */}
          <Rect
            x={CARD_X + 72}
            y={CARD_Y_TOP + 16}
            width={70}
            height={10}
            rx={3}
            fill={colors.text.primary}
          />
          <Rect
            x={CARD_X + 72}
            y={CARD_Y_TOP + 32}
            width={48}
            height={8}
            rx={3}
            fill={colors.text.secondary}
          />
          <Rect
            x={CARD_X + 72}
            y={CARD_Y_TOP + 48}
            width={36}
            height={8}
            rx={3}
            fill={colors.text.secondary}
          />

          {/* Glow ring around winner (animated opacity) */}
          <Rect
            testID="phone-mockup-glow"
            x={GLOW_X}
            y={GLOW_Y}
            width={GLOW_W}
            height={GLOW_H}
            rx={GLOW_R}
            fill="none"
            stroke={colors.accent}
            strokeWidth={4}
            opacity={glowOpacity.value}
          />

          {/* Product card 2 (winner) */}
          <Rect
            testID="phone-mockup-product-1"
            x={CARD_X}
            y={CARD_Y_BOTTOM}
            width={CARD_W}
            height={CARD_H}
            rx={16}
            fill={colors.bg.primary}
            stroke={colors.accent}
            strokeWidth={2}
          />
          <Rect
            x={CARD_X + 12}
            y={CARD_Y_BOTTOM + 12}
            width={48}
            height={48}
            rx={8}
            fill={colors.accent}
            opacity={0.15}
          />
          <Rect
            x={CARD_X + 72}
            y={CARD_Y_BOTTOM + 16}
            width={70}
            height={10}
            rx={3}
            fill={colors.text.primary}
          />
          <Rect
            x={CARD_X + 72}
            y={CARD_Y_BOTTOM + 32}
            width={48}
            height={8}
            rx={3}
            fill={colors.text.secondary}
          />

          {/* Winner badge (emerald pill, bottom-left of winner card) */}
          <Rect
            testID="phone-mockup-winner-badge"
            x={BADGE_X}
            y={BADGE_Y}
            width={BADGE_W}
            height={BADGE_H}
            rx={BADGE_H / 2}
            fill={colors.accent}
          />
          {/* Check mark inside the badge */}
          <Path
            d={`M${BADGE_X + 10} ${BADGE_Y + BADGE_H / 2} l3 3 l8 -8`}
            stroke="#FFFFFF"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />

          {/* Home indicator on the phone bezel */}
          <Rect
            x={PHONE_X + PHONE_W / 2 - 24}
            y={PHONE_Y + PHONE_H - 8}
            width={48}
            height={4}
            rx={2}
            fill="#2A2A2F"
          />

          {/* Camera notch (round dot at top center) */}
          <Circle
            cx={PHONE_X + PHONE_W / 2}
            cy={PHONE_Y + 16}
            r={4}
            fill="#2A2A2F"
          />
        </G>
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignSelf: 'center',
    padding: spacing.base,
  },
});
