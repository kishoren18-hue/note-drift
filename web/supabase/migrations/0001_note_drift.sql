-- note-drift: saved reports and AI usage quota.
-- Every table has row-level security on. Users can only see their own reports,
-- plus any report its owner explicitly made public.

create table if not exists public.nd_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title text not null default 'Untitled report' check (char_length(title) between 1 and 120),
  note text not null check (char_length(note) between 1 and 20000),
  summary text not null check (char_length(summary) between 1 and 20000),
  summary_source text not null default 'pasted' check (summary_source in ('pasted', 'claude', 'claude-challenge')),
  model text,
  injected jsonb not null default '[]'::jsonb,
  findings jsonb not null,
  worst text not null check (worst in ('none', 'info', 'low', 'medium', 'high')),
  counts jsonb not null default '{}'::jsonb,
  is_public boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists nd_reports_user_created on public.nd_reports (user_id, created_at desc);

alter table public.nd_reports enable row level security;

drop policy if exists "read own or public reports" on public.nd_reports;
create policy "read own or public reports" on public.nd_reports
  for select using (is_public or user_id = (select auth.uid()));

drop policy if exists "insert own reports" on public.nd_reports;
create policy "insert own reports" on public.nd_reports
  for insert to authenticated with check (user_id = (select auth.uid()));

drop policy if exists "update own reports" on public.nd_reports;
create policy "update own reports" on public.nd_reports
  for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists "delete own reports" on public.nd_reports;
create policy "delete own reports" on public.nd_reports
  for delete to authenticated using (user_id = (select auth.uid()));

-- Daily AI quota. No policies: the table is only reachable through the function below.
create table if not exists public.nd_usage (
  user_id uuid not null references auth.users (id) on delete cascade,
  day date not null default current_date,
  count integer not null default 0,
  primary key (user_id, day)
);
alter table public.nd_usage enable row level security;

create or replace function public.nd_take_quota()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  n integer;
begin
  if uid is null then
    return false;
  end if;
  insert into public.nd_usage (user_id, day, count)
  values (uid, current_date, 1)
  on conflict (user_id, day) do update set count = public.nd_usage.count + 1
  returning count into n;
  return n <= 20;
end;
$$;

revoke all on function public.nd_take_quota() from public, anon;
grant execute on function public.nd_take_quota() to authenticated;
