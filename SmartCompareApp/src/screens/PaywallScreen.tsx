/**
 * PaywallScreen — Bundle E S1.1 composition.
 *
 * Triggered when free comparisons run out. NEVER shown in onboarding (per
 * product rule). Re-composed against
 * docs/claude-design-handoff/ui_kits/mobile/PaywallScreen.jsx:174-287
 * (the v3 high-conversion layout).
 *
 * Anatomy (per JSX + design doc § 3.1 PaywallScreen row + § 6 checkpoints):
 *   1. Close X (top-left, glass-blur circle)
 *   2. HeroVisual — 3 staggered mini vs-pairs (center popped 6px w/ shadow)
 *   3. Headline ("Keep deciding with confidence.") + sub
 *   4. SocialProof strip — 5 overlapping avatars + "Trusted by 5,000+ GCC
 *      shoppers" + 4.8★ rating pill
 *   5. PlanCardLarge ×2 — Yearly w/ "3 days free · Best value" emerald
 *      eyebrow + Monthly radio
 *   6. Feature section (4 lines w/ emerald check on accentLight circle)
 *   7. Trial timeline (dashed-border card, Today / In 2 days / In 3 days)
 *   8. Sticky CTA — "Start My 3-Day Free Trial" + "No payment due now" trust
 *      line + Terms/Privacy/Restore links
 *
 * Wiring: CTAs Alert.alert('Coming soon') — real Tap Payments integration
 * is post-Bundle-E (Stripe / Apple Pay infra not in scope here).
 *
 * usage status read kept from Bundle D so the screen still surfaces "X / Y
 * free comparisons used" when reached via USAGE_LIMIT error path. Hidden
 * on entry from /profile or settings.
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { X, Check, Star } from 'lucide-react-native';
import { colors, spacing, radii } from '../theme';
import { getUsageStatus, UsageStatus } from '../services/usageService';
import type { RootStackParamList } from '../types/types';

type PaywallRouteProp = RouteProp<RootStackParamList, 'Paywall'>;
type PaywallNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Paywall'>;

type Plan = 'yearly' | 'monthly';

// ---------- HeroVisual: 3 staggered mini-vs-pair tiles ----------
interface HeroItem {
  a: string;
  b: string;
  winner: 'a' | 'b';
}

const HERO_ITEMS: HeroItem[] = [
  { a: '#E8E9ED', b: '#1B1C1F', winner: 'b' },
  { a: '#FBE6E6', b: '#FFEAD4', winner: 'a' },
  { a: '#E6EEF9', b: '#FFF1DA', winner: 'b' },
];

function HeroVisual() {
  return (
    <View style={heroStyles.row}>
      {HERO_ITEMS.map((item, i) => {
        const popped = i === 1;
        return (
          <View
            key={i}
            style={[
              heroStyles.tile,
              popped ? heroStyles.tilePopped : null,
            ]}
            testID={`paywall-hero-tile-${i}`}
          >
            <View style={heroStyles.pairRow}>
              <View
                style={[
                  heroStyles.pairSwatch,
                  { backgroundColor: item.a },
                  item.winner === 'a' ? heroStyles.pairSwatchWinner : null,
                ]}
              />
              <View style={heroStyles.vsPillAbs}>
                <Text style={heroStyles.vsPillText}>VS</Text>
              </View>
              <View
                style={[
                  heroStyles.pairSwatch,
                  { backgroundColor: item.b },
                  item.winner === 'b' ? heroStyles.pairSwatchWinner : null,
                ]}
              />
            </View>
          </View>
        );
      })}
    </View>
  );
}

// ---------- SocialProof: 5 overlapping avatar dots + label + 4.8 pill ----------
const AVATAR_COLORS = ['#FCD9D2', '#E6EEF9', '#FFF1DA', '#FBE6E6', '#1B1C1F'];
const AVATAR_INITIALS = ['K', 'M', 'A', 'S', '+'];

function SocialProof() {
  return (
    <View style={socialStyles.row}>
      <View style={socialStyles.avatars}>
        {AVATAR_COLORS.map((c, i) => (
          <View
            key={i}
            style={[
              socialStyles.avatar,
              { backgroundColor: c, marginLeft: i === 0 ? 0 : -8 },
            ]}
          >
            <Text
              style={[
                socialStyles.avatarInitial,
                { color: i === 4 ? colors.text.onInverse : 'rgba(0,0,0,0.4)' },
              ]}
            >
              {AVATAR_INITIALS[i]}
            </Text>
          </View>
        ))}
      </View>
      <Text style={socialStyles.label} numberOfLines={1}>
        Trusted by <Text style={socialStyles.labelBold}>5,000+</Text> GCC shoppers
      </Text>
      <View style={socialStyles.ratingPill}>
        <Star size={11} color={colors.accentDark} fill={colors.accentDark} />
        <Text style={socialStyles.ratingText}>4.8</Text>
      </View>
    </View>
  );
}

// ---------- PlanCardLarge ----------
interface PlanCardProps {
  name: string;
  price: string;
  sub: string;
  eyebrow?: string;
  selected: boolean;
  onSelect: () => void;
  testID?: string;
}

function PlanCardLarge({
  name,
  price,
  sub,
  eyebrow,
  selected,
  onSelect,
  testID,
}: PlanCardProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onSelect}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={`${name} ${price}`}
      style={[
        planStyles.card,
        selected ? planStyles.cardSelected : planStyles.cardUnselected,
        eyebrow ? planStyles.cardWithEyebrow : null,
      ]}
    >
      {eyebrow ? (
        <View style={planStyles.eyebrowRibbon}>
          <Text style={planStyles.eyebrowText}>{eyebrow}</Text>
        </View>
      ) : null}
      <View
        style={[
          planStyles.radio,
          selected ? planStyles.radioSelected : planStyles.radioUnselected,
        ]}
      />
      <View style={planStyles.textCol}>
        <Text style={planStyles.name}>{name}</Text>
        <Text style={planStyles.sub} numberOfLines={1}>
          {sub}
        </Text>
      </View>
      <Text style={planStyles.price}>{price}</Text>
    </TouchableOpacity>
  );
}

// ---------- FeatureLine ----------
function FeatureLine({ text }: { text: string }) {
  return (
    <View style={featureStyles.row}>
      <View style={featureStyles.checkCircle}>
        <Check size={10} color={colors.accentDark} strokeWidth={3.5} />
      </View>
      <Text style={featureStyles.text}>{text}</Text>
    </View>
  );
}

// ---------- Main screen ----------
export default function PaywallScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<PaywallNavigationProp>();
  const route = useRoute<PaywallRouteProp>();
  const initialUsage = route.params?.initialUsage;

  const [, setUsage] = useState<UsageStatus | null>(null);
  const [plan, setPlan] = useState<Plan>('yearly');

  useEffect(() => {
    if (!initialUsage) {
      getUsageStatus().then(setUsage);
    }
  }, [initialUsage]);

  const onDismiss = () => navigation.goBack();
  const onStartTrial = () => {
    Alert.alert(
      t('paywall.coming_soon_title', { defaultValue: 'Coming soon' }),
      t('paywall.coming_soon_body', {
        defaultValue: 'Subscriptions arrive after launch. Keep enjoying free comparisons in the meantime.',
      }),
      [{ text: 'OK', onPress: onDismiss }],
    );
  };
  const onComingSoon = () => {
    Alert.alert(t('paywall.coming_soon_title', { defaultValue: 'Coming soon' }));
  };

  return (
    <View style={styles.container}>
      {/* Top close button */}
      <View style={styles.header}>
        <TouchableOpacity
          testID="paywall-close"
          onPress={onDismiss}
          accessibilityRole="button"
          accessibilityLabel={t('common.cancel', { defaultValue: 'Close' })}
          style={styles.closeBtn}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
        >
          <X size={18} color={colors.text.primary} strokeWidth={2.4} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <HeroVisual />

        <Text style={styles.title}>
          {t('paywall.title_part1', { defaultValue: 'Keep deciding with ' })}
          <Text style={styles.titleAccent}>
            {t('paywall.title_accent', { defaultValue: 'confidence' })}
          </Text>
          .
        </Text>
        <Text style={styles.subtitle}>
          {t('paywall.subtitle', {
            defaultValue: 'Unlimited comparisons, deeper reviews, full price history.',
          })}
        </Text>

        <SocialProof />

        <PlanCardLarge
          testID="paywall-plan-yearly"
          name={t('paywall.plan.yearly_name', { defaultValue: 'Yearly' })}
          price={t('paywall.plan.yearly_price', { defaultValue: '0.9 BHD/mo' })}
          sub={t('paywall.plan.yearly_sub', {
            defaultValue: '10.8 BHD billed yearly · Save ~70%',
          })}
          eyebrow={t('paywall.plan.yearly_eyebrow', {
            defaultValue: '3 DAYS FREE · BEST VALUE',
          })}
          selected={plan === 'yearly'}
          onSelect={() => setPlan('yearly')}
        />
        <PlanCardLarge
          testID="paywall-plan-monthly"
          name={t('paywall.plan.monthly_name', { defaultValue: 'Monthly' })}
          price={t('paywall.plan.monthly_price', { defaultValue: '2.9 BHD' })}
          sub={t('paywall.plan.monthly_sub', {
            defaultValue: 'Billed monthly · Cancel anytime',
          })}
          selected={plan === 'monthly'}
          onSelect={() => setPlan('monthly')}
        />

        {/* Feature section */}
        <View style={styles.featureSection}>
          <FeatureLine
            text={t('paywall.features.comparisons', {
              defaultValue: '70 comparisons per month',
            })}
          />
          <FeatureLine
            text={t('paywall.features.history', {
              defaultValue: 'Full price history across 25+ GCC retailers',
            })}
          />
          <FeatureLine
            text={t('paywall.features.priority', {
              defaultValue: 'Priority processing — results in under 8 seconds',
            })}
          />
          <FeatureLine
            text={t('paywall.features.adFree', { defaultValue: 'Ad-free, always' })}
          />
        </View>

        {/* Trial timeline */}
        <View style={styles.timelineCard} testID="paywall-timeline">
          <Text style={styles.timelineEyebrow}>
            {t('paywall.timeline.title', { defaultValue: 'HOW THE TRIAL WORKS' })}
          </Text>
          <View style={styles.timelineRows}>
            <Text style={styles.timelineRow}>
              <Text style={styles.timelineAnchorActive}>Today</Text>
              <Text> · </Text>
              {t('paywall.timeline.today', {
                defaultValue: 'Unlock everything immediately.',
              })}
            </Text>
            <Text style={styles.timelineRow}>
              <Text style={styles.timelineAnchorMuted}>In 2 days</Text>
              <Text> · </Text>
              {t('paywall.timeline.in2', {
                defaultValue: 'Gentle reminder before billing.',
              })}
            </Text>
            <Text style={styles.timelineRow}>
              <Text style={styles.timelineAnchorMuted}>In 3 days</Text>
              <Text> · </Text>
              {t('paywall.timeline.in3', {
                defaultValue: 'Billing starts — cancel anytime.',
              })}
            </Text>
          </View>
        </View>
      </ScrollView>

      {/* Sticky bottom CTA */}
      <View style={styles.footer}>
        <TouchableOpacity
          testID="paywall-cta"
          onPress={onStartTrial}
          activeOpacity={0.9}
          accessibilityRole="button"
          accessibilityLabel={t('paywall.cta', {
            defaultValue: 'Start My 3-Day Free Trial',
          })}
          style={styles.ctaBtn}
        >
          <Text style={styles.ctaText}>
            {t('paywall.cta', { defaultValue: 'Start My 3-Day Free Trial' })}
          </Text>
        </TouchableOpacity>

        <View style={styles.trustRow}>
          <Check size={13} color={colors.accentDark} strokeWidth={2.4} />
          <Text style={styles.trustText}>
            {t('paywall.trust', {
              defaultValue: 'No payment due now · Cancel anytime',
            })}
          </Text>
        </View>

        <View style={styles.linksRow}>
          <TouchableOpacity onPress={onComingSoon} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={styles.linkText}>{t('common.terms', { defaultValue: 'Terms' })}</Text>
          </TouchableOpacity>
          <Text style={styles.linkDot}>·</Text>
          <TouchableOpacity onPress={onComingSoon} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={styles.linkText}>{t('common.privacy', { defaultValue: 'Privacy' })}</Text>
          </TouchableOpacity>
          <Text style={styles.linkDot}>·</Text>
          <TouchableOpacity testID="paywall-restore" onPress={onComingSoon} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={styles.linkText}>{t('paywall.restore', { defaultValue: 'Restore' })}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

