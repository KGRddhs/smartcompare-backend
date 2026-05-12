/**
 * Dual image-slot row for ScanCameraScreen.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React from 'react';
import { View, Image, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { X } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii } from '../theme';

export type Slot = { uri: string } | null;
export type Slots = [Slot, Slot];

type Props = {
  slots: Slots;
  onChange: (next: Slots) => void;
};

export default function ImageSlotRow({ slots, onChange }: Props) {
  const { t } = useTranslation();
  const remove = (idx: 0 | 1) => {
    const next: Slots = [slots[0], slots[1]];
    next[idx] = null;
    onChange(next);
  };

  return (
    <View style={styles.row}>
      {([0, 1] as const).map((idx) => {
        const slot = slots[idx];
        const slotNumber = idx + 1;
        return (
          <View
            key={idx}
            testID={`image-slot-${idx}`}
            style={styles.slot}
            accessibilityLabel={t('home.camera.a11y.slot', { count: slotNumber })}
            accessible
          >
            {slot ? (
              <>
                <Image
                  testID={`image-slot-${idx}-thumb`}
                  source={{ uri: slot.uri }}
                  style={styles.thumb}
                />
                <TouchableOpacity
                  testID={`image-slot-${idx}-remove`}
                  style={styles.remove}
                  onPress={() => remove(idx)}
                  accessibilityRole="button"
                  accessibilityLabel={t('home.camera.a11y.slotRemove', {
                    count: slotNumber,
                  })}
                  // qa-bcd a11y review — the visible × is 24×24; hitSlop=12
                  // brings the effective tap target to 48×48 so we clear the
                  // 44pt minimum on both iOS and Android.
                  hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                >
                  <X size={14} color={colors.text.onInverse} />
                </TouchableOpacity>
              </>
            ) : (
              <Text style={styles.placeholder}>{slotNumber}</Text>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    padding: spacing.base,
  },
  slot: {
    width: 80,
    height: 80,
    borderRadius: radii.button,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.5)',
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  thumb: {
    width: '100%',
    height: '100%',
    borderRadius: radii.button,
  },
  placeholder: {
    color: colors.text.onInverse,
    fontSize: 32,
    fontWeight: '300',
  },
  remove: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: 'rgba(0,0,0,0.7)',
    borderRadius: 12,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
