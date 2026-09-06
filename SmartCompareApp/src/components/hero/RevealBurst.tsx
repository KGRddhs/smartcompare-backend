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
 * A10 (mobile checkup, 2026-09-05) — the two shared values below used to be
 * WRITE-ONLY: `badgeScale` and `particleProgress` were driven by the effect
 * but never read by anything that renders, so the celebration shipped as a
 * frozen tableau — six emerald dots parked at their resting position at a
 * flat 0.85 opacity, plus a badge with no scale at all. Because the burst is
 * mounted into an absolute-fill slot over the DimensionBars card and is never
 * unmounted, that tableau then sat over the bars for the life of the screen.
 * Both drivers are now BOUND to render:
 *   - each particle is an `Animated.createAnimatedComponent(Circle)` whose
 *     cx/cy/opacity come from `useAnimatedProps` off `particleProgress`
 *   - the badge is an `Animated.View` scaled by `useAnimatedStyle`
 * The resting geometry is unchanged (progress 1 lands on exactly the old
 * static endpoint), so the only visual deltas are the motion itself and the
 * designed fade-out, which also retires the persistent overlay.
 *
 * Contract: __tests__/hero/RevealBurst.test.tsx (snapshots + fireOnce)
 *           __tests__/hero/RevealBurst.animation.test.tsx (driver binding)
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  useAnimatedStyle,
  withSpring,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
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
/** Peak particle opacity, held until the fade phase begins. */
const PARTICLE_OPACITY = 0.85;
/**
 * Downward drop (px) a particle accumulates by the end of the fall. Equal to
 * the constant `+ 40` the pre-A10 static render baked into cy, so the resting
 * position of every particle is byte-identical to what shipped before.
 */
const PARTICLE_FALL = 40;
/** Driver fraction after which a particle fades out (design § 3.2). */
const PARTICLE_FADE_START = 0.55;
/** Whole-burst duration; the outward emit owns the first EMIT_FRACTION of it. */
const DRIVER_MS =
  motion.revealBurst.particleEmit + motion.revealBurst.particleFall;
const EMIT_FRACTION = motion.revealBurst.particleEmit / DRIVER_MS;

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

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

interface ParticleProps {
  index: number;
  spec: ParticleSpec;
  progress: SharedValue<number>;
}

/**
 * One emerald particle, bound to the shared burst driver.
 *
 * Extracted as its own component ONLY because hooks cannot be called inside
 * `particles.map()`. It renders a single Circle, so the host tree shape is
 * identical to the pre-A10 inline map.
 */
function Particle({ index, spec, progress }: ParticleProps) {
  // Resolve the endpoint offsets to primitives up front so the worklet
  // closes over plain numbers rather than the spec object.
  const dx = Math.cos(spec.angleRad) * spec.distance;
  const dy = Math.sin(spec.angleRad) * spec.distance;
  const delayMs = spec.delayMs;

  const animatedProps = useAnimatedProps(() => {
    // Per-particle stagger. `delayMs` shifts only the START: at progress 0
    // every particle is at the centre, at progress 1 every particle is at
    // its resting position, whatever its delay.
    const t = Math.min(
      1,
      Math.max(
        0,
        (progress.value * DRIVER_MS - delayMs) /
          Math.max(1, DRIVER_MS - delayMs),
      ),
    );
    // The outward emit completes inside the emit phase; gravity keeps
    // accumulating across the whole driver, which is what makes the path
    // parabolic rather than a straight radial slide.
    const out = t < EMIT_FRACTION ? t / EMIT_FRACTION : 1;
    const fade =
      t <= PARTICLE_FADE_START
        ? 1
        : 1 - (t - PARTICLE_FADE_START) / (1 - PARTICLE_FADE_START);
    return {
      cx: CENTER + dx * out,
      cy: CENTER + dy * out + PARTICLE_FALL * t * t,
      opacity: PARTICLE_OPACITY * fade,
    };
  });

  return (
    <AnimatedCircle
      testID={`reveal-burst-particle-${index}`}
      r={PARTICLE_R}
      fill={colors.accent}
      animatedProps={animatedProps}
    />
  );
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
        duration: DRIVER_MS,
        easing: Easing.out(Easing.cubic),
      }),
    );
  }, [animated, badgeScale, particleProgress]);

  const badgeStyle = useAnimatedStyle(() => ({
    transform: [{ scale: badgeScale.value }],
  }));

  return (
    <View style={[styles.root, { width: size, height: size }]} testID={testID}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        {particles.map((p, i) => (
          <Particle
            key={`particle-${i}`}
            index={i}
            spec={p}
            progress={particleProgress}
          />
        ))}
      </Svg>

      <View style={styles.badgeWrap} pointerEvents="none">
        <Animated.View
          testID="reveal-burst-badge"
          style={[
            styles.badge,
            {
              width: BADGE_R * 2,
              height: BADGE_R * 2,
              borderRadius: BADGE_R,
            },
            badgeStyle,
          ]}
        >
          <QaranIcon size={Math.round(BADGE_R * 1.2)} />
        </Animated.View>
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
