/**
 * CategoryProfile — Faithful-results Phase 3.1 (Contract 1).
 *
 * Source of truth: .qa-discovery/CONTRACTS.md "Contract 1 — Category profile
 * block" (🟢 LOCKED 2026-06-17).
 *
 * ONE generic, category-driven block — NO per-category branching. The backend
 * emits `products[i].category_profile = { category, fields: [{key,label,value}] }`
 * already correct + ordered for the product's category (fragrance → scent
 * family + notes + longevity/sillage; supplements → count/dosage/form;
 * electronics → display/processor/…). The FE renders the ordered fields as a
 * curated `label · value` list per product, so users see what *defines* each
 * product without expanding the full side-by-side Specs table (which keeps its
 * own em-dash treatment in the "Dig deeper" accordion).
 *
 * Contract rules honored:
 *  - Render `fields` IN ORDER as `label · value`.
 *  - Hide the whole block when NEITHER product has a non-empty `fields`.
 *  - SYMMETRY / no-blank-second-product: each product renders its OWN populated
 *    fields independently (a field N/A for a product is already OMITTED upstream
 *    — never dashed here). Backend builds both from the same ordered key set, so
 *    columns typically align; when one product lacks a field it simply shows
 *    fewer rows.
 *  - i18n: `t('results.spec.' + key, { defaultValue: label })` — prefer the
 *    catalog string, fall back to the backend-supplied English label. Backend
 *    is never coupled to i18n.
 *
 * Winner-first column order + emerald ★ on the winning product mirror the
 * established 2-up pattern in ResultsAccordion (ProsConsCol).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, radii, typography } from '../../theme';
import type { Product, CategoryProfileField } from '../../types';

export interface CategoryProfileProps {
  products: Product[];
  /** Overall winner index — emphasizes that product's column (★ + accent name).
   *  Undefined → no star, natural product order (legacy/低-confidence callers). */
  winnerIndex?: 0 | 1;
  testID?: string;
}

/** A product has a renderable profile when it carries ≥1 ordered field. */
function profileFields(product: Product | undefined): CategoryProfileField[] {
  const fields = product?.category_profile?.fields;
  if (!Array.isArray(fields)) return [];
  // Defensive: drop any malformed entry so a single bad row can't blank the
  // block. Backend guarantees value is a non-empty cleaned string, but a
  // stale/partial client payload should degrade gracefully.
  return fields.filter(
    (f) =>
      f &&
      typeof f.key === 'string' &&
      typeof f.value === 'string' &&
      f.value.trim().length > 0,
  );
}

export function CategoryProfile({
  products,
  winnerIndex,
  testID = 'category-profile',
}: CategoryProfileProps) {
  const { t } = useTranslation();

  // Per-product populated field lists. Index-aligned with `products`.
  const perProduct = products.map((p) => profileFields(p));

  // Contract: hide the whole block when NEITHER product has fields.
  const anyFields = perProduct.some((f) => f.length > 0);
  if (!anyFields) return null;

  // Winner-first column order (mirrors ProsConsCol). testIDs use the ORIGINAL
  // product index, not the display position, so tests/analytics stay stable.
  const order: number[] =
    typeof winnerIndex === 'number'
      ? [winnerIndex, winnerIndex === 0 ? 1 : 0].filter((i) => i < products.length)
      : products.map((_, i) => i);

  return (
    <View style={styles.wrapper} testID={testID}>
      <Text style={styles.eyebrow}>{t('results.categoryProfile.title')}</Text>
      <View style={styles.grid}>
        {order.map((idx) => {
          const product = products[idx];
          const fields = perProduct[idx];
          const isWinner = typeof winnerIndex === 'number' && winnerIndex === idx;
          return (
            <View key={idx} style={styles.col} testID={`${testID}-col-${idx}`}>
              <View style={styles.nameRow}>
                {isWinner ? (
                  <Text
                    style={styles.winnerStar}
                    testID={`${testID}-winner-star-${idx}`}
                  >
                    {'★'}
                  </Text>
                ) : null}
                <Text
                  style={[styles.name, isWinner ? styles.nameWinner : null]}
                  numberOfLines={1}
                >
                  {product?.name}
                </Text>
              </View>
              {fields.length > 0 ? (
                fields.map((f) => (
                  <View
                    key={f.key}
                    style={styles.fieldRow}
                    testID={`${testID}-field-${idx}-${f.key}`}
                  >
                    <Text style={styles.fieldLabel} numberOfLines={1}>
                      {t(`results.spec.${f.key}`, { defaultValue: f.label })}
                    </Text>
                    <Text style={styles.fieldValue}>{f.value}</Text>
                  </View>
                ))
              ) : (
                // The OTHER product has fields but this one doesn't — keep the
                // column present (name only) so the 2-up layout stays balanced.
                // No apologetic copy, no dash rows.
                <View testID={`${testID}-col-${idx}-empty`} />
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // Lean treatment to match the design — a single bordered card grouping the
  // curated profile (consistent with the "Dig deeper" panel chrome), sitting
  // on the page background with vertical rhythm.
  wrapper: {
    marginBottom: spacing.xl,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    padding: spacing.base,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginBottom: spacing.md,
  },
  grid: {
    flexDirection: 'row',
    gap: spacing.base,
  },
  col: {
    flex: 1,
    minWidth: 0,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  winnerStar: {
    fontSize: 11,
    color: colors.accentDark,
  },
  name: {
    flexShrink: 1,
    fontSize: 12,
    fontWeight: '600',
    color: colors.text.primary,
    lineHeight: 12 * 1.3,
  },
  nameWinner: {
    fontWeight: '700',
    color: colors.accentDark,
  },
  fieldRow: {
    marginBottom: spacing.sm,
  },
  // Label above value (vertical) keeps long GCC values + Arabic readable in a
  // narrow 2-up column without truncating the value.
  fieldLabel: {
    fontSize: 11,
    color: colors.text.secondary,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  fieldValue: {
    ...typography.caption,
    fontSize: 13,
    color: colors.text.primary,
    lineHeight: 13 * 1.4,
  },
});

export default CategoryProfile;
