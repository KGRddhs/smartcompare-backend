// SmartCompareApp/src/screens/LegalScreen.tsx
//
// Renders /api/v1/legal/privacy_policy or /terms_of_service as markdown.
// CONTENT note: backend markdown at app/legal/*.md was rebranded to Qaren
// by Bundle D R22 (commits 83a83f0 + eeaea11). Renders branded content
// directly — no stale "SmartCompare" / "@smartcompare.app" strings remain.

import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import Markdown from 'react-native-markdown-display';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, radii, typography } from '../theme';
import api from '../services/api';
import type { RootStackParamList } from '../types';

export type LegalDoc = 'privacy' | 'terms';

type Props = NativeStackScreenProps<RootStackParamList, 'Legal'>;

const ENDPOINTS: Record<LegalDoc, string> = {
  privacy: '/api/v1/legal/privacy_policy',
  terms: '/api/v1/legal/terms_of_service',
};

export default function LegalScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { doc } = route.params;
  const [content, setContent] = useState<string | null>(null);
  const [bannerKey, setBannerKey] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const endpoint = ENDPOINTS[doc];
  const cacheKey = `legal_cache_${doc}`;

  const load = useCallback(async () => {
    setLoading(true);
    setErrorKey(null);
    setBannerKey(null);
    try {
      const res = await api.get(endpoint);
      const md = res.data?.content ?? '';
      setContent(md);
      try { await AsyncStorage.setItem(cacheKey, md); } catch {}
    } catch {
      const cached = await AsyncStorage.getItem(cacheKey).catch(() => null);
      if (cached) {
        setContent(cached);
        setBannerKey('legal.offline.banner');
      } else {
        setErrorKey('legal.error.title');
      }
    } finally {
      setLoading(false);
    }
  }, [endpoint, cacheKey]);

  useEffect(() => { load(); }, [load]);

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
          <ChevronLeft size={24} color={colors.text.primary} />
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
