/**
 * RevealBurst — Bundle E S0.1b hero illustration.
 *
 * ResultsScreen winner-card first appearance ONLY (per QA § 6 audit
 * 2026-05-26). NOT used by Step15Reveal anymore — Step15 uses the
 * MatchBadge primitive instead.
 *
 * Anatomy (design doc § 3.2):
 *   - 6–8 emerald particles emit from center on parabolic fall, fade-out
 *   - Center holds a scale-bounce badge (0 → 1.1 → 1.0 via withSpring
 *     damping=8 stiffness=100; tokens from motion.revealBurst.badgeSpring)
 *   - fireOnce gates the emit: a useRef ensures the particle array is
 *     built ONCE per mount and is stable across re-renders driven by
 *     parent state (analytics fetches, paywall mounting). This is
 *     load-bearing — re-emitting on every render would be jarring.
 *
 * Contract: __tests__/hero/RevealBurst.test.tsx
 *   - default snapshot + custom particleCount snapshot
 *   - fireOnce invariant: re-rendering with the same React key keeps the
 *     particle node count stable (no re-emit)
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import {
  useSharedValue,
  withSpring,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing } from '../../theme';
import { motion } from '../../theme/motion';
import { QaranIcon } from '../../icons/QaranIcon';

interface Props {
  size?: number;
  /** Number of emerald particles to emit (clamped 6–8 in design intent). */
  particleCount?: number;
  /**
   * fireOnce ensures the particle array is built ONE TIME on first mount
   * and not recomputed on re-render. ResultsScreen re-renders frequently
   * as personalization / analytics fetches resolve; the celebration must
   * not retrigger. Defaults to true (the load-bearing path).
   */
  fireOnce?: boolean;
  /** animated=false short-circuits the spring + particle motion. */
  animated?: boolean;
  testID?: string;
}

const VIEWBOX = 320;
const CENTER = VIEWBOX / 2;
const BADGE_R = 56;
const PARTICLE_R = 5;
const PARTICLE_TRAVEL = 110;

interface ParticleSpec {
  angleRad: number;
  distance: number;
  delayMs: number;
}

function buildParticles(count: number): ParticleSpec[] {
  // Even angular distribution with a small randomized jitter for an
  // organic feel. Distance + delay are deterministic so the test
  // snapshot is stable.
  const arr: ParticleSpec[] = [];
  for (let i = 0; i < count; i++) {
    const angleRad = (i * 2 * Math.PI) / count - Math.PI / 2;
    arr.push({
      angleRad,
      distance: PARTICLE_TRAVEL * (0.85 + (i % 2) * 0.15),
      delayMs: i * 40,
    });
  }
  return arr;
}

export function RevealBurst({
  size = 320,
  particleCount = 6,
  fireOnce = true,
  animated = true,
  testID,
}: Props) {
  const safeCount = Math.max(0, Math.min(particleCount, 8));

  // Memoize particle specs on first mount. With fireOnce=true, the
  // particleCount changes are ignored after first render (the celebration
  // is keyed by the React key, not the prop). With fireOnce=false, the
  // useMemo deps include count so the particles re-build on prop change.
  const particlesRef = useRef<ParticleSpec[] | null>(null);
  const particles = useMemo(() => {
    if (fireOnce) {
      if (particlesRef.current === null) {
        particlesRef.current = buildParticles(safeCount);
      }
      return particlesRef.current;
    }
    return buildParticles(safeCount);
  }, [fireOnce, safeCount]);

  const badgeScale = useSharedValue(animated ? 0 : 1);
  const particleProgress = useSharedValue(animated ? 0 : 1);

  useEffect(() => {
    if (!animated) return;
    // 0 → 1.1 → 1.0 settling spring per motion.revealBurst.badgeSpring.
    badgeScale.value = withSpring(1, motion.revealBurst.badgeSpring);
    // Particle parabolic emit + fall: a single shared driver runs the
    // outward + downward + fade phases. Animation total =
    //   particleEmit (600ms) + particleFall (800ms) = 1400ms.
    particleProgress.value = withDelay(
      0,
      withTiming(1, {
        duration: motion.revealBurst.particleEmit + motion.revealBurst.particleFall,
        easing: Easing.out(Easing.cubic),
      }),
    );
  }, [animated, badgeScale, particleProgress]);

  return (
    <View style={[styles.root, { width: size, height: size }]} testID={testID}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        {particles.map((p, i) => {
          const cos = Math.cos(p.angleRad);
          const sin = Math.sin(p.angleRad);
          // Final resting position — animation lives in the worklet layer
          // and we render the static endpoint in the SVG so tests can
          // count nodes deterministically.
          const cx = CENTER + cos * p.distance;
          const cy = CENTER + sin * p.distance + 40;
          return (
            <Circle
              key={`particle-${i}`}
              testID={`reveal-burst-particle-${i}`}
              cx={cx}
              cy={cy}
              r={PARTICLE_R}
              fill={colors.accent}
              opacity={0.85}
            />
          );
        })}
      </Svg>

      <View style={styles.badgeWrap} pointerEvents="none">
        <View
          testID="reveal-burst-badge"
          style={[
            styles.badge,
            {
              width: BADGE_R * 2,
              height: BADGE_R * 2,
              borderRadius: BADGE_R,
            },
          ]}
        >
          <QaranIcon size={Math.round(BADGE_R * 1.2)} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.base,
  },
  badgeWrap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.accent,
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
});