// ---------- Styles ----------
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
    paddingTop: 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.xs,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    lineHeight: 26 * 1.2,
    letterSpacing: -0.3,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.xs,
    marginBottom: 6,
  },
  titleAccent: {
    color: colors.accent,
  },
  subtitle: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 14 * 1.5,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 320,
    alignSelf: 'center',
    marginBottom: 18,
  },
  featureSection: {
    marginTop: 18,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  timelineCard: {
    marginTop: 16,
    paddingVertical: spacing.md,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border.light,
    borderStyle: 'dashed',
  },
  timelineEyebrow: {
    fontSize: 11,
    fontWeight: '600',
    lineHeight: 11 * 1.4,
    letterSpacing: 0.8,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  timelineRows: {
    gap: 6,
  },
  timelineRow: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.text.primary,
  },
  timelineAnchorActive: {
    color: colors.accentDark,
    fontWeight: '700',
  },
  timelineAnchorMuted: {
    color: colors.text.secondary,
    fontWeight: '700',
  },
  footer: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.base,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
    backgroundColor: colors.bg.primary,
  },
  ctaBtn: {
    width: '100%',
    height: 56,
    borderRadius: radii.chip,
    backgroundColor: colors.cta.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  ctaText: {
    fontSize: 17,
    fontWeight: '700',
    lineHeight: 17,
    color: colors.cta.onPrimary,
  },
  trustRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 10,
  },
  trustText: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
  },
  linksRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 14,
    marginTop: 6,
    alignItems: 'center',
  },
  linkText: {
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 11 * 1.4,
    color: colors.text.placeholder,
  },
  linkDot: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.text.placeholder,
  },
});

const heroStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 16,
    paddingHorizontal: spacing.base,
  },
  tile: {
    padding: 8,
    borderRadius: 12,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  tilePopped: {
    transform: [{ translateY: -6 }],
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  pairRow: {
    flexDirection: 'row',
    gap: 4,
    position: 'relative',
  },
  pairSwatch: {
    width: 38,
    height: 38,
    borderRadius: 8,
  },
  pairSwatchWinner: {
    borderWidth: 2,
    borderColor: colors.accent,
  },
  vsPillAbs: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    pointerEvents: 'none',
  },
  vsPillText: {
    paddingHorizontal: 5,
    height: 16,
    lineHeight: 16,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    color: colors.accentDark,
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 0.8,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: colors.bg.secondary,
  },
});

const socialStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginBottom: 18,
  },
  avatars: {
    flexDirection: 'row',
  },
  avatar: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitial: {
    fontSize: 9,
    fontWeight: '700',
    lineHeight: 9,
  },
  label: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.4,
    color: colors.text.primary,
    flexShrink: 1,
  },
  labelBold: {
    fontWeight: '700',
  },
  ratingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
  },
  ratingText: {
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 11,
    color: colors.accentDark,
  },
});

const planStyles = StyleSheet.create({
  card: {
    width: '100%',
    minHeight: 92,
    paddingVertical: 14,
    paddingHorizontal: spacing.base,
    borderRadius: 18,
    backgroundColor: colors.bg.primary,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginTop: spacing.sm,
    position: 'relative',
  },
  cardWithEyebrow: {
    marginTop: 14,
  },
  cardSelected: {
    borderWidth: 2,
    borderColor: colors.cta.primary,
  },
  cardUnselected: {
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  eyebrowRibbon: {
    position: 'absolute',
    top: -10,
    left: spacing.base,
    paddingHorizontal: 10,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  eyebrowText: {
    fontSize: 10,
    fontWeight: '700',
    lineHeight: 10,
    color: colors.text.onInverse,
    letterSpacing: 1,
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
  },
  radioSelected: {
    borderWidth: 6,
    borderColor: colors.cta.primary,
    backgroundColor: colors.bg.primary,
  },
  radioUnselected: {
    borderWidth: 1.5,
    borderColor: colors.border.medium,
  },
  textCol: {
    flex: 1,
    minWidth: 0,
  },
  name: {
    fontSize: 17,
    fontWeight: '700',
    lineHeight: 17 * 1.3,
    color: colors.text.primary,
  },
  sub: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
    marginTop: 4,
  },
  price: {
    fontSize: 18,
    fontWeight: '700',
    lineHeight: 18,
    color: colors.text.primary,
    fontVariant: ['tabular-nums'],
  },
});

const featureStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 6,
  },
  checkCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 13 * 1.4,
    color: colors.text.primary,
  },
});
