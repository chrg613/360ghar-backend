-- Make users.email optional to support phone-only auth
-- Also normalize existing blank emails to NULL

-- 1) Drop NOT NULL first to allow setting NULLs
ALTER TABLE public.users
    ALTER COLUMN email DROP NOT NULL;

-- 2) Normalize empty strings to NULL for consistency
UPDATE public.users
SET email = NULL
WHERE email IS NULL OR trim(email) = '';

-- Note: UNIQUE(email) remains; PostgreSQL allows multiple NULLs in a UNIQUE column
