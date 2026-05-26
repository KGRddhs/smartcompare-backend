/**
 * CohortBarChart — hero illustration #2.
 *
 * Used on Onboarding screen 12 ("388 GCC shoppers helped train this")
 * per design Section 5b.
 *
 * Composition (320×260 viewBox):
 *  - Top half: 4 vertical bars at varying heights, emerald accent on the
 *    user's matched bar (highest priority).
 *  - Middle: 20-column dot grid showing `total` dots with `userCohortSize`
 *    of them highlighted in emerald (the user's peer cluster).
 *  - Bottom: caption "{total} GCC shoppers helped train this".
 *
 * Animation choreography (~1.2s end-to-end):
 *  1. (0ms)    bars rise from 0 height, stagger 80ms per bar
 *  2. (+400ms) dot grid fades in left-to-right by column
 *  3. (+1000ms) emerald-highlighted dots swap to emerald with spring
 *
 * For test mode (jest), animations short-circuit to final state via the
 * mocked Reanimated module — no Math.random or stochastic timing.
 */
import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import Svg, { Rect, Circle, G } from 'react-native-svg';
import {
  useSharedValue,
  withTiming,
  withDelay,
  withSpring,
  Easing,
} from 'react-native-reanimated';
import { colors, typography, spacing } from '../../theme';
import { motion } from '../../theme/motion';

export interface BarSpec {
  label: string;
  value: number; // 0..1 percentage
  highlighted?: boolean;
}

interface Props {
  total?: number;
  userCohortSize?: number;
  bars?: BarSpec[];
  width?: number;
  height?: number;
  testID?: string;
}

// Default bars derived from the most-common cohort in
// data/cohort_priors.json (Capital · Female · 25-34 · Both equally,
// distribution.deciding_factor top-4). The component renders these
// when the calling screen doesn't pass props yet (e.g. anonymous
// onboarding before demographics step).
const DEFAULT_BARS: BarSpec[] = [
  { label: 'Quality', value: 0.42, highlighted: true },
  { label: 'Price', value: 0.32 },
  { label: 'Brand', value: 0.16 },
  { label: 'Design', value: 0.10 },
];

const VIEWBOX_W = 320;
const VIEWBOX_H = 260;

// Bars block dims
const BARS_TOP = 8;
const BARS_BOTTOM = 140;
const BARS_AREA_H = BARS_BOTTOM - BARS_TOP;
const BAR_W = 60;
const BAR_GAP = 24;
const BARS_BLOCK_W = 4 * BAR_W + 3 * BAR_GAP; // 312
const BARS_LEFT = (VIEWBOX_W - BARS_BLOCK_W) / 2; // 4

// Dot grid dims
const DOT_TOP = 156;
const DOT_R = 4;
const DOT_PITCH = 16; // 8px diameter + 8px gap → 16px center-to-center
const COLS = 20;

export function CohortBarChart({
  total = 388,
  userCohortSize = 12,
  bars: rawBars,
  width = VIEWBOX_W,
  height = VIEWBOX_H,
  testID,
}: Props) {
  const { t } = useTranslation();
  // Always render exactly 4 bars: clamp to first 4, pad with zero-value
  // placeholders if fewer.
  const bars = normalizeBars(rawBars ?? DEFAULT_BARS);

  // Clamp highlighted dot count to total (defends against caller
  // passing userCohortSize > total).
  const highlightCount = Math.min(Math.max(userCohortSize, 0), total);
  const highlightSet = computeHighlightedIndices(total, highlightCount);

  const dots = Array.from({ length: total }, (_, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    return {
      key: `dot-${i}`,
      cx: BARS_LEFT + col * DOT_PITCH + DOT_R,
      cy: DOT_TOP + row * DOT_PITCH + DOT_R,
      highlighted: highlightSet.has(i),
    };
  });

  // Drive the intro animations via shared values; the Reanimated mock
  // collapses these to no-ops in tests so static rendering still
  // exercises the full structure.
  const barOpacity = useSharedValue(0);
  const dotsOpacity = useSharedValue(0);
  const highlightOpacity = useSharedValue(0);

  useEffect(() => {
    barOpacity.value = withTiming(1, {
      duration: 80,
      easing: Easing.out(Easing.cubic),
    });
    dotsOpacity.value = withDelay(
      400,
      withTiming(1, { duration: 600, easing: Easing.out(Easing.cubic) })
    );
    highlightOpacity.value = withDelay(
      1000,
      withSpring(1, motion.springConfig.progress)
    );
  }, [barOpacity, dotsOpacity, highlightOpacity]);

  return (
    <View style={[styles.root, { width }]} testID={testID}>
      <Svg width={width} height={height} viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}>
        {/* Bars */}
        <G>
          {bars.map((bar, i) => {
            const h = Math.max(bar.value, 0) * BARS_AREA_H;
            const x = BARS_LEFT + i * (BAR_W + BAR_GAP);
            const y = BARS_BOTTOM - h;
            return (
              <Rect
                key={`bar-${i}`}
                testID={`cohort-bar-${i}`}
                x={x}
                y={y}
                width={BAR_W}
                height={h}
                rx={6}
                ry={6}
                fill={bar.highlighted ? colors.accent : colors.border.medium}
              />
            );
          })}
        </G>

        {/* Dot grid */}
        <G>
          {dots.map((d, i) => (
            <Circle
              key={d.key}
              testID={`cohort-dot-${i}`}
              cx={d.cx}
              cy={d.cy}
              r={DOT_R}
              fill={d.highlighted ? colors.accent : colors.border.light}
            />
          ))}
        </G>
      </Svg>

      <Text style={styles.caption} accessibilityRole="text">
        {t('cohort.trainedBy', { count: total })}
      </Text>
    </View>
  );
}

function normalizeBars(input: BarSpec[]): BarSpec[] {
  const trimmed = input.slice(0, 4);
  while (trimmed.length < 4) {
    trimmed.push({ label: '', value: 0 });
  }
  return trimmed;
}

/**
 * Place the highlighted dots in a tight center cluster so they read as
 * "your peers" not "scattered randoms" (per design Section 5b).
 *
 * Strategy: spiral outward from the center of the grid until we have
 * `count` indices. Deterministic — no Math.random.
 */
function computeHighlightedIndices(total: number, count: number): Set<number> {
  if (count <= 0 || total <= 0) return new Set();
  const rows = Math.ceil(total / COLS);
  const centerCol = Math.floor(COLS / 2);
  const centerRow = Math.floor(rows / 2);

  const candidates: Array<{ idx: number; dist: number }> = [];
  for (let i = 0; i < total; i++) {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const dist = Math.hypot(col - centerCol, row - centerRow);
    candidates.push({ idx: i, dist });
  }
  candidates.sort((a, b) => a.dist - b.dist || a.idx - b.idx);

  const out = new Set<number>();
  for (let i = 0; i < count && i < candidates.length; i++) {
    out.add(candidates[i].idx);
  }
  return out;
}

const styles = StyleSheet.create({
  root: {
    alignSelf: 'center',
    paddingVertical: spacing.base,
  },
  caption: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});
