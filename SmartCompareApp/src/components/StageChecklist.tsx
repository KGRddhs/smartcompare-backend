/**
 * StageChecklist — vertical multi-stage progress with haptic ticks.
 *
 * Phase 2 Task 11. Used on Results loading screen and onboarding screen 14
 * (theatrical loading). 5 rows by convention but accepts any count. Each
 * row shows ✓ done (emerald) / ⟳ active (emerald) / ○ pending (gray).
 *
 * Haptic light fires when a stage transitions FROM not-done TO done. We
 * never fire on initial mount for stages that started as done (no
 * surprise vibration when the screen renders cached state).
 *
 * Copy comes from the parent (the orchestrator picks the right i18n key
 * for the current SSE stage); this component is purely presentational.
 */

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, typography } from '../theme';

export type StageStatus = 'pending' | 'active' | 'done';

export interface Stage {
  id: string;
  label: string;
  status: StageStatus;
}

interface StageChecklistProps {
  stages: Stage[];
}

const GLYPH: Record<StageStatus, string> = {
  done: '\u2713', // ✓
  active: '\u27F3', // ⟳
  pending: '\u25CB', // ○
};

export function StageChecklist({ stages }: StageChecklistProps) {
  const prevStatuses = useRef<Record<string, StageStatus>>({});

  useEffect(() => {
    for (const s of stages) {
      const prev = prevStatuses.current[s.id];
      // Fire only on transition into done — never on initial mount of a
      // stage that started as 'done' (cached-state render must not vibrate).
      if (prev !== undefined && prev !== 'done' && s.status === 'done') {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {
          // Haptics best-effort. Phase 5 a11y honors reduced-motion at OS level.
        });
      }
      prevStatuses.current[s.id] = s.status;
    }
  }, [stages]);

  return (
    <View style={styles.list}>
      {stages.map((s) => (
        <View key={s.id} style={styles.row}>
          <View
            testID={`stage-${s.id}-icon`}
            accessibilityLabel={s.status}
            accessibilityRole="image"
            style={[styles.iconWrap, iconWrapStyle(s.status)]}
          >
            <Text
              testID={`stage-${s.id}-glyph`}
              style={[styles.glyph, glyphStyle(s.status)]}
            >
              {GLYPH[s.status]}
            </Text>
          </View>
          <Text style={[styles.label, labelStyle(s.status)]}>{s.label}</Text>
        </View>
      ))}
    </View>
  );
}

function iconWrapStyle(status: StageStatus) {
  if (status === 'done' || status === 'active') {
    return { backgroundColor: colors.accentLight };
  }
  return { backgroundColor: colors.bg.secondary };
}

function glyphStyle(status: StageStatus) {
  if (status === 'pending') {
    return { color: colors.text.placeholder };
  }
  return { color: colors.accent };
}

function labelStyle(status: StageStatus) {
  return { color: status === 'pending' ? colors.text.secondary : colors.text.primary };
}

const ICON_SIZE = 24;

const styles = StyleSheet.create({
  list: {
    paddingVertical: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  iconWrap: {
    width: ICON_SIZE,
    height: ICON_SIZE,
    borderRadius: ICON_SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
    // marginEnd auto-flips with writing direction so the gap stays
    // between the icon and its label under both LTR and RTL.
    marginEnd: spacing.md,
  },
  glyph: {
    ...typography.caption,
    fontWeight: '600',
  },
  label: {
    ...typography.body,
    flex: 1,
  },
});
