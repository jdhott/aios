create table if not exists public.daily_journal (
  journal_date date primary key,
  body text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
