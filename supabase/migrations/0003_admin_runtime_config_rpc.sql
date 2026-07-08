-- Admin-gated writes to runtime_config (reads are already public via RLS).
-- Lets the app's admin settings UI register the GB10 gateway URL / default
-- model without anyone touching SQL or dashboard env vars.
create or replace function public.admin_set_runtime_config(cfg_key text, cfg_value text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin(auth.uid()) then
    raise exception 'not authorized';
  end if;
  if cfg_key is null or length(trim(cfg_key)) = 0 then
    raise exception 'key required';
  end if;
  if cfg_value is null or length(trim(cfg_value)) = 0 then
    delete from public.runtime_config where key = cfg_key;
    return;
  end if;
  insert into public.runtime_config (key, value)
  values (cfg_key, cfg_value)
  on conflict (key) do update set value = excluded.value, updated_at = now();
end;
$$;

grant execute on function public.admin_set_runtime_config(text, text) to authenticated;
