alter table public.projects add column if not exists work_generation_question text;
alter table public.projects add column if not exists work_generation_answer text;
alter table public.projects add column if not exists work_generation_context_update text;
alter table public.projects add column if not exists work_generation_round integer not null default 0;

alter table public.projects drop constraint if exists projects_work_generation_state_check;
alter table public.projects add constraint projects_work_generation_state_check check (
  work_generation_state is null or work_generation_state in (
    'pending','actionable','waiting','failed','clarification','answer_pending','context_review'
  )
);
