// SmartCompareApp/src/screens/LegalScreen.tsx
//
// Renders /api/v1/legal/privacy_policy or /terms_of_service as markdown.
// U8 (rulings UL5, UL13): the document is requested in the UI language
// (`lang` query parameter, 'ar' or 'en'; the backend serves app/legal/*_ar.md
// for 'ar'), the offline copy is cached per document AND language under
// `legal_cache_{doc}_{lang}` (the pre-U8 key held the DRAFT and is never read),
// and the error state links to the landing page of the same document and
// language. No copy of the policy is bundled in the binary. A language change
// clears the other language's document before the refetch (adversary B10).

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Linking,
} from 'react-native';
import Markdown from 'react-native-markdown-display';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { DirectionalIcon } from '../components/primitives/DirectionalIcon';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import api, { LANDING_BASE_URL } from '../services/api';
import type { RootStackParamList } from '../types';

export type LegalDoc = 'privacy' | 'terms';

type LegalLang = 'ar' | 'en';

type Props = NativeStackScreenProps<RootStackParamList, 'Legal'>;

const ENDPOINTS: Record<LegalDoc, string> = {
  privacy: '/api/v1/legal/privacy_policy',
  terms: '/api/v1/legal/terms_of_service',
};

/** Landing page file of each document (the Arabic pages live under ar/). */
const LANDING_PAGES: Record<LegalDoc, string> = {
  privacy: 'privacy.html',
  terms: 'terms.html',
};

/** 'ar' when the i18next UI language starts with 'ar', else 'en' (undefined -> 'en'). */
function legalLang(uiLanguage: string | undefined): LegalLang {
  return typeof uiLanguage === 'string' && uiLanguage.startsWith('ar') ? 'ar' : 'en';
}

export default function LegalScreen({ route, navigation }: Props) {
  const { t, i18n } = useTranslation();
  const { doc } = route.params;
  const [content, setContent] = useState<string | null>(null);
  const [bannerKey, setBannerKey] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // The language of the document on screen: a language change never keeps the other one (B10).
  const shownLang = useRef<LegalLang | null>(null);

  const lang = legalLang(i18n?.language);
  const endpoint = ENDPOINTS[doc];
  const cacheKey = `legal_cache_${doc}_${lang}`;
  const webUrl = `${LANDING_BASE_URL}/${lang === 'ar' ? 'ar/' : ''}${LANDING_PAGES[doc]}`;

  const load = useCallback(async () => {
    setLoading(true);
    setErrorKey(null);
    setBannerKey(null);
    if (shownLang.current !== lang) {
      shownLang.current = null;
      setContent(null);
    }
    try {
      const res = await api.get(endpoint, { params: { lang } });
      const md = res.data?.content ?? '';
      shownLang.current = lang;
      setContent(md);
      try { await AsyncStorage.setItem(cacheKey, md); } catch {}
    } catch {
      const cached = await AsyncStorage.getItem(cacheKey).catch(() => null);
      if (cached) {
        shownLang.current = lang;
        setContent(cached);
        setBannerKey('legal.offline.banner');
      } else {
        setErrorKey('legal.error.title');
      }
    } finally {
      setLoading(false);
    }
  }, [endpoint, lang, cacheKey]);

  useEffect(() => { load(); }, [load]);

  const openWebVersion = useCallback(() => {
    Linking.openURL(webUrl).catch(() => {});
  }, [webUrl]);

  const title = doc === 'privacy' ? t('profile.privacy') : t('profile.terms');

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          style={styles.headerBtn}
        >
          <DirectionalIcon>
            <ChevronLeft size={24} color={colors.text.primary} />
          </DirectionalIcon>
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        <View style={styles.headerBtn} />
      </View>

      {loading && !content ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.accent} />
          <Text style={styles.loadingText}>{t('legal.loading')}</Text>
        </View>
      ) : null}

      {errorKey && !content ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{t(errorKey)}</Text>
          <TouchableOpacity onPress={load} style={styles.retryBtn} accessibilityRole="button">
            <Text style={styles.retryText}>{t('legal.error.retry')}</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={openWebVersion} style={styles.webLink} accessibilityRole="link">
            <Text style={styles.webLinkText}>{t('legal.error.openWeb')}</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {content ? (
        <ScrollView contentContainerStyle={styles.scroll}>
          {bannerKey ? <Text style={styles.offlineBanner}>{t(bannerKey)}</Text> : null}
          <Markdown style={markdownStyles}>{content}</Markdown>
        </ScrollView>
      ) : null}
    </SafeAreaView>
  );
}

const markdownStyles = {
  heading1: {
    ...typography.title,
    color: colors.text.primary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  heading2: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
    marginTop: spacing.md,
    marginBottom: spacing.xs,
  },
  body: {
    ...typography.body,
    color: colors.text.primary,
  },
  paragraph: {
    ...typography.body,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  link: {
    color: colors.accent,
  },
  list_item: {
    marginVertical: spacing.xs,
  },
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  headerBtn: { width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  title: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
    flex: 1,
    textAlign: 'center',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  loadingText: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },
  scroll: {
    padding: spacing.md,
  },
  errorText: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  retryBtn: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.cta.primary,
    borderRadius: radii.button,
  },
  retryText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
  // Centred under the retry button: no physical left/right, so RTL needs no flip.
  webLink: {
    marginTop: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  webLinkText: {
    ...typography.body,
    color: colors.accent,
    textAlign: 'center',
    textDecorationLine: 'underline',
  },
  offlineBanner: {
    backgroundColor: colors.bg.secondary,
    color: colors.text.secondary,
    padding: spacing.sm,
    marginBottom: spacing.md,
    borderRadius: radii.button,
    ...typography.caption,
    textAlign: 'center',
  },
});
