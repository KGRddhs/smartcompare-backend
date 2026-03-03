-- Migration: Ensure search_logs and products tables exist with correct schema
-- Idempotent: safe to run multiple times

-- search_logs table
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    query TEXT NOT NULL,
    input_type TEXT DEFAULT 'text',
    products_found JSONB DEFAULT '[]'::jsonb,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    cost DECIMAL(10, 6) DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_logs_user_created
    ON search_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_logs_created
    ON search_logs (created_at DESC);

-- products table (ensure canonical_name unique constraint)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'products' AND constraint_type = 'UNIQUE'
        AND constraint_name = 'products_canonical_name_key'
    ) THEN
        -- Table may already exist from earlier schema; add constraint if missing
        ALTER TABLE products ADD CONSTRAINT products_canonical_name_key UNIQUE (canonical_name);
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        CREATE TABLE products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            canonical_name TEXT UNIQUE NOT NULL,
            brand TEXT,
            category TEXT,
            variants JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
END $$;

CREATE INDEX IF NOT EXISTS idx_products_canonical_name
    ON products (canonical_name);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products (category);
