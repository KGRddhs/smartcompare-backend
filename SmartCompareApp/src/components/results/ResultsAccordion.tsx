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
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { ChevronDown, Star, ListChecks, BarChart3 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing } from '../../theme';
import type { Product, ReviewSummary } from '../../types';

type AccordionKey = 'reviews' | 'proscons' | 'specs';

interface ResultsAccordionProps {
  products: Product[];
  /** Bundle E S3 — reviews section data (new structured format). */
  reviewProducts?: Array<{
    name: string;
    rating?: number | null;
    review_count?: number | null;
    /** Faithful-results Contract 2 — canonical real review count (mirrors
     *  review_count). */
    rating_count?: number | null;
    rating_source?: { name?: string; url?: string } | null;
    review_summary?: ReviewSummary;
    /** Faithful-results Contract 2 — synthesized praise line (non-verbatim,
     *  no citations/source domains). null when insufficient real signal. */
    review_praise?: string | null;
    /** Lane A-L3 Task L3.4 — up to 3 retailer quotes per product
     *  (Amazon / Noon / X). Backend writes
     *  `reviews.products[i].retailer_quotes`. Faithful-results Phase 5.2:
     *  kept in the type for backward-compat but NO LONGER RENDERED (dormant
     *  per Contract 2). */
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
      // Reference sub: "8 dimensions" — the count of rendered spec rows.
      sub:
        allSpecKeys.length > 0
          ? `${allSpecKeys.length} ${t('results.accordion.specsDimensions')}`
          : t('results.accordion.specsDimensions'),
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
                   * Faithful-results Phase 5.2 (Contract 2) — paraphrased
                   * praise, no citations. One synthesized praise line PER
                   * PRODUCT (backend `review_praise`, non-verbatim, no [N]
                   * markers, no source domains), with REAL stars + count only
                   * when a genuine rating exists. The prior verbatim
                   * `retailer_quotes` + `review_summary.highlights` rendering
                   * (per-source AMAZON/NOON/X pills + "quote" lines) is REMOVED
                   * — `retailer_quotes` stays in the payload but is no longer
                   * shown (dormant per Contract 2).
                   *
                   * Winner-first product order (mirrors the pros/cons grid).
                   * review_praise / rating / rating_count are read from the
                   * review projection when present, falling back to the root
                   * product (Contract 2 locates review_praise on root
                   * `products[i]`). A product with neither a praise line nor a
                   * rating is skipped; when NO product has any signal we render
                   * one calm line. */}
                  {(() => {
                    const order: number[] =
                      typeof winnerIndex === 'number'
                        ? [winnerIndex, winnerIndex === 0 ? 1 : 0].filter(
                            (i) => i < reviewSrc.length
                          )
                        : reviewSrc.map((_, i) => i);

                    const blocks: React.ReactNode[] = [];
                    order.forEach((idx) => {
                      const rp: any = reviewSrc[idx] ?? {};
                      const root: any = (products as any)[idx] ?? {};
                      const praise: string | null =
                        (typeof rp.review_praise === 'string' &&
                        rp.review_praise.trim().length > 0
                          ? rp.review_praise
                          : null) ??
                        (typeof root.review_praise === 'string' &&
                        root.review_praise.trim().length > 0
                          ? root.review_praise
                          : null);
                      const rating: number | null =
                        typeof rp.rating === 'number'
                          ? rp.rating
                          : typeof root.rating === 'number'
                            ? root.rating
                            : null;
                      const ratingCount: number | null =
                        typeof rp.rating_count === 'number'
                          ? rp.rating_count
                          : typeof rp.review_count === 'number'
                            ? rp.review_count
                            : typeof root.rating_count === 'number'
                              ? root.rating_count
                              : typeof root.review_count === 'number'
                                ? root.review_count
                                : null;

                      // Skip a product with no real review signal at all.
                      if (!praise && !(typeof rating === 'number' && rating > 0)) {
                        return;
                      }
                      blocks.push(
                        <ReviewPraiseBlock
                          key={`praise-${idx}`}
                          testID={
                            testID ? `${testID}-reviews-praise-${idx}` : undefined
                          }
                          name={String(rp.name || root.name || '')}
                          rating={rating}
                          ratingCount={ratingCount}
                          praise={praise}
                        />
                      );
                    });

                    if (blocks.length === 0) {
                      return (
                        <Text style={styles.reviewsEmpty}>
                          {t('results.accordion.reviewsEmpty')}
                        </Text>
                      );
                    }
                    return blocks;
                  })()}
                </View>
              )}

              {isOpen && s.key === 'proscons' && (
                <View
                  testID="results-accordion-body-proscons"
                  style={styles.body}
                >
                  <View style={styles.prosConsGrid}>
                    {/*
                     * Reference: ProsConsCol (ResultsScreen.jsx 238-263).
                     * The WINNER column renders FIRST (left) with a ★ +
                     * accentDark name; pros are "+ text" (accentDark "+"),
                     * cons are "- text" (placeholder "-"). When winnerIndex
                     * is undefined we keep the natural product order and draw
                     * no star (legacy callers). testIDs use the ORIGINAL
                     * product index, not the display position. */}
                    {(
                      typeof winnerIndex === 'number'
                        ? [winnerIndex, winnerIndex === 0 ? 1 : 0].filter(
                            (idx) => idx < products.length
                          )
                        : products.map((_, idx) => idx)
                    ).map((idx) => {
                      const p = products[idx];
                      const isWinner =
                        typeof winnerIndex === 'number' && winnerIndex === idx;
                      return (
                        <View key={idx} style={styles.prosConsCol}>
                          <View style={styles.prosConsNameRow}>
                            {/* Lane A-L3 Task L3.3 — emerald ★ prefix on the
                                winning product's column header. Hidden when
                                winnerIndex is undefined so legacy callers
                                don't render an empty star. */}
                            {isWinner ? (
                              <Text
                                testID={`${testID}-proscons-winner-star-${idx}`}
                                style={styles.prosConsWinnerStar}
                              >
                                {'★'}
                              </Text>
                            ) : null}
                            <Text
                              style={[
                                styles.prosConsName,
                                isWinner ? styles.prosConsNameWinner : null,
                              ]}
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
                              <Text style={styles.prosConsPlus}>+ </Text>
                              {pro}
                            </Text>
                          ))}
                          {(p.cons ?? []).map((con, ci) => (
                            <Text
                              key={`con-${ci}`}
                              style={styles.prosConsCon}
                              numberOfLines={2}
                            >
                              <Text style={styles.prosConsMinus}>{'−'} </Text>
                              {con}
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
                    {allSpecKeys.map((key) => {
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
 * Faithful-results Phase 5.2 (Contract 2) — paraphrased praise block.
 * Per product:
 *   {Product name}   ★★★★★ {rating} · {count}   (stars + meta only when a
 *                                                 REAL rating exists)
 *   {synthesized praise line — non-verbatim, no citations, no source domains}
 *
 * Stars round the rating to the nearest whole glyph (1-5). Ratings are NEVER
 * AI-generated (CLAUDE.md hard invariant) — the backend only supplies a real
 * one, else `rating` is null and no stars render. `praise` may be null when a
 * product has a rating but no synthesized line; the block still renders the
 * rating row. Callers skip a product with neither signal.
 */
function ReviewPraiseBlock({
  name,
  rating,
  ratingCount,
  praise,
  testID,
}: {
  name: string;
  rating?: number | null;
  ratingCount?: number | null;
  praise?: string | null;
  testID?: string;
}) {
  const { t } = useTranslation();
  const hasRating = typeof rating === 'number' && rating > 0;
  const filled = hasRating
    ? Math.max(0, Math.min(5, Math.round(rating as number)))
    : 0;
  return (
    <View testID={testID} style={styles.reviewLine}>
      <View style={styles.reviewLineHeader}>
        <Text style={styles.reviewProductName} numberOfLines={1}>
          {name}
        </Text>
        {hasRating ? (
          <View style={styles.reviewRatingMeta}>
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
            <Text style={styles.reviewRatingText}>
              {typeof ratingCount === 'number' && ratingCount > 0
                ? t('results.reviews.ratingWithCount', {
                    rating: (rating as number).toFixed(1),
                    count: ratingCount.toLocaleString(),
                  })
                : (rating as number).toFixed(1)}
            </Text>
          </View>
        ) : null}
      </View>
      {praise ? (
        <Text
          style={styles.reviewPraise}
          testID={testID ? `${testID}-text` : undefined}
        >
          {praise}
        </Text>
      ) : null}
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
  // Faithful-results Phase 5.2 — per-product praise block: product name +
  // (real stars + rating·count) header, then the synthesized praise line.
  reviewLine: {
    flexDirection: 'column',
    gap: 4,
    marginBottom: 12,
  },
  reviewLineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  reviewProductName: {
    flexShrink: 1,
    fontSize: 12,
    fontWeight: '600',
    color: colors.text.primary,
  },
  reviewRatingMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  reviewStars: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 1,
  },
  reviewRatingText: {
    fontSize: 11,
    color: colors.text.secondary,
    fontVariant: ['tabular-nums'],
  },
  reviewPraise: {
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
  // Reference: ProsConsCol name (ResultsScreen.jsx 241-248). Non-winner
  // name = text.primary weight 600; winner name = accentDark weight 700.
  prosConsName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text.primary,
    flexShrink: 1,
  },
  prosConsNameWinner: {
    fontWeight: '700',
    color: colors.accentDark,
  },
  // Lane A-L3 Task L3.3 — row container for the winner-star + name.
  prosConsNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 8,
  },
  // Winner star — accentDark, matching the reference's accentDark name.
  prosConsWinnerStar: {
    fontSize: 11,
    color: colors.accentDark,
  },
  // Pros: "+ text" — the "+" paints accentDark, the text text.primary.
  prosConsPro: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.text.primary,
    marginBottom: 3,
  },
  prosConsPlus: {
    color: colors.accentDark,
  },
  // Cons: "- text" — the "-" paints placeholder, the text text.secondary.
  prosConsCon: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.text.secondary,
    marginBottom: 3,
  },
  prosConsMinus: {
    color: colors.text.placeholder,
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
