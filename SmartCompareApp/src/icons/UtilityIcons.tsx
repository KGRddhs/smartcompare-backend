import React from 'react';
import Svg, { Path } from 'react-native-svg';

/**
 * 6 custom utility icons (Phase 1 Task 5).
 *
 * Style contract per design Section 5a:
 * - Filled mono, no strokes (stroke="none", fill={color})
 * - 24×24 viewBox base; size prop scales linearly
 * - Rounded line ends and corners (achieved via geometry, not stroke
 *   linecap, since these are filled paths)
 * - Default color #0A0A0B (the design black). Override via prop.
 *
 * BackIcon flips for RTL via icons/index → flipForRTL helper.
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

// ── BackIcon ── chunky chevron pointing left.
// Path uses a filled wedge (geometric panel, ~4px corner radius via curves).
export const BackIcon = makeIcon((c) => (
  <Path
    d="M14.7 4.3a1.5 1.5 0 0 1 0 2.1L9.6 12l5.1 5.6a1.5 1.5 0 1 1-2.2 2.1l-6-6.6a1.5 1.5 0 0 1 0-2.1l6-6.6a1.5 1.5 0 0 1 2.2 0z"
    fill={c}
    stroke="none"
  />
));

// ── CloseIcon ── two filled bars crossing at the center, ~2px corner radius.
export const CloseIcon = makeIcon((c) => (
  <Path
    d="M19.3 5.8a1.5 1.5 0 0 0-2.1-2.1L12 9 6.8 3.7a1.5 1.5 0 1 0-2.1 2.1L9.9 11 4.7 16.2a1.5 1.5 0 1 0 2.1 2.1L12 13l5.2 5.3a1.5 1.5 0 1 0 2.1-2.1L14.1 11l5.2-5.2z"
    fill={c}
    stroke="none"
  />
));

// ── SearchIcon ── chunky filled magnifier (similar grammar to QaranIcon
// but heavier; QaranIcon stays an outlined ring as a brand mark).
export const SearchIcon = makeIcon((c) => (
  <Path
    d="M10 3.5a6.5 6.5 0 1 0 4.05 11.6l4.42 4.42a1.5 1.5 0 1 0 2.13-2.12l-4.43-4.43A6.5 6.5 0 0 0 10 3.5zm0 3a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z"
    fill={c}
    stroke="none"
  />
));

// ── BellIcon ── filled bell silhouette + clapper ball (Cal-AI weight).
export const BellIcon = makeIcon((c) => (
  <Path
    d="M12 2.5c-.83 0-1.5.67-1.5 1.5v.6A6.5 6.5 0 0 0 5.5 11v3.4l-1.4 1.6a1.4 1.4 0 0 0 1 2.4h13.8a1.4 1.4 0 0 0 1-2.4l-1.4-1.6V11a6.5 6.5 0 0 0-5-6.4V4c0-.83-.67-1.5-1.5-1.5zM10 20.5a2 2 0 0 0 4 0h-4z"
    fill={c}
    stroke="none"
  />
));

// ── SettingsIcon ── 8-tooth gear, filled.
export const SettingsIcon = makeIcon((c) => (
  <Path
    d="M19.4 13.0a1 1 0 0 0 .2-1.0v-.0c0-.34-.04-.66-.1-1l1.74-1.36a.5.5 0 0 0 .12-.62l-1.65-2.86a.5.5 0 0 0-.6-.22l-2.05.82c-.5-.4-1.06-.74-1.66-.98l-.32-2.18A.5.5 0 0 0 14.6 3h-3.3a.5.5 0 0 0-.5.42L10.5 5.6c-.6.24-1.16.58-1.66.98L6.8 5.76a.5.5 0 0 0-.6.22L4.55 8.84a.5.5 0 0 0 .12.62L6.4 10.82c-.06.34-.1.66-.1 1l.0.0c0 .34.04.66.1 1L4.67 14.18a.5.5 0 0 0-.12.62l1.65 2.86a.5.5 0 0 0 .6.22l2.05-.82c.5.4 1.06.74 1.66.98l.32 2.18a.5.5 0 0 0 .5.42h3.3a.5.5 0 0 0 .5-.42l.32-2.18c.6-.24 1.16-.58 1.66-.98l2.05.82a.5.5 0 0 0 .6-.22l1.65-2.86a.5.5 0 0 0-.12-.62L19.4 13.0zM12 15.4a3.4 3.4 0 1 1 0-6.8 3.4 3.4 0 0 1 0 6.8z"
    fill={c}
    stroke="none"
  />
));

// ── PlusIcon ── two filled bars crossing, 2px rounded ends.
export const PlusIcon = makeIcon((c) => (
  <Path
    d="M13.5 4.5a1.5 1.5 0 0 0-3 0v6h-6a1.5 1.5 0 0 0 0 3h6v6a1.5 1.5 0 0 0 3 0v-6h6a1.5 1.5 0 0 0 0-3h-6v-6z"
    fill={c}
    stroke="none"
  />
));
