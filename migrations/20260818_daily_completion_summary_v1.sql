create table if not exists public.daily_completion_summaries (
    summary_date date primary key,
    fingerprint text not null,
    summary text not null default '',
    completed_count integer not null default 0,
    generated_at timestamptz not null default now()
);
