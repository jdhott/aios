-- AIOS Supabase Inbox Capture Metadata POC
alter table public.inbox_items
    add column if not exists clean_text text null,
    add column if not exists due_date date null,
    add column if not exists project_hint text null,
    add column if not exists is_urgent boolean not null default false,
    add column if not exists is_important boolean not null default false,
    add column if not exists is_just_do_it boolean not null default false;
