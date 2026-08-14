-- AIOS Supabase Inbox Review POC
-- Creates durable, source-neutral human-review state for inbox items.
-- Safe to run more than once.

create table if not exists public.inbox_reviews (
    id uuid primary key default gen_random_uuid(),

    inbox_item_id uuid not null
        references public.inbox_items(id)
        on delete cascade,

    review_type text not null
        check (
            review_type in (
                'clarification',
                'possible_duplicate'
            )
        ),

    state text not null default 'pending'
        check (
            state in (
                'pending',
                'awaiting_answer',
                'pending_confirmation',
                'resolved'
            )
        ),

    payload jsonb not null default '{}'::jsonb,
    decision jsonb null,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    resolved_at timestamptz null
);

create index if not exists inbox_reviews_inbox_item_id_idx
    on public.inbox_reviews (inbox_item_id);

create index if not exists inbox_reviews_state_created_at_idx
    on public.inbox_reviews (state, created_at);

create index if not exists inbox_reviews_type_state_idx
    on public.inbox_reviews (review_type, state);

create or replace function public.set_inbox_reviews_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_inbox_reviews_updated_at
    on public.inbox_reviews;

create trigger set_inbox_reviews_updated_at
before update on public.inbox_reviews
for each row
execute function public.set_inbox_reviews_updated_at();

comment on table public.inbox_reviews is
    'Durable human-review workflow state for AIOS inbox items.';
