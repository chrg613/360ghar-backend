-- Enable pgvector extension and add property_embeddings table for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Table to store embeddings for properties
CREATE TABLE IF NOT EXISTS public.property_embeddings (
    property_id BIGINT PRIMARY KEY REFERENCES public.properties(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    emb_text_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ANN index for fast similarity search (cosine distance)
-- Choose HNSW for recall/latency balance. Requires pgvector >= 0.5.0
DO $$
BEGIN
    BEGIN
        CREATE INDEX IF NOT EXISTS idx_property_embeddings_hnsw
            ON public.property_embeddings USING hnsw (embedding vector_cosine_ops);
    EXCEPTION WHEN undefined_object THEN
        -- Fallback to IVF flat if HNSW not available
        CREATE INDEX IF NOT EXISTS idx_property_embeddings_ivfflat
            ON public.property_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    END;
END $$;

-- Lightweight state table to track last processed watermark for incremental sync
CREATE TABLE IF NOT EXISTS public.vector_sync_state (
    key TEXT PRIMARY KEY,
    last_watermark TIMESTAMPTZ
);

-- Seed a default row for properties if not present
INSERT INTO public.vector_sync_state (key, last_watermark)
VALUES ('properties', NULL)
ON CONFLICT (key) DO NOTHING;

