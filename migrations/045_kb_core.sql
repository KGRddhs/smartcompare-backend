-- Migration 045: the owned knowledge base core, kb_* (S81-14 KB-SCHEMA, S81)
--
-- Ten tables, one view, five functions, three triggers. Per JUICE (brand +
-- identity + concentration): kb_products, kb_specs, kb_reviews. Per SKU (juice
-- + ml): kb_variants, kb_offers (SKU x merchant x market), kb_images. Registry
-- kb_merchants; loop kb_gaps, kb_feedback, kb_coverage_daily. Ids come from
-- app/services/kb_service.py (kb_product_id, kb_variant_key).
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: no code reads or writes kb_*.
-- APPLY ORDER: apply before any kb_* writer flag flips (S81-15 / S81-16 /
-- S81-17); none against 047 or 050. PostgreSQL 15 or later (security_invoker).
--
-- Service role only (044 / 050; the 037 both-readings rule): RLS on, no
-- policy, REVOKE ALL from PUBLIC, anon, authenticated, service_role, then one
-- GRANT to service_role, for every table, the view and every function
-- (functions: SECURITY INVOKER, pinned search_path, EXECUTE for service_role
-- only). No users FK and no user / email / address column (the 043 fence sees
-- no kb_* table).
--
-- kb_feedback.device_key is a pseudonymous device identifier: the S81-05
-- HMAC-SHA256 of the device header under DEVICE_KEY_PEPPER, NOT a user id and
-- NOT the raw header, so it sits outside the 043 user-table fence by design.
-- It is nullable (a vote with no key is stored device-less and never counts
-- toward one vote per device). Deletion: S81-22's account-deletion hook (its
-- compare_request_id filter is served by idx_kb_feedback_request) plus the
-- 365-day TTL prune kb_prune_feedback(365) run by S81-22's nightly job.
--
-- Offers: captured_at is the first observation of one exact (variant,
-- merchant, market, currency, amount, list_vs_sale) row and never moves. A
-- re-observation upserts on kb_offers_observation and sets last_seen,
-- in_stock, evidence_rung and canonical_url only; a changed amount is a NEW
-- row. Latest = last_seen DESC, (list_vs_sale = 'sale') DESC, captured_at
-- DESC, id DESC per (variant, merchant, market, currency): the R-S14-1 order
-- last_seen DESC, captured_at DESC, id DESC with the sale key placed right
-- after last_seen DESC, so among the rows last seen at the same instant the
-- sale wins, then the newest capture (the sale is what the shopper pays, also
-- when the list amount changed during the sale: F2-1); idx_kb_offers_latest
-- carries the same key in the same position, and the prune ages rows by
-- last_seen. The view and the card serve the latest row whatever its age or
-- stock: freshness and stock filtering are S81-18's reader contract.
--
-- kb_merchants: the decode reads host, registry, status, deny, blocked_reason
-- and partner only; country, currency_hint, platform, adapter and
-- search_template are display / ops-only columns. A denied host is STORED with
-- deny = true and status 'blocked' (the owner's blocked list), so no deny
-- label check applies to kb_merchants. Every host column and the host of
-- every URL column of kb_* has a last label that carries a letter and is
-- neither all digits nor 0x-hex (a WHATWG parser or inet_aton reads 10.0.0.1
-- and 127.0.0.0x1 as IPv4): one belt, the leaf's KB_HOST_TOP_LABEL_REGEX, in
-- the *_top_label_letter constraints (F2-4; a digit registrable label such as
-- 4711.com stays valid).
-- The kb_* data tables refuse the denied labels (basenotes, fimgs, fragrantica,
-- parfumo) by CHECK: a belt that is a strict SUBSET of the rule,
-- deny_hosts.kb_source_allowed in the builders (a belt never refuses a row a
-- builder accepted; the rule also refuses path, query, hyphenated and
-- top-level label tokens).
--
-- Postcheck: APPLY_045_3_POSTCHECK.sql. Rollback: migrations/rollback/045_kb_core.sql

BEGIN;

DO $$
BEGIN
  IF current_setting('server_version_num')::int < 150000 THEN
    RAISE EXCEPTION '045 needs PostgreSQL 15 or later';
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION public.kb_gtin_check_digit_ok(p_gtin text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
SECURITY INVOKER
SET search_path TO 'public'
AS $$
  SELECT CASE
    WHEN p_gtin !~ '^([0-9]{8}|[0-9]{12,14})$' THEN false
    ELSE (
      SELECT (10 - (sum(
        substr(p_gtin, i, 1)::int
        * CASE WHEN (length(p_gtin) - i) % 2 = 1 THEN 3 ELSE 1 END
      ) % 10)) % 10
      FROM generate_series(1, length(p_gtin) - 1) AS i
    ) = substr(p_gtin, length(p_gtin), 1)::int
  END
$$;

CREATE OR REPLACE FUNCTION public.kb_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO 'public'
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

CREATE TABLE IF NOT EXISTS public.kb_merchants (
    host text PRIMARY KEY CHECK (
        host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
    ),
    country text CHECK (country IS NULL OR country ~ '^[A-Z]{2,3}$'),
    currency_hint text CHECK (currency_hint IS NULL OR currency_hint ~ '^[A-Z]{3}$'),
    platform text CHECK (platform IS NULL OR char_length(platform) BETWEEN 1 AND 32),
    platform_confidence text CHECK (
        platform_confidence IS NULL OR platform_confidence IN ('mechanism', 'probe', 'url', 'operator')
    ),
    adapter text CHECK (adapter IS NULL OR char_length(adapter) BETWEEN 1 AND 64),
    search_template text CHECK (
        search_template IS NULL OR char_length(search_template) BETWEEN 1 AND 1024
    ),
    registry jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(registry) = 'array'),
    robots jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(robots) = 'object'),
    politeness jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(politeness) = 'object'),
    health jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(health) = 'object'),
    challenge jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(challenge) = 'object'),
    tos jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(tos) = 'object'),
    deny boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'live', 'blocked')),
    blocked_reason text CHECK (blocked_reason IS NULL OR char_length(blocked_reason) BETWEEN 1 AND 64),
    partner jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(partner) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_merchants_host_top_label_letter CHECK (
        host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_merchants_deny_is_blocked CHECK (NOT deny OR status = 'blocked'),
    CONSTRAINT kb_merchants_blocked_has_reason CHECK (status <> 'blocked' OR blocked_reason IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.kb_products (
    id text PRIMARY KEY CHECK (char_length(id) BETWEEN 14 AND 512 AND left(id, 11) = 'fragrances|'),
    brand text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 128),
    line text CHECK (line IS NULL OR char_length(line) BETWEEN 1 AND 256),
    name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 256),
    concentration text CHECK (
        concentration IS NULL
        OR concentration IN ('Extrait', 'Parfum Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum')
    ),
    audience text CHECK (audience IS NULL OR audience IN ('men', 'women', 'unisex')),
    identity_confidence text NOT NULL CHECK (identity_confidence IN ('high', 'medium', 'low')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.kb_variants (
    id text PRIMARY KEY,
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    concentration text CHECK (
        concentration IS NULL
        OR concentration IN ('Extrait', 'Parfum Intense', 'EDP', 'EDT', 'EDC', 'Eau Fraiche', 'Parfum')
    ),
    size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999),
    gtin text CHECK (gtin IS NULL OR public.kb_gtin_check_digit_ok(gtin)),
    sku text CHECK (sku IS NULL OR char_length(sku) BETWEEN 1 AND 128),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_variants_id_extends_product CHECK (
        left(id, char_length(product_id) + 1) = product_id || '|'
        AND char_length(id) BETWEEN char_length(product_id) + 2 AND char_length(product_id) + 5
    )
);

CREATE TABLE IF NOT EXISTS public.kb_offers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id text NOT NULL REFERENCES public.kb_variants (id) ON DELETE CASCADE,
    merchant_id text NOT NULL REFERENCES public.kb_merchants (host) ON DELETE CASCADE,
    market text NOT NULL CHECK (market ~ '^[A-Z]{2,3}$'),
    amount numeric(14, 3) NOT NULL CHECK (amount > 0),
    observed_currency char(3) NOT NULL CHECK (observed_currency ~ '^[A-Z]{3}$'),
    evidence_rung text NOT NULL CHECK (
        evidence_rung IN ('own_token', 'page_evidence', 'expected_missing', 'platform_api', 'operator')
    ),
    size_ml integer CHECK (size_ml IS NULL OR size_ml BETWEEN 1 AND 9999),
    list_vs_sale text NOT NULL DEFAULT 'unknown' CHECK (list_vs_sale IN ('list', 'sale', 'unknown')),
    in_stock boolean,
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    captured_at timestamptz NOT NULL DEFAULT now(),
    canonical_url text NOT NULL CHECK (
        canonical_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^?#[:space:]]*$'
        AND canonical_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'
    ),
    CONSTRAINT kb_offers_url_top_label_letter CHECK (
        canonical_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_offers_seen_order CHECK (first_seen <= last_seen),
    CONSTRAINT kb_offers_url_on_merchant CHECK (
        split_part(split_part(canonical_url, '://', 2), '/', 1) = merchant_id
        OR right(split_part(split_part(canonical_url, '://', 2), '/', 1), char_length(merchant_id) + 1)
        = '.' || merchant_id
    ),
    CONSTRAINT kb_offers_observation UNIQUE (
        variant_id, merchant_id, market, observed_currency, amount, list_vs_sale
    )
);

CREATE TABLE IF NOT EXISTS public.kb_images (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    variant_id text REFERENCES public.kb_variants (id) ON DELETE CASCADE,
    url text NOT NULL CHECK (
        url ~ '^https://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
        AND url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'
        AND char_length(url) <= 2048
    ),
    provenance_host text NOT NULL CHECK (
        provenance_host ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
        AND provenance_host !~ '(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]'
    ),
    source text NOT NULL CHECK (
        source IN ('retailer_jsonld', 'retailer_og', 'brand_site', 'partner_feed', 'operator')
    ),
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_images_url_top_label_letter CHECK (
        url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_images_provenance_top_label_letter CHECK (
        provenance_host ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_images_product_url UNIQUE (product_id, url)
);

CREATE TABLE IF NOT EXISTS public.kb_specs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    lang char(2) NOT NULL DEFAULT 'en' CHECK (lang IN ('en', 'ar')),
    value text NOT NULL CHECK (char_length(value) BETWEEN 1 AND 2000),
    source_url text CHECK (
        source_url IS NULL OR (
            source_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
            AND source_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'
            AND char_length(source_url) <= 2048
        )
    ),
    extractor text NOT NULL CHECK (char_length(extractor) BETWEEN 1 AND 64),
    model text CHECK (model IS NULL OR char_length(model) BETWEEN 1 AND 64),
    cited boolean NOT NULL DEFAULT false,
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_specs_source_top_label_letter CHECK (
        source_url IS NULL OR source_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_specs_cited_has_source CHECK (NOT cited OR source_url IS NOT NULL),
    CONSTRAINT kb_specs_product_field_lang UNIQUE (product_id, field, lang)
);

CREATE TABLE IF NOT EXISTS public.kb_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id text NOT NULL REFERENCES public.kb_products (id) ON DELETE CASCADE,
    source text NOT NULL CHECK (
        source IN ('retailer_jsonld', 'retailer_widget', 'brand_site', 'marketplace')
    ),
    aggregate_rating numeric(3, 2) CHECK (aggregate_rating IS NULL OR aggregate_rating BETWEEN 0 AND 5),
    review_count integer CHECK (review_count IS NULL OR review_count >= 0),
    source_url text NOT NULL CHECK (
        source_url ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^#[:space:]]*$'
        AND source_url !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'
        AND char_length(source_url) <= 2048
    ),
    captured_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kb_reviews_source_top_label_letter CHECK (
        source_url ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_reviews_has_signal CHECK (aggregate_rating IS NOT NULL OR review_count IS NOT NULL),
    CONSTRAINT kb_reviews_product_url UNIQUE (product_id, source_url)
);

CREATE TABLE IF NOT EXISTS public.kb_gaps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_key text NOT NULL CHECK (char_length(product_key) BETWEEN 14 AND 520),
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    demand_count integer NOT NULL DEFAULT 1 CHECK (demand_count >= 0),
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    state text NOT NULL DEFAULT 'open' CHECK (
        state IN ('open', 'queued', 'needs_operator', 'licence', 'closed')
    ),
    source_hint text CHECK (
        source_hint IS NULL OR (
            char_length(source_hint) BETWEEN 1 AND 256
            AND (
                source_hint ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'
                OR source_hint ~ '^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+/[^?#[:space:]]*$'
            )
            AND source_hint !~ '(^|[.])(basenotes|fimgs|fragrantica|parfumo)[.]'
            AND source_hint !~ '^https?://([^/]*[.])?(basenotes|fimgs|fragrantica|parfumo)[.]'
        )
    ),
    CONSTRAINT kb_gaps_hint_top_label_letter CHECK (
        source_hint IS NULL OR source_hint ~ '^(https?://)?([^/]*[.])?(?!(0x[0-9a-f]*|[0-9]+)(/|$))[a-z0-9-]*[a-z][a-z0-9-]*(/|$)'
    ),
    CONSTRAINT kb_gaps_seen_order CHECK (first_seen <= last_seen),
    CONSTRAINT kb_gaps_key_field UNIQUE (product_key, field)
);

CREATE TABLE IF NOT EXISTS public.kb_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    compare_request_id uuid NOT NULL,
    product_id text REFERENCES public.kb_products (id) ON DELETE CASCADE,
    field text NOT NULL CHECK (field ~ '^[a-z][a-z0-9_]{0,63}$'),
    verdict text NOT NULL CHECK (verdict IN ('correct', 'wrong', 'unsure')),
    device_key text CHECK (device_key IS NULL OR device_key ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.kb_coverage_daily (
    day date NOT NULL,
    metric text NOT NULL CHECK (metric ~ '^[a-z][a-z0-9_.:-]{0,127}$'),
    value numeric NOT NULL,
    n integer NOT NULL CHECK (n >= 0),
    PRIMARY KEY (day, metric)
);

CREATE INDEX IF NOT EXISTS idx_kb_merchants_status ON public.kb_merchants (status);
CREATE INDEX IF NOT EXISTS idx_kb_variants_product ON public.kb_variants (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_variants_gtin ON public.kb_variants (gtin) WHERE gtin IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_offers_latest ON public.kb_offers (
    variant_id, merchant_id, market, observed_currency, last_seen DESC, (list_vs_sale = 'sale') DESC,
    captured_at DESC, id DESC
);
CREATE INDEX IF NOT EXISTS idx_kb_offers_merchant ON public.kb_offers (merchant_id);
CREATE INDEX IF NOT EXISTS idx_kb_images_product ON public.kb_images (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_images_variant ON public.kb_images (variant_id) WHERE variant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_reviews_product ON public.kb_reviews (product_id);
CREATE INDEX IF NOT EXISTS idx_kb_gaps_open_demand
    ON public.kb_gaps (demand_count DESC, last_seen DESC) WHERE state = 'open';
CREATE INDEX IF NOT EXISTS idx_kb_feedback_device_key
    ON public.kb_feedback (device_key) WHERE device_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_feedback_product ON public.kb_feedback (product_id) WHERE product_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_feedback_created ON public.kb_feedback (created_at);
CREATE INDEX IF NOT EXISTS idx_kb_feedback_request ON public.kb_feedback (compare_request_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_feedback_one_vote
    ON public.kb_feedback (device_key, compare_request_id, field, coalesce(product_id, ''))
    WHERE device_key IS NOT NULL;

CREATE OR REPLACE TRIGGER kb_merchants_set_updated_at
BEFORE UPDATE ON public.kb_merchants
FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at();
CREATE OR REPLACE TRIGGER kb_products_set_updated_at
BEFORE UPDATE ON public.kb_products
FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at();
CREATE OR REPLACE TRIGGER kb_variants_set_updated_at
BEFORE UPDATE ON public.kb_variants
FOR EACH ROW EXECUTE FUNCTION public.kb_set_updated_at();

CREATE OR REPLACE VIEW public.kb_offers_latest
WITH (security_invoker = true) AS
SELECT DISTINCT ON (o.variant_id, o.merchant_id, o.market, o.observed_currency)
    o.id,
    o.variant_id,
    o.merchant_id,
    o.market,
    o.amount,
    o.observed_currency,
    o.evidence_rung,
    o.size_ml,
    o.list_vs_sale,
    o.in_stock,
    o.first_seen,
    o.last_seen,
    o.captured_at,
    o.canonical_url
FROM public.kb_offers AS o
ORDER BY
    o.variant_id ASC, o.merchant_id ASC, o.market ASC, o.observed_currency ASC,
    o.last_seen DESC, (o.list_vs_sale = 'sale') DESC, o.captured_at DESC, o.id DESC;

CREATE OR REPLACE FUNCTION public.kb_prune_offers(p_max_age_days integer, p_keep_per_merchant integer)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO 'public'
AS $$
DECLARE
  v_deleted integer;
BEGIN
  IF p_max_age_days IS NULL OR p_max_age_days < 1 OR p_max_age_days > 3650
     OR p_keep_per_merchant IS NULL OR p_keep_per_merchant < 1 OR p_keep_per_merchant > 1000 THEN
    RAISE EXCEPTION 'kb_prune_offers: bounds out of range';
  END IF;
  WITH ranked AS (
    SELECT
      o.id,
      o.last_seen,
      row_number() OVER (
        PARTITION BY o.variant_id, o.merchant_id, o.market, o.observed_currency
        ORDER BY o.last_seen DESC, (o.list_vs_sale = 'sale') DESC, o.captured_at DESC, o.id DESC
      ) AS rn
    FROM public.kb_offers AS o
  )
  DELETE FROM public.kb_offers AS d
  USING ranked AS r
  WHERE d.id = r.id
    AND r.rn > p_keep_per_merchant
    AND r.last_seen < now() - make_interval(days => p_max_age_days);
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END
$$;

CREATE OR REPLACE FUNCTION public.kb_prune_feedback(p_days integer)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO 'public'
AS $$
DECLARE
  v_deleted integer;
BEGIN
  IF p_days IS NULL OR p_days < 1 OR p_days > 3650 THEN
    RAISE EXCEPTION 'kb_prune_feedback: bounds out of range';
  END IF;
  DELETE FROM public.kb_feedback AS f
  WHERE f.created_at < now() - make_interval(days => p_days);
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END
$$;

CREATE OR REPLACE FUNCTION public.kb_product_card(p_product_id text, p_lang text DEFAULT 'en')
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path TO 'public'
AS $$
  SELECT jsonb_build_object(
    'product', to_jsonb(p.*),
    'variants', coalesce((
      SELECT jsonb_agg(to_jsonb(v.*) ORDER BY v.id)
      FROM public.kb_variants AS v
      WHERE v.product_id = p.id
    ), '[]'::jsonb),
    'offers', coalesce((
      SELECT jsonb_agg(to_jsonb(l.*) ORDER BY l.variant_id, l.merchant_id, l.market, l.observed_currency)
      FROM (
        SELECT DISTINCT ON (o.variant_id, o.merchant_id, o.market, o.observed_currency) o.*
        FROM public.kb_offers AS o
        WHERE o.variant_id IN (SELECT v2.id FROM public.kb_variants AS v2 WHERE v2.product_id = p.id)
        ORDER BY
          o.variant_id, o.merchant_id, o.market, o.observed_currency,
          o.last_seen DESC, (o.list_vs_sale = 'sale') DESC, o.captured_at DESC, o.id DESC
      ) AS l
    ), '[]'::jsonb),
    'images', coalesce((
      SELECT jsonb_agg(to_jsonb(i.*) ORDER BY i.captured_at DESC, i.id)
      FROM public.kb_images AS i
      WHERE i.product_id = p.id
    ), '[]'::jsonb),
    'specs', coalesce((
      SELECT jsonb_agg(to_jsonb(s.*) ORDER BY s.field)
      FROM (
        SELECT DISTINCT ON (s0.field) s0.*
        FROM public.kb_specs AS s0
        WHERE s0.product_id = p.id AND s0.cited AND s0.lang IN (p_lang, 'en')
        ORDER BY s0.field, (s0.lang = p_lang) DESC
      ) AS s
    ), '[]'::jsonb),
    'rating', (
      SELECT jsonb_build_object(
        'sources', count(*),
        'review_count', sum(r.review_count),
        'rating', round(
          sum(r.aggregate_rating * r.review_count)
          FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL)
          / nullif(sum(r.review_count)
            FILTER (WHERE r.aggregate_rating IS NOT NULL AND r.review_count IS NOT NULL), 0),
          2
        )
      )
      FROM public.kb_reviews AS r
      WHERE r.product_id = p.id
    )
  )
  FROM public.kb_products AS p
  WHERE p.id = p_product_id
$$;

ALTER TABLE public.kb_merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_specs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_coverage_daily ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.kb_merchants FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_products FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_variants FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_offers FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_images FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_specs FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_reviews FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_gaps FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_feedback FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_coverage_daily FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON TABLE public.kb_offers_latest FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_merchants TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_products TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_variants TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_offers TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_images TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_specs TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_reviews TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_gaps TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_feedback TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.kb_coverage_daily TO service_role;
GRANT SELECT ON TABLE public.kb_offers_latest TO service_role;

REVOKE ALL ON FUNCTION public.kb_gtin_check_digit_ok(text) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.kb_set_updated_at() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.kb_prune_offers(integer, integer) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.kb_prune_feedback(integer) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.kb_product_card(text, text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.kb_gtin_check_digit_ok(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_set_updated_at() TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_prune_offers(integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_prune_feedback(integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.kb_product_card(text, text) TO service_role;

COMMIT;
