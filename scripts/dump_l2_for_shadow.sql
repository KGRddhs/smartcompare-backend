-- L2 dump for the I4 shadow harness (scripts/shadow_experiments.py).
--
-- Produces one JSON object per L2 product, joining the freshest product_specs
-- row with its freshest product_reviews row and its freshest bahrain
-- product_prices row (matched on lower(brand||name)). This is the sandbox-safe
-- input path: run it via the Supabase MCP channel (execute_sql), write the
-- `row` column to a jsonl, and point SHADOW_L2_DUMP at the file. The harness
-- then reconstructs verdict inputs with ZERO network + ZERO Serper.
--
-- Output: a single column `row` of jsonb; each value has
--   {brand, name, variant, category, specs, reviews, price}
-- where price is {amount,currency,retailer,url,source_method,estimated} or null.
--
-- WHY brand+name join (not product_key): the three tables hash product_key
-- independently per cache-key recipe, but all carry brand/name/variant/category
-- as plain columns. The baseline run (nocache=true, 2026-06-10) wrote all three
-- after fresh extraction, so the freshest rows ARE what the baseline verdicts saw.

WITH spec_ranked AS (
  SELECT *, row_number() OVER (
           PARTITION BY lower(brand || '|' || name)
           ORDER BY fetched_at DESC
         ) AS rn
  FROM product_specs
),
rev_ranked AS (
  SELECT brand, name, reviews, fetched_at,
         row_number() OVER (
           PARTITION BY lower(brand || '|' || name)
           ORDER BY fetched_at DESC
         ) AS rn
  FROM product_reviews
),
price_ranked AS (
  SELECT brand, name, amount, currency, retailer, url, source_method, estimated, fetched_at,
         row_number() OVER (
           PARTITION BY lower(brand || '|' || name)
           ORDER BY fetched_at DESC
         ) AS rn
  FROM product_prices
  WHERE region = 'bahrain'
)
SELECT jsonb_build_object(
         'brand', s.brand,
         'name', s.name,
         'variant', s.variant,
         'category', s.category,
         'specs', s.specs,
         'reviews', COALESCE(r.reviews, '{}'::jsonb),
         'price', CASE WHEN p.amount IS NULL THEN NULL ELSE jsonb_build_object(
                    'amount', p.amount,
                    'currency', p.currency,
                    'retailer', p.retailer,
                    'url', p.url,
                    'source_method', p.source_method,
                    'estimated', COALESCE(p.estimated, false)
                  ) END
       ) AS row
FROM spec_ranked s
LEFT JOIN rev_ranked   r ON lower(r.brand || '|' || r.name) = lower(s.brand || '|' || s.name) AND r.rn = 1
LEFT JOIN price_ranked p ON lower(p.brand || '|' || p.name) = lower(s.brand || '|' || s.name) AND p.rn = 1
WHERE s.rn = 1
  AND s.fetched_at > now() - interval '30 days'
ORDER BY s.category, s.brand, s.name;
