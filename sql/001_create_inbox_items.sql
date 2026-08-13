-- AIOS Supabase Inbox POC
-- Creates a source-neutral processing queue for Brain Dump and future sources.
-- Safe to run more than once.

create table if not exists public.inbox_items (
    id uuid primary key default gen_random_uuid(),

    text text not null,
    notes text[] not null default '{}',

    -- User-facing capture/source identity.
    -- Examples: brain_dump, reminders, email, share_sheet.
    source text not null default 'brain_dump',

    -- Optional ID from an upstream external source such as Apple Reminders.
    -- The Supabase inbox row's own lifecycle identity is always `id`.
    source_item_id text null,
    source_metadata jsonb not null default '{}'::jsonb,

    status text not null default 'pending'
        check (status in ('pending', 'review', 'processed', 'archived')),

    review_type text null,
    review_state text null
        check (
            review_state is null
            or review_state in ('pending', 'resolved')
        ),
    review_payload jsonb not null default '{}'::jsonb,
    review_decision text null,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    processed_at timestamptz null
);

create index if not exists inbox_items_status_created_at_idx
    on public.inbox_items (status, created_at);

create index if not exists inbox_items_source_status_idx
    on public.inbox_items (source, status);

create or replace function public.set_inbox_items_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_inbox_items_updated_at
    on public.inbox_items;

create trigger set_inbox_items_updated_at
before update on public.inbox_items
for each row
execute function public.set_inbox_items_updated_at();

comment on table public.inbox_items is
    'Source-neutral AIOS intake queue. Brain Dump is one source; AIOS processing consumes pending rows.';
