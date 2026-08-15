create table if not exists public.task_focus_guidance (
    task_id uuid primary key references public.tasks(id) on delete cascade,
    generation_key text not null,
    starter_step text not null,
    starter_minutes integer not null check (starter_minutes in (5, 10, 15, 20)),
    source text not null default 'ai',
    updated_at timestamptz not null default now()
);
create index if not exists task_focus_guidance_updated_at_idx
    on public.task_focus_guidance(updated_at desc);
