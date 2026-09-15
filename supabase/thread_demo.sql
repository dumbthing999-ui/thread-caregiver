-- Separate from existing project data; browser roles cannot access these records.
create table if not exists public.thread_demo_sessions (
  token_hash text primary key check (token_hash ~ '^[a-f0-9]{64}$'),
  version bigint not null default 1,
  state jsonb not null check (octet_length(state::text) < 262144),
  expires_at timestamptz not null default now() + interval '24 hours'
);
alter table public.thread_demo_sessions enable row level security;
revoke all on public.thread_demo_sessions from anon, authenticated;

create or replace function public.thread_demo_load(p_token text) returns jsonb
language sql security definer set search_path = '' as $$
  select jsonb_build_object('version', version, 'state', state)
  from public.thread_demo_sessions where token_hash = p_token and expires_at > now();
$$;

create or replace function public.thread_demo_save(p_token text, p_version bigint, p_state jsonb) returns boolean
language plpgsql security definer set search_path = '' as $$
declare changed integer;
begin
  if p_version = 0 then
    perform pg_advisory_xact_lock(746872656164);
    delete from public.thread_demo_sessions where expires_at <= now();
    if (select count(*) from public.thread_demo_sessions) >= 1000 then return false; end if;
    insert into public.thread_demo_sessions(token_hash, state) values (p_token, p_state)
      on conflict do nothing;
  else
    update public.thread_demo_sessions set state = p_state, version = version + 1
      where token_hash = p_token and version = p_version and expires_at > now();
  end if;
  get diagnostics changed = row_count;
  return changed = 1;
end;
$$;
revoke all on function public.thread_demo_load(text) from public, anon, authenticated;
revoke all on function public.thread_demo_save(text, bigint, jsonb) from public, anon, authenticated;
grant execute on function public.thread_demo_load(text) to service_role;
grant execute on function public.thread_demo_save(text, bigint, jsonb) to service_role;
