-- AIOS Focus Context Loop v1
-- Durable user-approved context remains in public.tasks.context.
alter table public.tasks
    add column if not exists focus_context_help_state text,
    add column if not exists focus_context_draft text,
    add column if not exists focus_context_question text,
    add column if not exists focus_context_help_updated_at timestamptz;
