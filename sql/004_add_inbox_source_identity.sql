-- AIOS Supabase Inbox External Identity Bridge
create unique index if not exists inbox_items_source_identity_uidx
on public.inbox_items (source, source_item_id)
where source_item_id is not null;
