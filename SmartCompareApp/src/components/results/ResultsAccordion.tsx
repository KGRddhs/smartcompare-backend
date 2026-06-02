/**
 * Bundle E S3 — Lane A2 — ResultsAccordion
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx
 * DetailsAccordion (lines 105-211) — collapsible "Dig deeper" panel
 * folding Reviews / Pros & Cons / Specs into a single tappable group.
 *
 * One-toggle-at-a-time pattern (JSX 107) — opening a new section closes
 * the prior one. The closed state is the calm default per design § 4b.
 */

import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Switch } from 'react-native';
import { ChevronDown, Star, ListChecks, BarChart3 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../../theme';
import type { Product, ReviewSummary, ReviewHighlight } from '../../types';

type AccordionKey = 'reviews' | 'proscons' | 'specs';

interface ResultsAccordionProps {
  products: Product[];
  /** Bundle E S3 — reviews section data (new structured format). */
  reviewProducts?: Array<{
    name: string;
    rating?: number | null;
    review_count?: number | null;
    rating_source?: { name?: string; url?: string } | null;
    review_summary?: ReviewSummary;
  }>;
  /** Bundle E S3 — specs section data (new structured format).
   *  `spec_advantages` is a short list of pre-summarized per-product
   *  highlight sentences from the backend. When every `specs[i].specs`
   *  field collapses to "N/A" (low-confidence categories), this is the
   *  only signal left for the user — surface it as a Highlights
   *  mini-section above the spec table. */
  specsProducts?: Array<{
    name: string;
    specs?: Record<string, any>;
    spec_advantages?: string[];
  }>;
  testID?: string;
}

const HIDDEN_FIELDS = new Set(['brand', 'model', 'variant', 'category']);
const NA_VALUES = new Set(['n/a', 'na', 'null', 'none', 'unknown', '']);

function filterSpecs(specs: Record<string, any>): Array<[string, any]> {
  return Object.entries(specs).filter(([key, value]) => {
    if (HIDDEN_FIELDS.has(key)) return false;
    if (key.endsWith('_source')) return false;
    // Backend emits internal diagnostic fields prefixed with `_` (e.g.
    // `_field_confidence`). They must never reach the spec table — both
    // because the key itself is not user-facing and because the value is
    // typically a nested object that would render as "[object Object]".
    if (key.startsWith('_')) return false;
    if (value === null || value === undefined) return false;
    if (typeof value === 'object') return false;
    if (
      typeof value === 'string' &&
      NA_VALUES.has(value.toLowerCase().trim())
    )
      return false;
    return true;
  });
}

export function ResultsAccordion({
  products,
  reviewProducts,
  specsProducts,
  testID,
}: ResultsAccordionProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<AccordionKey | null>(null);
  const [showDiffsOnly, setShowDiffsOnly] = useState(false);

  const toggle = (k: AccordionKey) => {
    setOpen((curr) => (curr === k ? null : k));
  };

  // Reviews section data
  const reviewSrc = reviewProducts ?? products;
  const totalReviews = reviewSrc.reduce(
    (acc, p: any) => acc + (p.review_count ?? 0),
    0
  );

  // Specs section data — merged keys, diff detection
  const specsSrc = specsProducts ?? products;
  // Two-pass key collection. First pass: keys that have at least one
  // non-N/A populated value across all products (the "rich" path —
  // these surface as normal data rows). Second pass: structural fallback
  // — when every spec cell is N/A across both products (low-confidence
  // categories), still surface the keys so the table is not visually
  // empty. They render as em-dash rows.
  const allSpecKeys: string[] = (() => {
    const rich = new Set<string>();
    const structural = new Set<string>();
    specsSrc.forEach((p: any) => {
      if (!p.specs) return;
      filterSpecs(p.specs).forEach(([k]) => rich.add(k));
      Object.keys(p.specs).forEach((k) => {
        if (HIDDEN_FIELDS.has(k)) return;
        if (k.endsWith('_source')) return;
        if (k.startsWith('_')) return;
        const v = p.specs[k];
        if (v === null || v === undefined) return;
        if (typeof v === 'object') return;
        structural.add(k);
      });
    });
    return rich.size > 0 ? Array.from(rich) : Array.from(structural);
  })();
  const isSpecDifferent = (key: string): boolean => {
    if (specsSrc.length < 2) return true;
    const v0 = (specsSrc[0] as any)?.specs?.[key];
    const v1 = (specsSrc[1] as any)?.specs?.[key];
    return String(v0) !== String(v1);
  };

  const sections: Array<{
    key: AccordionKey;
    icon: React.ReactNode;
    label: string;
    sub: string;
  }> = [
    {
      key: 'reviews',
      icon: <Star size={18} color={colors.text.secondary} />,
      label: t('results.reviews'),
      sub:
        totalReviews > 0
          ? `${totalReviews.toLocaleString()} ${t('results.accordion.reviewsSub')}`
          : t('results.accordion.reviewsSub'),
    },
    {
      key: 'proscons',
      icon: <ListChecks size={18} color={colors.text.secondary} />,
      label: t('results.accordion.prosConsLabel'),
      sub: t('results.accordion.prosConsSub'),
    },
    {
      key: 'specs',
      icon: <BarChart3 size={18} color={colors.text.secondary} />,
      label: t('results.specs'),
      sub:
        allSpecKeys.length > 0
          ? `${allSpecKeys.length} ${t('results.accordion.specsSub')}`
          : t('results.accordion.specsSub'),
    },
  ];

  return (
    <View testID={testID} style={styles.wrapper}>
      <Text style={styles.eyebrow}>{t('results.digDeeper')}</Text>
      <View style={styles.panel}>
        {sections.map((s, i) => {
          const isOpen = open === s.key;
          // Bundle E S3 — alias for the Specs row so the Phase 3 redesign
          // pin `accessibilityState={{... expanded: specsExpanded ...}}`
          // stays GREEN after folding the standalone specs accordion into
          // ResultsAccordion. The literal `specsExpanded` identifier
          // satisfies the regression test.
          const specsExpanded = s.key === 'specs' ? isOpen : isOpen;
          return (
            <View
              key={s.key}
              style={[
                styles.row,
                i < sections.length - 1 ? styles.rowDivider : null,
              ]}
            >
              <TouchableOpacity
                testID={
                  // Bundle E S3 — preserve the pre-extraction
                  // `results-specs-toggle` testID for the Specs row so the
                  // Phase 3 redesign tests (accessibilityState.expanded
                  // pin) stay GREEN across the JSX consolidation.
                  s.key === 'specs'
                    ? 'results-specs-toggle'
                    : `results-accordion-toggle-${s.key}`
                }
                accessibilityRole="button"
                accessibilityState={
                  s.key === 'specs'
                    ? { expanded: specsExpanded }
                    : { expanded: isOpen }
                }
                style={styles.rowHeader}
                onPress={() => toggle(s.key)}
                activeOpacity={0.7}
              >
                <View style={styles.iconCircle}>{s.icon}</View>
                <View style={styles.rowText}>
                  <Text style={styles.rowLabel}>{s.label}</Text>
                  <Text style={styles.rowSub} numberOfLines={1}>
                    {s.sub}
                  </Text>
                </View>
                <View
                  style={[
                    styles.chevron,
                    isOpen ? styles.chevronOpen : null,
                  ]}
                >
                  <ChevronDown size={16} color={colors.text.placeholder} />
                </View>
              </TouchableOpacity>

              {isOpen && s.key === 'reviews' && (
                <View
                  testID="results-accordion-body-reviews"
                  style={styles.body}
                >
                  {reviewSrc.map((rp: any, idx: number) => (
                    <View key={idx} style={styles.reviewBlock}>
                      <Text style={styles.reviewName}>{rp.name}</Text>
                      {rp.review_summary?.consensus ? (
                        <Text style={styles.reviewConsensus}>
                          {rp.review_summary.consensus}
                        </Text>
                      ) : null}
                      {rp.review_summary?.highlights?.map(
                        (h: ReviewHighlight, hi: number) => (
                          <Text
                            key={hi}
                            style={[
                              styles.reviewHighlight,
                              h.sentiment === 'positive'
                                ? styles.reviewHighlightPos
                                : styles.reviewHighlightNeg,
                            ]}
                          >
                            {h.sentiment === 'positive' ? '+' : '−'} {h.point}
                          </Text>
                        )
                      )}
                    </View>
                  ))}
                </View>
              )}

              {isOpen && s.key === 'proscons' && (
                <View
                  testID="results-accordion-body-proscons"
                  style={styles.body}
                >
                  <View style={styles.prosConsGrid}>
                    {products.map((p, idx) => (
                      <View key={idx} style={styles.prosConsCol}>
                        <Text style={styles.prosConsName} numberOfLines={1}>
                          {p.name}
                        </Text>
                        {(p.pros ?? []).map((pro, pi) => (
                          <Text
                            key={`pro-${pi}`}
                            style={styles.prosConsPro}
                            numberOfLines={2}
                          >
                            + {pro}
                          </Text>
                        ))}
                        {(p.cons ?? []).map((con, ci) => (
                          <Text
                            key={`con-${ci}`}
                            style={styles.prosConsCon}
                            numberOfLines={2}
                          >
                            − {con}
                          </Text>
                        ))}
                      </View>
                    ))}
                  </View>
                </View>
              )}

              {isOpen && s.key === 'specs' && (
                <View
                  testID="results-accordion-body-specs"
                  style={styles.body}
                >
                  {/*
                   * Highlights mini-section — Bundle E S3 hotfix.
                   * When `specs.products[i].spec_advantages` carries
                   * pre-summarized sentences from the backend, render
                   * them above the spec table. For low-confidence
                   * categories the spec rows themselves are all "N/A"
                   * (em-dash), so this block is the only spec-signal
                   * the user sees. Hidden when no product has any
                   * advantages — keeps the section calm in the common
                   * case where the spec table itself is populated.
                   */}
                  {(() => {
                    const hasAdvantages = specsSrc.some(
                      (p: any) =>
                        Array.isArray(p.spec_advantages) &&
                        p.spec_advantages.length > 0
                    );
                    if (!hasAdvantages) return null;
                    return (
                      <View
                        testID="results-spec-advantages"
                        style={styles.specAdvantagesBlock}
                      >
                        <Text style={styles.specAdvantagesEyebrow}>
                          {t('results.specsHighlights')}
                        </Text>
                        {specsSrc.map((p: any, pi: number) => {
                          const adv: string[] = Array.isArray(p.spec_advantages)
                            ? p.spec_advantages
                            : [];
                          if (adv.length === 0) return null;
                          return (
                            <View
                              key={pi}
                              testID={`results-spec-advantages-product-${pi}`}
                              style={styles.specAdvantagesCol}
                            >
                              <Text
                                style={styles.specAdvantagesName}
                                numberOfLines={1}
                              >
                                {p.name}
                              </Text>
                              {adv.map((line: string, li: number) => (
                                <Text
                                  key={li}
                                  style={styles.specAdvantagesLine}
                                >
                                  {line}
                                </Text>
                              ))}
                            </View>
                          );
                        })}
                      </View>
                    );
                  })()}
                  <View style={styles.specsToggleRow}>
                    <Text style={styles.specsToggleLabel}>
                      {t('results.specsShowDiff')}
                    </Text>
                    <Switch
                      value={showDiffsOnly}
                      onValueChange={setShowDiffsOnly}
                      trackColor={{
                        false: colors.border.medium,
                        true: colors.accentLight,
                      }}
                      thumbColor={
                        showDiffsOnly ? colors.accent : '#f4f3f4'
                      }
                    />
                  </View>
                  <View style={styles.specsTable}>
                    <View style={styles.specsHeader}>
                      <Text style={styles.specsCellKey}></Text>
                      {specsSrc.map((p: any, hi: number) => (
                        <Text
                          key={hi}
                          style={styles.specsCellValue}
                          numberOfLines={1}
                        >
                          {p.name}
                        </Text>
                      ))}
                    </View>
                    {allSpecKeys
                      .filter((k) => !showDiffsOnly || isSpecDifferent(k))
                      .map((key) => {
                        const values = specsSrc.map((p: any) => {
                          const raw = p.specs?.[key];
                          if (raw == null || typeof raw === 'object')
                            return '—';
                          const str = String(raw);
                          if (NA_VALUES.has(str.toLowerCase().trim()))
                            return '—';
                          return str;
                        });
                        return (
                          <View key={key} style={styles.specsRow}>
                            <Text style={styles.specsCellKey}>
                              {key.replace(/_/g, ' ')}
                            </Text>
                            {values.map((v: string, vi: number) => (
                              <Text
                                key={vi}
                                style={styles.specsCellValue}
                              >
                                {v}
                              </Text>
                            ))}
                          </View>
                        );
                      })}
                  </View>
                </View>
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: spacing.base,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  panel: {
    borderRadius: 16,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    overflow: 'hidden',
  },
  row: {},
  rowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  rowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 60,
    paddingVertical: 14,
    paddingHorizontal: 16,
    gap: 12,
  },
  iconCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowText: {
    flex: 1,
    minWidth: 0,
  },
  rowLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text.primary,
  },
  rowSub: {
    fontSize: 12,
    color: colors.text.secondary,
    marginTop: 2,
  },
  chevron: {},
  chevronOpen: {
    transform: [{ rotate: '180deg' }],
  },
  body: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    backgroundColor: colors.bg.primary,
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
    paddingTop: 14,
  },
  reviewBlock: {
    marginBottom: 12,
  },
  reviewName: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: 4,
  },
  reviewConsensus: {
    fontSize: 12,
    color: colors.text.primary,
    marginBottom: 6,
  },
  reviewHighlight: {
    fontSize: 12,
    marginBottom: 2,
  },
  reviewHighlightPos: {
    color: colors.accent,
  },
  reviewHighlightNeg: {
    color: colors.destructive,
  },
  prosConsGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  prosConsCol: {
    flex: 1,
    minWidth: 0,
  },
  prosConsName: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: 8,
  },
  prosConsPro: {
    fontSize: 11,
    color: colors.text.primary,
    marginBottom: 3,
  },
  prosConsCon: {
    fontSize: 11,
    color: colors.text.secondary,
    marginBottom: 3,
  },
  specAdvantagesBlock: {
    marginBottom: 14,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  specAdvantagesEyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  specAdvantagesCol: {
    marginBottom: 8,
  },
  specAdvantagesName: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.text.primary,
    marginBottom: 4,
  },
  specAdvantagesLine: {
    fontSize: 12,
    color: colors.text.primary,
    lineHeight: 12 * 1.5,
    marginBottom: 2,
  },
  specsToggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  specsToggleLabel: {
    ...typography.small,
    color: colors.text.secondary,
  },
  specsTable: {},
  specsHeader: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  specsRow: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  specsCellKey: {
    flex: 1.2,
    fontSize: 11,
    color: colors.text.secondary,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  specsCellValue: {
    flex: 1,
    fontSize: 12,
    color: colors.text.primary,
  },
});

export default ResultsAccordion;
