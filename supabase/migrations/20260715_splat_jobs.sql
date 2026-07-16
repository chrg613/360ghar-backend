-- ============================================================
-- Splat Jobs Table: 3D Gaussian Splatting Pipeline Lab
-- ============================================================
-- Each row represents a single pipeline run:
--   video upload → frame extraction → SfM → 3DGS training → 
--   compression → collision generation → Walk Mode viewer
-- ============================================================

CREATE TYPE splat_job_status AS ENUM (
  'pending',      -- Created, waiting for video upload
  'uploading',    -- Video being uploaded to storage
  'extracting',   -- FFmpeg extracting frames from video
  'converting',   -- 360° equirectangular → cubemap perspective faces
  'sfm',          -- COLMAP Structure from Motion running
  'training',     -- Nerfstudio Splatfacto training (GPU required)
  'compressing',  -- PLY → SPZ compression + optimization
  'collision',    -- Generating collision mesh (.glb) for Walk Mode
  'ready',        -- Pipeline complete, viewer URLs available
  'failed'        -- Pipeline failed, check error_message
);

CREATE TYPE splat_quality_preset AS ENUM (
  'fast',         -- ~5-10k iterations, 5-10 min on RTX 4090
  'balanced',     -- ~15k iterations, 15-20 min on RTX 4090 (recommended)
  'quality'       -- ~30k iterations, 30-45 min on RTX 4090
);

CREATE TABLE IF NOT EXISTS splat_jobs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Job metadata
  title               TEXT NOT NULL DEFAULT 'Untitled Scene',
  status              splat_job_status NOT NULL DEFAULT 'pending',
  progress            INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  stage_message       TEXT,

  -- Pipeline options set at job creation
  is_360_video        BOOLEAN NOT NULL DEFAULT FALSE,
  mask_people         BOOLEAN NOT NULL DEFAULT TRUE,
  quality_preset      splat_quality_preset NOT NULL DEFAULT 'balanced',
  fps_extraction      NUMERIC(4,1) NOT NULL DEFAULT 2.0,

  -- Storage paths / URLs (populated as pipeline runs)
  video_path          TEXT,           -- Supabase storage path: splat-jobs/{user_id}/{job_id}/input.mp4
  splat_url           TEXT,           -- Public or signed URL to final .spz file
  ply_url             TEXT,           -- Full-quality .ply (before compression)
  collision_url       TEXT,           -- .collision.glb for Walk Mode
  supersplat_url      TEXT,           -- superspl.at share URL (if iframe preview available)
  thumbnail_url       TEXT,           -- Preview screenshot of the scene

  -- Pipeline metrics
  frames_total        INTEGER,        -- Total frames extracted from video
  frames_used         INTEGER,        -- Frames after quality filtering
  sfm_cameras         INTEGER,        -- Cameras registered by COLMAP
  sfm_points          INTEGER,        -- 3D points in COLMAP sparse model
  splat_gaussians     INTEGER,        -- Final Gaussian count in trained model
  training_iterations INTEGER,        -- Actual iterations run

  -- Compute infrastructure
  daytona_sandbox_id  TEXT,           -- Daytona sandbox ID for this job
  gpu_available       BOOLEAN,        -- Was GPU available in the sandbox?
  compute_duration_s  INTEGER,        -- Total compute time in seconds

  -- Error handling
  error_message       TEXT,           -- Human-readable error message
  error_code          TEXT,           -- Machine-readable code (e.g. 'GPU_REQUIRED', 'COLMAP_FAILED')

  -- Timestamps
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at        TIMESTAMPTZ       -- Set when status becomes 'ready' or 'failed'
);

-- Index for fast user job lookups
CREATE INDEX idx_splat_jobs_user_id ON splat_jobs(user_id, created_at DESC);
CREATE INDEX idx_splat_jobs_status ON splat_jobs(status) WHERE status NOT IN ('ready', 'failed');

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_splat_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  IF NEW.status IN ('ready', 'failed') AND OLD.status NOT IN ('ready', 'failed') THEN
    NEW.completed_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER splat_jobs_updated_at
  BEFORE UPDATE ON splat_jobs
  FOR EACH ROW EXECUTE FUNCTION update_splat_jobs_updated_at();

-- ============================================================
-- Row-Level Security: Users can only access their own jobs
-- ============================================================
ALTER TABLE splat_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own jobs"
  ON splat_jobs FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own jobs"
  ON splat_jobs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own jobs"
  ON splat_jobs FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own jobs"
  ON splat_jobs FOR DELETE
  USING (auth.uid() = user_id);

-- Service role (backend) can bypass RLS for pipeline status updates
-- Backend uses SUPABASE_SECRET_KEY which has service role privileges
