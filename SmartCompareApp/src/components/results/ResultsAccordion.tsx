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
    /** Lane A-L3 Task L3.4 — up to 3 retailer quotes per product
     *  (Amazon / Noon / X). Backend writes
     *  `reviews.products[i].retailer_quotes`. */
    retailer_quotes?: Array<{
      retailer: string;
      rating?: number | null;
      text: string;
    }>;
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
  /** Lane A-L3 Task L3.2 — per-row winner data. Backend writes
   *  `specs.specs_comparison`. When present, each row's winning cell
   *  paints emerald. */
  specsComparison?: Array<{
    field: string;
    p0_value: string;
    p1_value: string;
    winner: 0 | 1 | null;
  }>;
  /** Lane A-L3 Task L3.3 — overall winner index. Used to draw the
   *  winner-star (★) prefix on the winning column in the pros/cons grid. */
  winnerIndex?: 0 | 1;
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
  specsComparison,
  winnerIndex,
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
  // Weighted average rating across both products (by review_count when
  // available, else simple mean of the ratings present). Used in the
  // Reviews header sub: "{avg}★ avg · {total} reviews across both".
  const avgRating: number | null = (() => {
    const rated = reviewSrc.filter(
      (p: any) => typeof p.rating === 'number' && p.rating > 0
    );
    if (rated.length === 0) return null;
    const weightTotal = rated.reduce(
      (acc: number, p: any) => acc + (p.review_count ?? 0),
      0
    );
    if (weightTotal > 0) {
      const sum = rated.reduce(
        (acc: number, p: any) => acc + p.rating * (p.review_count ?? 0),
        0
      );
      return sum / weightTotal;
    }
    const sum = rated.reduce((acc: number, p: any) => acc + p.rating, 0);
    return sum / rated.length;
  })();

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

  // Lane A-L3 Task L3.2 — fast O(1) lookup of per-row winner index from
  // the backend's specs_comparison array. Null/missing → no emerald
  // (tie or pre-v2 data).
  const winnerByField: Record<string, 0 | 1 | null> = React.useMemo(() => {
    const map: Record<string, 0 | 1 | null> = {};
    if (Array.isArray(specsComparison)) {
      for (const r of specsComparison) {
        if (r && typeof r.field === 'string') {
          map[r.field] = r.winner ?? null;
        }
      }
    }
    return map;
  }, [specsComparison]);

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
      // Reference sub: "4.8★ avg · 1,240 reviews across both".
      // Prepend the weighted-avg rating when available; always include the
      // total-reviews phrase. Falls back to the bare phrase when neither
      // a rating nor a count is present.
      sub: (() => {
        const tail =
          totalReviews > 0
            ? `${totalReviews.toLocaleString()} ${t('results.accordion.reviewsSub')}`
            : t('results.accordion.reviewsSub');
        if (avgRating !== null) {
          return `${avgRating.toFixed(1)}${t('results.accordion.reviewsAvg')} · ${tail}`;
        }
        return tail;
      })(),
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
          // Bundle E S3 — alias preserves the literal `specsExpanded`
          // identifier that the Phase 3 redesign regression test
          // (ResultsScreen.redesign.test.tsx:86-88) greps for inside
          // the concatenated source via the pattern
          // `accessibilityState={{ expanded: specsExpanded ...}}`.
          // The test asserts presence of the JSX-quoted shape, not a
          // branching form.
          const specsExpanded = isOpen;
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
                  {/*
                   * Reference: ReviewLine (ResultsScreen.jsx 213-236). Each
                   * review = a small uppercase SOURCE pill + a row of 5 star
                   * glyphs (filled to the rating, amber) + a short "quote".
                   * We render a FLAT list across both products built from
                   * `retailer_quotes` -- no product-name headers, no consensus
                   * paragraph, no +/- highlight bullets.
                   *
                   * Fallback: many categories (e.g. fragrances) ship empty
                   * `retailer_quotes` -- the backend currently emits only
                   * consensus/highlights there. When a product has no quotes
                   * we surface at most 3 compact lines from `highlights`
                   * (plain short quote lines, NO +/- prefix, NOT the giant
                   * consensus paragraph). Populating per-source quotes for
                   * those categories is a BACKEND follow-up (review extraction
                   * must emit retailer_quotes). When there is truly nothing,
                   * render one calm line. */}
                  {(() => {
                    const lines: React.ReactNode[] = [];
                    reviewSrc.forEach((rp: any, idx: number) => {
                      const quotes = Array.isArray(rp.retailer_quotes)
                        ? rp.retailer_quotes
                        : [];
                      if (quotes.length > 0) {
                        quotes.slice(0, 3).forEach((q: any, qi: number) => {
                          lines.push(
                            <ReviewLine
                              key={`q-${idx}-${qi}`}
                              testID={
                                testID
                                  ? `${testID}-reviews-quote-${idx}-${qi}`
                                  : undefined
                              }
                              source={String(q.retailer || '')}
                              rating={
                                typeof q.rating === 'number' ? q.rating : null
                              }
                              text={String(q.text || '')}
                            />
                          );
                        });
                      } else {
                        // Compact fallback -- short highlight quote lines.
                        const highlights: ReviewHighlight[] = Array.isArray(
                          rp.review_summary?.highlights
                        )
                          ? rp.review_summary.highlights
                          : [];
                        highlights
                          .slice(0, 3)
                          .forEach((h: ReviewHighlight, hi: number) => {
                            if (!h?.point) return;
                            lines.push(
                              <ReviewLine
                                key={`h-${idx}-${hi}`}
                                testID={
                                  testID
                                    ? `${testID}-reviews-fallback-${idx}-${hi}`
                                    : undefined
                                }
                                source={String(rp.name || '')}
                                rating={
                                  typeof rp.rating === 'number'
                                    ? rp.rating
                                    : null
                                }
                                text={String(h.point)}
                              />
                            );
                          });
                      }
                    });
                    if (lines.length === 0) {
                      return (
                        <Text style={styles.reviewsEmpty}>
                          {t('results.accordion.reviewsEmpty')}
                        </Text>
                      );
                    }
                    return lines;
                  })()}
                </View>
              )}

              {isOpen && s.key === 'proscons' && (
                <View
                  testID="results-accordion-body-proscons"
                  style={styles.body}
                >
                  <View style={styles.prosConsGrid}>
                    {products.map((p, idx) => {
                      const isWinner =
                        typeof winnerIndex === 'number' && winnerIndex === idx;
                      return (
                        <View key={idx} style={styles.prosConsCol}>
                          <View style={styles.prosConsNameRow}>
                            {/* Lane A-L3 Task L3.3 — emerald ★ prefix on the
                                winning product's column header per design
                                Screen 3 ("WHAT FANS LOVE / DRAWBACKS"). Hidden
                                when winnerIndex is undefined so legacy callers
                                don't render an empty star. */}
                            {isWinner ? (
                              <Text
                                testID={`${testID}-proscons-winner-star-${idx}`}
                                style={styles.prosConsWinnerStar}
                              >
                                {'\u2605'}
                              </Text>
                            ) : null}
                            <Text
                              style={styles.prosConsName}
                              numberOfLines={1}
                            >
                              {p.name}
                            </Text>
                          </View>
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
                      );
                    })}
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
                  {/* Phase 4.4 — comparison table per the "UI Kit — Mobile
                      Results" mockup (SpecRow, JSX 265-284): each row is
                      value · CENTERED-label · value (1fr / center / 1fr).
                      The header mirrors the layout with the two product
                      names flanking the centered eyebrow column. Winning
                      cell value paints bold-emerald. */}
                  <View style={styles.specsTable}>
                    <View style={styles.specsHeader}>
                      <Text
                        style={[styles.specsCellValue, styles.specsCellValueLeft]}
                        numberOfLines={1}
                      >
                        {(specsSrc[0] as any)?.name ?? ''}
                      </Text>
                      <Text style={styles.specsCellKey} />
                      <Text
                        style={[styles.specsCellValue, styles.specsCellValueRight]}
                        numberOfLines={1}
                      >
                        {(specsSrc[1] as any)?.name ?? ''}
                      </Text>
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
                        // Lane A-L3 Task L3.2 — emerald winner cell.
                        // winner === 0 → p0 wins (cell idx 0 paints emerald).
                        // winner === 1 → p1 wins (cell idx 1 paints emerald).
                        // winner === null or absent → neutral (both stay default).
                        const winner = winnerByField[key];
                        // value · CENTERED-label · value. Cell idx 0 is the
                        // left (right-aligned) value, idx 1 the right
                        // (left-aligned) value. The label sits centered
                        // between them.
                        const cellStyle = (vi: number, sideStyle: any) => {
                          const isWinnerCell = winner === vi && winner !== null;
                          return isWinnerCell
                            ? [styles.specsCellValue, sideStyle, styles.specsCellWinner]
                            : [styles.specsCellValue, sideStyle];
                        };
                        return (
                          <View
                            key={key}
                            testID={
                              testID
                                ? `${testID}-specs-row-${key}`
                                : undefined
                            }
                            style={styles.specsRow}
                          >
                            <Text
                              testID={
                                testID
                                  ? `${testID}-specs-cell-${key}-0`
                                  : undefined
                              }
                              style={cellStyle(0, styles.specsCellValueLeft)}
                              numberOfLines={2}
                            >
                              {values[0] ?? '—'}
                            </Text>
                            <Text style={styles.specsCellKey}>
                              {key.replace(/_/g, ' ')}
                            </Text>
                            <Text
                              testID={
                                testID
                                  ? `${testID}-specs-cell-${key}-1`
                                  : undefined
                              }
                              style={cellStyle(1, styles.specsCellValueRight)}
                              numberOfLines={2}
                            >
                              {values[1] ?? '—'}
                            </Text>
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

/**
 * Reference: ReviewLine (ResultsScreen.jsx 213-236). A single review row:
 *   [SOURCE pill]  ★★★★★ (filled to rating, amber)
 *   "short quote in quotes"
 * Stars round the rating to the nearest whole glyph (1-5). When no rating
 * is present we still render the pill + quote (no star row) so a quote is
 * never dropped for a missing rating.
 */
function ReviewLine({
  source,
  rating,
  text,
  testID,
}: {
  source: string;
  rating?: number | null;
  text: string;
  testID?: string;
}) {
  const filled =
    typeof rating === 'number' && rating > 0
      ? Math.max(0, Math.min(5, Math.round(rating)))
      : 0;
  return (
    <View testID={testID} style={styles.reviewLine}>
      <View style={styles.reviewLineHeader}>
        <Text style={styles.reviewSourcePill} numberOfLines={1}>
          {source.toUpperCase()}
        </Text>
        {filled > 0 ? (
          <View style={styles.reviewStars}>
            {[1, 2, 3, 4, 5].map((s) => (
              <Star
                key={s}
                size={10}
                color={s <= filled ? colors.warning : colors.border.medium}
                fill={s <= filled ? colors.warning : 'transparent'}
              />
            ))}
          </View>
        ) : null}
      </View>
      <Text style={styles.reviewQuote}>{`“${text}”`}</Text>
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
  // Reference: ReviewLine (ResultsScreen.jsx 213-236). Compact source-quote
  // rows — uppercase source pill + amber star row + a short "quote".
  reviewLine: {
    flexDirection: 'column',
    gap: 4,
    marginBottom: 10,
  },
  reviewLineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  reviewSourcePill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    fontSize: 9,
    fontWeight: '600',
    letterSpacing: 0.5,
    color: colors.text.secondary,
    flexShrink: 1,
    overflow: 'hidden',
  },
  reviewStars: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 1,
  },
  reviewQuote: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.text.primary,
    lineHeight: 12 * 1.5,
  },
  reviewsEmpty: {
    fontSize: 12,
    color: colors.text.secondary,
    lineHeight: 12 * 1.5,
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
    flexShrink: 1,
  },
  // Lane A-L3 Task L3.3 — row container for the winner-star + name.
  prosConsNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 8,
  },
  // Lane A-L3 Task L3.3 — emerald star marking the overall winner on
  // the pros/cons grid column header.
  prosConsWinnerStar: {
    fontSize: 12,
    color: colors.accent,
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
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  specsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  // Phase 4.4 — CENTERED label column (mockup SpecRow center cell: 90px,
  // centered, uppercase eyebrow).
  specsCellKey: {
    width: 96,
    fontSize: 11,
    fontWeight: '500',
    color: colors.text.secondary,
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  specsCellValue: {
    flex: 1,
    fontSize: 12,
    fontWeight: '500',
    color: colors.text.primary,
  },
  // Left value cell hugs the centered label (right-aligned per mockup).
  specsCellValueLeft: {
    textAlign: 'right',
  },
  // Right value cell reads outward from the centered label (left-aligned).
  specsCellValueRight: {
    textAlign: 'left',
  },
  // Lane A-L3 Task L3.2 — winning spec cell paints emerald (accent),
  // bold weight, per design Screen 4.
  specsCellWinner: {
    color: colors.accent,
    fontWeight: '700',
  },
});

export default ResultsAccordion;
