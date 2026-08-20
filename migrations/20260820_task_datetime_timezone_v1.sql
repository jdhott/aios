-- AIOS task datetime timezone normalization v1
--
-- due_at and defer_until represent absolute instants. Existing date/date-only
-- values are interpreted as midnight in America/Toronto before conversion to
-- timestamptz. Existing timezone-aware timestamps preserve their instant.
--
-- This migration is intentionally type-aware because earlier AIOS prototypes
-- may have created these columns as date, timestamp, text, or timestamptz.

do $$
declare
    col_name text;
    col_type text;
begin
    foreach col_name in array array['due_at', 'defer_until'] loop
        select data_type
          into col_type
          from information_schema.columns
         where table_schema = 'public'
           and table_name = 'tasks'
           and column_name = col_name;

        if col_type is null then
            raise exception 'public.tasks.% does not exist', col_name;
        elsif col_type = 'timestamp with time zone' then
            raise notice 'public.tasks.% already uses timestamptz', col_name;
        elsif col_type = 'date' then
            execute format(
                'alter table public.tasks alter column %I type timestamptz using (%I::timestamp at time zone ''America/Toronto'')',
                col_name, col_name
            );
        elsif col_type = 'timestamp without time zone' then
            execute format(
                'alter table public.tasks alter column %I type timestamptz using (%I at time zone ''America/Toronto'')',
                col_name, col_name
            );
        elsif col_type in ('text', 'character varying') then
            execute format(
                $fmt$
                alter table public.tasks alter column %I type timestamptz using (
                    case
                        when %I is null or btrim(%I) = '' then null
                        when btrim(%I) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                            then (btrim(%I)::date::timestamp at time zone 'America/Toronto')
                        else btrim(%I)::timestamptz
                    end
                )
                $fmt$,
                col_name, col_name, col_name, col_name, col_name, col_name
            );
        else
            raise exception 'Unsupported type for public.tasks.%: %', col_name, col_type;
        end if;

        -- Earlier API versions could send YYYY-MM-DD into an already-timestamptz
        -- column. PostgreSQL then commonly interpreted that as 00:00 UTC. AIOS
        -- did not yet support explicit due/defer times at 00:00 UTC, so these
        -- exact-midnight legacy values can safely be restored to local midnight
        -- on the same intended calendar date. Real time-of-day snoozes are not
        -- touched.
        execute format(
            'update public.tasks set %I = (((%I at time zone ''UTC'')::date)::timestamp at time zone ''America/Toronto'') where %I is not null and (%I at time zone ''UTC'')::time = time ''00:00:00''',
            col_name, col_name, col_name, col_name
        );
    end loop;
end $$;
