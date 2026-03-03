-- Migration: Update comparisons table for full JSONB blob storage
-- Idempotent: safe to run multiple times

-- Add new columns (IF NOT EXISTS via DO block)
DO $$
BEGIN
    -- Add full_response column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'full_response'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN full_response JSONB;
    END IF;

    -- Add query column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'query'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN query TEXT;
    END IF;

    -- Add input_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'input_type'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN input_type TEXT DEFAULT 'text';
    END IF;

    -- Add product_names column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comparisons' AND column_name = 'product_names'
    ) THEN
        ALTER TABLE comparisons ADD COLUMN product_names TEXT[];
    END IF;
END $$;

-- Add indexes (IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_comparisons_user_created
    ON comparisons (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comparisons_product_names
    ON comparisons USING GIN (product_names);

CREATE INDEX IF NOT EXISTS idx_comparisons_query_search
    ON comparisons USING GIN (to_tsvector('english', coalesce(query, '')));
