-- Row-level security and function tests. Each block asserts with RAISE.
\set ON_ERROR_STOP on
set client_min_messages = warning;

insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'teacher@example.com'),
  ('22222222-2222-2222-2222-222222222222', 'other@example.com');

-- helper: act as a role/user
create or replace function pg_temp.act(r text, uid text) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub', coalesce(uid, ''), false);
  execute format('set role %I', r);
end $$;

-- note-drift
select pg_temp.act('authenticated', '11111111-1111-1111-1111-111111111111');
insert into public.nd_reports (title, note, summary, findings, worst) values ('mine', 'n', 's', '[]', 'none');
insert into public.nd_reports (title, note, summary, findings, worst, is_public) values ('shared', 'n', 's', '[]', 'none', true);
do $$ declare i int; ok boolean; begin
  for i in 1..20 loop ok := public.nd_take_quota(); if not ok then raise exception 'quota denied early at %', i; end if; end loop;
  if public.nd_take_quota() then raise exception '21st call allowed'; end if;
end $$;
reset role;
select pg_temp.act('authenticated', '22222222-2222-2222-2222-222222222222');
do $$ begin
  if (select count(*) from public.nd_reports) <> 1 then raise exception 'other user should see only the public report'; end if;
  update public.nd_reports set title = 'hacked';
  delete from public.nd_reports;
  begin
    insert into public.nd_reports (user_id, title, note, summary, findings, worst) values ('11111111-1111-1111-1111-111111111111', 'spoof', 'n', 's', '[]', 'none');
    raise exception 'spoofed insert allowed';
  exception when insufficient_privilege then null; end;
  if (select count(*) from public.nd_usage) <> 0 then raise exception 'usage table readable'; end if;
  if not public.nd_take_quota() then raise exception 'second user quota should be separate'; end if;
end $$;
reset role;
do $$ begin
  if exists (select 1 from public.nd_reports where title = 'hacked') or (select count(*) from public.nd_reports) <> 2 then
    raise exception 'non-owner modified reports';
  end if;
end $$;
select pg_temp.act('anon', null);
do $$ begin
  if (select count(*) from public.nd_reports) <> 1 then raise exception 'anon should see only public'; end if;
  begin perform public.nd_take_quota(); raise exception 'anon can call quota';
  exception when insufficient_privilege then null; end;
end $$;
reset role;

select 'ALL RLS TESTS PASSED' as result;
