import {
  useFonts as useInterFonts,
  Inter_400Regular,
  Inter_600SemiBold,
  Inter_700Bold,
} from '@expo-google-fonts/inter';
import {
  useFonts as useCairoFonts,
  Cairo_400Regular,
  Cairo_600SemiBold,
  Cairo_700Bold,
} from '@expo-google-fonts/cairo';

export const fontFamily = {
  en: {
    regular: 'Inter_400Regular',
    semiBold: 'Inter_600SemiBold',
    bold: 'Inter_700Bold',
  },
  ar: {
    regular: 'Cairo_400Regular',
    semiBold: 'Cairo_600SemiBold',
    bold: 'Cairo_700Bold',
  },
} as const;

export function useAppFonts(): boolean {
  const [interLoaded] = useInterFonts({
    Inter_400Regular,
    Inter_600SemiBold,
    Inter_700Bold,
  });
  const [cairoLoaded] = useCairoFonts({
    Cairo_400Regular,
    Cairo_600SemiBold,
    Cairo_700Bold,
  });
  return interLoaded && cairoLoaded;
}
