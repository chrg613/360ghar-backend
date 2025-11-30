-- Notification infrastructure tables for Supabase
-- Creates device_tokens, notifications, and notification_deliveries

-- Ensure UUID generation is available
create extension if not exists "pgcrypto";

create table if not exists public.device_tokens (
    id uuid primary key default gen_random_uuid(),
    token text not null unique,
    user_id uuid references auth.users (id) on delete set null,
    platform text not null check (platform in ('android', 'ios', 'web')),
    app_version text,
    locale text,
    is_active boolean default true,
    last_seen timestamptz default now(),
    created_at timestamptz default now()
);

create index if not exists idx_device_tokens_user on public.device_tokens (user_id);
create index if not exists idx_device_tokens_active on public.device_tokens (is_active);

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    body text not null,
    data jsonb,
    audience_type text not null,
    target_user_id uuid references auth.users (id) on delete set null,
    topic text,
    created_at timestamptz default now()
);

create index if not exists idx_notifications_target_user on public.notifications (target_user_id);
create index if not exists idx_notifications_created_at on public.notifications (created_at desc);

create table if not exists public.notification_deliveries (
    id uuid primary key default gen_random_uuid(),
    notification_id uuid references public.notifications (id) on delete cascade,
    device_token_id uuid references public.device_tokens (id) on delete set null,
    status text not null,
    fcm_message_id text,
    sent_at timestamptz,
    opened_at timestamptz,
    error_code text,
    created_at timestamptz default now()
);

create index if not exists idx_notification_deliveries_notification on public.notification_deliveries (notification_id);
create index if not exists idx_notification_deliveries_device_token on public.notification_deliveries (device_token_id);
create index if not exists idx_notification_deliveries_status on public.notification_deliveries (status);
