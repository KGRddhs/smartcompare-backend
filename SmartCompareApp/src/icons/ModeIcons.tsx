import React from 'react';
import Svg, { Path, Rect } from 'react-native-svg';

/**
 * 3 mode icons for HomeScreen's 3-equal-chip mode selector
 * (Scan / Link / Type) per design § 5a "Mode | 3".
 *
 * Style contract (matches UtilityIcons grammar):
 * - Filled mono, no strokes (stroke="none", fill={color})
 * - 24×24 viewBox base; size prop scales linearly
 * - Default color #0A0A0B (the design black)
 *
 * Drop-in compatible with the Lucide icons currently used on the
 * HomeScreen mode chips — same `size` and `color` props, same default.
 */
interface IconProps {
  size?: number;
  color?: string;
  testID?: string;
}

function makeIcon(
  paths: (color: string) => React.ReactNode
): React.FC<IconProps> {
  const Component: React.FC<IconProps> = ({
    size = 24,
    color = '#0A0A0B',
    testID,
  }) => (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      testID={testID}
    >
      {paths(color)}
    </Svg>
  );
  return Component;
}

// ── ScanIcon ── viewfinder corners + center dot. Reads as "scan a
// product with the camera" without depicting a literal camera body
// (that's the permission-card hero domain).
export const ScanIcon = makeIcon((c) => (
  <>
    {/* 4 corner brackets, 5px long, 2px thick, rounded inner corners */}
    {/* Top-left */}
    <Path
      d="M3 7.5V5a2 2 0 0 1 2-2h2.5v2H5v2.5zM21 7.5V5a2 2 0 0 0-2-2h-2.5v2H19v2.5z"
      fill={c}
      stroke="none"
    />
    {/* Bottom corners (mirror) */}
    <Path
      d="M3 16.5V19a2 2 0 0 0 2 2h2.5v-2H5v-2.5zM21 16.5V19a2 2 0 0 1-2 2h-2.5v-2H19v-2.5z"
      fill={c}
      stroke="none"
    />
    {/* Center dot — the "subject" */}
    <Path
      d="M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z"
      fill={c}
      stroke="none"
    />
  </>
));

// ── LinkIcon ── two interlocking link halves at 45° angle. Distinct
// from Lucide's Link2 which renders horizontally — this matches the
// "paste a URL" affordance.
export const LinkIcon = makeIcon((c) => (
  <Path
    d="M9.6 14.4l4.8-4.8a1.5 1.5 0 1 1 2.12 2.12l-2.12 2.12a1 1 0 1 0 1.42 1.42l2.12-2.12a3.5 3.5 0 1 0-4.95-4.95l-4.8 4.8a1 1 0 1 0 1.41 1.41zm4.8-4.8l-4.8 4.8a1.5 1.5 0 1 1-2.12-2.12l2.12-2.12a1 1 0 1 0-1.42-1.42L6.06 10.86a3.5 3.5 0 1 0 4.95 4.95l4.8-4.8a1 1 0 1 0-1.41-1.41z"
    fill={c}
    stroke="none"
  />
));

// ── TypeIcon ── classic "T" letterform on a baseline tick. Matches
// the "type a query" affordance — distinct from a search magnifier.
export const TypeIcon = makeIcon((c) => (
  <>
    {/* T crossbar */}
    <Rect x={4} y={5} width={16} height={3} rx={1.5} fill={c} />
    {/* T stem */}
    <Rect x={10.5} y={6.5} width={3} height={11} rx={1} fill={c} />
    {/* Baseline tick (gives the glyph an "input" feel rather than just a letter) */}
    <Rect x={5} y={18.5} width={14} height={1.6} rx={0.8} fill={c} />
  </>
));
