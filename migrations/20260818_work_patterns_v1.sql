create table if not exists public.work_patterns (
  id uuid primary key default gen_random_uuid(), name text not null, context text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.work_pattern_steps (
  id uuid primary key default gen_random_uuid(), pattern_id uuid not null references public.work_patterns(id) on delete cascade,
  step_order integer not null, title text not null, context text, created_at timestamptz not null default now(), unique(pattern_id, step_order)
);
create index if not exists work_pattern_steps_pattern_order_idx on public.work_pattern_steps(pattern_id, step_order);
