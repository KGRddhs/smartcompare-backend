/**
 * Qaren typography fonts.
 *
 * EN voice: Geist (local TTF, SIL OFL v1.1, ~125KB per weight)
 * AR voice: Cairo (Google Fonts via @expo-google-fonts/cairo)
 *
 * Phase 1 visual swap — Inter retired in favor of Geist for EN voice.
 * See docs/plans/2026-05-06-qaren-ux-redesign-design.md Section 1
 * "Typography — Geist (EN) + Cairo (AR)".
 *
 * B4 — IMPORT THE CAIRO WEIGHTS FROM THEIR PER-WEIGHT SUBPATHS, NEVER THE
 * BARREL. `@expo-google-fonts/cairo`'s index.js top-level `require()`s all
 * EIGHT TTFs, and Metro does no tree-shaking (there is no metro.config.js
 * here, and the experimental tree-shaker is absent from this @expo/metro-config),
 * so a single barrel import drags 469,608 bytes of never-loaded weights
 * (200/300/500/800/900) into the shipped asset graph. Each subpath directory
 * has its own index.js requiring exactly one TTF. The package declares no
 * "exports" field, so the subpaths resolve as plain directories.
 *
 * Same reason `useFonts` comes from expo-font, not from the cairo package:
 * `@expo-google-fonts/cairo`'s useFonts re-enters the barrel and would put
 * all eight weights back. The cairo wrapper is a thin shim over
 * expo-font's loadAsync, so this is functionally identical.
 */
import { useFonts as useExpoFonts } from 'expo-font';
import { Cairo_400Regular } from '@expo-google-fonts/cairo/400Regular';
import { Cairo_600SemiBold } from '@expo-google-fonts/cairo/600SemiBold';
import { Cairo_700Bold } from '@expo-google-fonts/cairo/700Bold';

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

const appFontMap = {
  'Geist-Regular': require('../../assets/fonts/Geist-Regular.ttf'),
  'Geist-SemiBold': require('../../assets/fonts/Geist-SemiBold.ttf'),
  'Geist-Bold': require('../../assets/fonts/Geist-Bold.ttf'),
  Cairo_400Regular,
  Cairo_600SemiBold,
  Cairo_700Bold,
};

export function useAppFonts(): boolean {
  const [fontsLoaded] = useExpoFonts(appFontMap);
  return fontsLoaded;
}
