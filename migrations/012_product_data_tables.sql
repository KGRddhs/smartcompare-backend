-- Product Data Persistence: L2 cache + training data
-- Product key = md5(brand|name|variant)[:12] — matches Redis cache key pattern from extraction_service.py

CREATE TABLE IF NOT EXISTS product_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_key TEXT NOT NULL,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    variant TEXT,
    category TEXT,
    specs JSONB NOT NULL,
    source TEXT DEFAULT 'gpt',
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_key)
);
CREATE INDEX idx_specs_key ON product_specs (product_key);
CREATE INDEX idx_specs_fetched ON product_specs (fetched_at DESC);
ALTER TABLE product_specs ENABLE ROW LEVEL SECURITY;
CREATE POLICY specs_select ON product_specs FOR SELECT USING (true);
CREATE POLICY specs_insert ON product_specs FOR INSERT WITH CHECK (true);
CREATE POLICY specs_update ON product_specs FOR UPDATE USING (true);

CREATE TABLE IF NOT EXISTS product_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_key TEXT NOT NULL,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    variant TEXT,
    region TEXT NOT NULL,
    amount NUMERIC,
    currency TEXT,
    retailer TEXT,
    url TEXT,
    source_method TEXT,
    estimated BOOLEAN DEFAULT false,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_prices_key_region ON product_prices (product_key, region);
CREATE INDEX idx_prices_fetched ON product_prices (fetched_at DESC);
ALTER TABLE product_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY prices_select ON product_prices FOR SELECT USING (true);
CREATE POLICY prices_insert ON product_prices FOR INSERT WITH CHECK (true);

CREATE TABLE IF NOT EXISTS product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_key TEXT NOT NULL,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    variant TEXT,
    reviews JSONB NOT NULL,
    source TEXT DEFAULT 'gpt',
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_key)
);
CREATE INDEX idx_reviews_key ON product_reviews (product_key);
CREATE INDEX idx_reviews_fetched ON product_reviews (fetched_at DESC);
ALTER TABLE product_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY reviews_select ON product_reviews FOR SELECT USING (true);
CREATE POLICY reviews_insert ON product_reviews FOR INSERT WITH CHECK (true);
CREATE POLICY reviews_update ON product_reviews FOR UPDATE USING (true);
