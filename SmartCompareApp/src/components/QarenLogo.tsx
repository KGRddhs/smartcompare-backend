/**
 * QarenLogo — brand-glyph SVG.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated.md § Task 2.10
 *
 * A simple Q-with-tail mark plus an emerald accent dot at the top-right
 * of the ring. The accent dot is the Bundle A signal-color "one drop"
 * rule made literal — the rest of the app stays monochrome black/white
 * unless something earns the emerald (winner reveal, success tick,
 * cohort accent).
 *
 * Replaces the plain text "Qaren" header in Home / Profile / History /
 * Splash. Pre-launch ships glyph + wordmark together; glyph-only is a
 * later iteration once recognition lands.
 */
import React from 'react';
import Svg, { Circle, Path, G } from 'react-native-svg';
import { colors } from '../theme';

type Props = {
  size?: number;
  color?: string;
};

export default function QarenLogo({
  size = 32,
  color = colors.text.primary,
}: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <G>
        {/* Q-ring */}
        <Circle
          cx={16}
          cy={16}
          r={13}
          stroke={color}
          strokeWidth={2.5}
          fill="none"
        />
        {/* Q-tail */}
        <Path
          d="M22 22 L27 27"
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        {/* Emerald accent dot — Bundle A signal-color anchor. */}
        <Circle cx={22} cy={11} r={2} fill={colors.accent} />
      </G>
    </Svg>
  );
}
