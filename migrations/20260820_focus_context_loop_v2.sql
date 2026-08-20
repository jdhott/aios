-- AIOS Focus Context Loop v2
-- Temporary answer used only while AIOS incorporates a coaching response into
-- an editable draft. Durable approved context remains public.tasks.context.
alter table public.tasks
    add column if not exists focus_context_answer text;
