alter table public.tasks
add column if not exists breakdown_state text;

alter table public.tasks
add column if not exists breakdown_request_context text;

alter table public.tasks
add column if not exists breakdown_proposal jsonb;

alter table public.tasks
add column if not exists breakdown_requested_at timestamptz;

alter table public.tasks
add column if not exists breakdown_completed_at timestamptz;

alter table public.tasks
drop constraint if exists tasks_breakdown_state_check;

alter table public.tasks
add constraint tasks_breakdown_state_check
check (
  breakdown_state is null
  or breakdown_state in ('pending','proposed','no_proposal','accepted','failed')
);
