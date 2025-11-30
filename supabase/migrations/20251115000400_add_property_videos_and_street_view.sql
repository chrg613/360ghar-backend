BEGIN;

-- Add media fields for videos and Google Street View to properties
ALTER TABLE properties
    ADD COLUMN IF NOT EXISTS video_urls JSONB,
    ADD COLUMN IF NOT EXISTS google_street_view_url TEXT;

COMMIT;
