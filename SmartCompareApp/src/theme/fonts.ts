/**
 * Qaren typography fonts.
 *
 * EN voice: Geist (local TTF, SIL OFL v1.1, ~125KB per weight)
 * AR voice: Cairo (Google Fonts via @expo-google-fonts/cairo)
 *
 * Phase 1 visual swap — Inter retired in favor of Geist for EN voice.
 * See docs/plans/2026-05-06-qaren-ux-redesign-design.md Section 1
 * "Typography — Geist (EN) + Cairo (AR)".
 */
import { useFonts as useExpoFonts } from 'expo-font';
import {
  useFonts as useCairoFonts,
  Cairo_400Regular,
  Cairo_600SemiBold,
  Cairo_700Bold,
} from '@expo-google-fonts/cairo';

export const fontFamily = {
  en: {
    regular: 'Geist-Regular',
    semiBold: 'Geist-SemiBold',
    bold: 'Geist-Bold',
  },
  ar: {
    regular: 'Cairo_400Regular',
    semiBold: 'Cairo_600SemiBold',
    bold: 'Cairo_700Bold',
  },
} as const;

const geistFontMap = {
  'Geist-Regular': require('../../assets/fonts/Geist-Regular.ttf'),
  'Geist-SemiBold': require('../../assets/fonts/Geist-SemiBold.ttf'),
  'Geist-Bold': require('../../assets/fonts/Geist-Bold.ttf'),
};

export function useAppFonts(): boolean {
  const [geistLoaded] = useExpoFonts(geistFontMap);
  const [cairoLoaded] = useCairoFonts({
    Cairo_400Regular,
    Cairo_600SemiBold,
    Cairo_700Bold,
  });
  return geistLoaded && cairoLoaded;
}
