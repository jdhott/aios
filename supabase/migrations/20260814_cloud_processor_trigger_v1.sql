-- AIOS Cloud Processor Trigger v1
-- Apply once in the Supabase SQL editor before enabling API-triggered processing.

create table if not exists public.aios_processor_state (
    id text primary key,
    running boolean not null default false,
    trigger_pending boolean not null default false,
    processing_requested boolean not null default false,
    requested_at timestamptz,
    started_at timestamptz,
    finished_at timestamptz,
    failed_at timestamptz,
    updated_at timestamptz not null default now(),
    constraint aios_processor_state_singleton check (id = 'default')
);

insert into public.aios_processor_state (
    id,
    running,
    trigger_pending,
    processing_requested
)
values (
    'default',
    false,
    false,
    false
)
on conflict (id) do nothing;


create or replace function public.request_aios_processing()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    s public.aios_processor_state%rowtype;
    should_start boolean;
begin
    select *
    into s
    from public.aios_processor_state
    where id = 'default'
    for update;

    -- Recover automatically from a processor lease that outlived the
    -- Cloud Run Job's 20-minute timeout.
    if s.running
       and s.started_at is not null
       and s.started_at < now() - interval '30 minutes'
    then
        s.running := false;
        s.trigger_pending := false;
    end if;

    -- Recover a trigger claim if Cloud Run never accepted/started it.
    if not s.running
       and s.trigger_pending
       and s.requested_at is not null
       and s.requested_at < now() - interval '10 minutes'
    then
        s.trigger_pending := false;
    end if;

    should_start := not s.running and not s.trigger_pending;

    update public.aios_processor_state
    set
        running = s.running,
        processing_requested = true,
        trigger_pending = (
            s.trigger_pending or should_start
        ),
        requested_at = now(),
        updated_at = now()
    where id = 'default';

    return jsonb_build_object(
        'should_trigger', should_start,
        'running', s.running,
        'trigger_pending', (s.trigger_pending or should_start),
        'processing_requested', true
    );
end;
$$;


create or replace function public.release_aios_processing_trigger()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.aios_processor_state
    set
        trigger_pending = false,
        processing_requested = true,
        updated_at = now()
    where id = 'default';

    return jsonb_build_object(
        'released', true,
        'processing_requested', true
    );
end;
$$;


create or replace function public.begin_aios_processing()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    s public.aios_processor_state%rowtype;
begin
    select *
    into s
    from public.aios_processor_state
    where id = 'default'
    for update;

    if s.running
       and s.started_at is not null
       and s.started_at >= now() - interval '30 minutes'
    then
        return jsonb_build_object(
            'acquired', false,
            'reason', 'already_running'
        );
    end if;

    update public.aios_processor_state
    set
        running = true,
        trigger_pending = false,
        processing_requested = false,
        started_at = now(),
        failed_at = null,
        updated_at = now()
    where id = 'default';

    return jsonb_build_object(
        'acquired', true
    );
end;
$$;


create or replace function public.finish_aios_processing_cycle()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    s public.aios_processor_state%rowtype;
begin
    select *
    into s
    from public.aios_processor_state
    where id = 'default'
    for update;

    if s.processing_requested then
        update public.aios_processor_state
        set
            processing_requested = false,
            running = true,
            trigger_pending = false,
            updated_at = now()
        where id = 'default';

        return jsonb_build_object(
            'rerun_needed', true
        );
    end if;

    update public.aios_processor_state
    set
        running = false,
        trigger_pending = false,
        processing_requested = false,
        finished_at = now(),
        updated_at = now()
    where id = 'default';

    return jsonb_build_object(
        'rerun_needed', false
    );
end;
$$;


create or replace function public.fail_aios_processing()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.aios_processor_state
    set
        running = false,
        trigger_pending = false,
        processing_requested = true,
        failed_at = now(),
        updated_at = now()
    where id = 'default';

    return jsonb_build_object(
        'failed', true,
        'processing_requested', true
    );
end;
$$;


revoke all on public.aios_processor_state from anon, authenticated;
revoke all on function public.request_aios_processing() from public;
revoke all on function public.release_aios_processing_trigger() from public;
revoke all on function public.begin_aios_processing() from public;
revoke all on function public.finish_aios_processing_cycle() from public;
revoke all on function public.fail_aios_processing() from public;

-- Supabase service-role requests bypass RLS and can execute these functions.
