import React from 'react';
import Svg, { Circle, Line } from 'react-native-svg';

/**
 * Qaran brand mark — Q rendered as a magnifying glass.
 *
 * Composition (24×24 grid):
 * - Open circle ring (the lens) at (10, 10), radius 6
 * - Diagonal handle from (14.2, 14.2) to (20, 20)
 * - Filled dot at the handle tip (20, 20) — echoes the Q tail and
 *   gives the magnifier its inspectional weight
 *
 * Rendered as a single mono color so it can sit on white surfaces
 * (color="#0A0A0B" default), on the black hero surface (color="#FFFFFF"),
 * or as the emerald cohort accent (color="#10B981").
 */
interface Props {
  size?: number;
  color?: string;
  testID?: string;
}

export function QaranIcon({ size = 24, color = '#0A0A0B', testID }: Props) {
  const stroke = Math.max(1.5, size * (2.5 / 24));
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" testID={testID}>
      <Circle
        cx="10"
        cy="10"
        r="6"
        stroke={color}
        strokeWidth={stroke}
        fill="none"
      />
      <Line
        x1="14.2"
        y1="14.2"
        x2="20"
        y2="20"
        stroke={color}
        strokeWidth={stroke}
        strokeLinecap="round"
      />
      <Circle cx="20" cy="20" r={stroke * 0.6} fill={color} />
    </Svg>
  );
}

export default QaranIcon;
