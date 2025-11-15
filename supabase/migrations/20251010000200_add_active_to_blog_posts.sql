-- Add 'active' column to blog_posts for publication status
alter table if exists public.blog_posts
  add column if not exists active boolean;

-- Ensure default and not-null constraints
alter table public.blog_posts
  alter column active set default false;

update public.blog_posts set active = false where active is null;

alter table public.blog_posts
  alter column active set not null;

-- Helpful index for filtering by publication status
create index if not exists ix_blog_posts_active on public.blog_posts (active);

