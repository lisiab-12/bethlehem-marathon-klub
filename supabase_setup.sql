-- Bethlehem Marathon Klub secure pilot schema (run once in Supabase SQL Editor).
-- IMPORTANT: This SQL does not import real members or create auth accounts.
-- Create users via Supabase Authentication > Users > Invite user; create profile
-- entries in SQL Editor only after identifying auth.users IDs.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check(length(trim(display_name)) between 1 and 160),
  member_number text,
  member_group text not null default 'ANDER' check (member_group in ('MANS','VROUE','ANDER')),
  age_category text,
  role text not null default 'member' check (role in ('member','committee','awards_admin','super_admin')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.race_results (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references public.profiles(id) on delete restrict,
  race_name text not null check (length(trim(race_name)) between 1 and 200),
  race_date date not null,
  discipline text not null check (discipline in ('Road','Trail','Cross-country','Track','Other')),
  distance_km numeric(7,2) not null check (distance_km > 0 and distance_km <= 1000),
  finish_seconds integer not null check (finish_seconds > 0),
  status text not null default 'Pending' check (status in ('Pending','Approved','Rejected')),
  reviewed_by uuid references public.profiles(id),
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists race_results_member_date_idx on public.race_results(member_id, race_date desc);
create index if not exists race_results_status_idx on public.race_results(status);

create table if not exists public.result_review_log (
  id bigint generated always as identity primary key,
  result_id uuid not null references public.race_results(id) on delete cascade,
  previous_status text not null,
  new_status text not null,
  reviewer_id uuid,
  changed_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.race_results enable row level security;
alter table public.result_review_log enable row level security;

-- The function runs as the database owner, so the profiles SELECT policy
-- can inspect committee roles without recursive policy evaluation.
create or replace function public.bmk_has_role(allowed text[])
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.active = true
      and p.role = any(allowed)
  );
$$;
revoke all on function public.bmk_has_role(text[]) from public, anon;
grant execute on function public.bmk_has_role(text[]) to authenticated;

revoke all on public.profiles, public.race_results, public.result_review_log from anon, authenticated;
grant select on public.profiles to authenticated;
grant select, insert on public.race_results to authenticated;
grant update (status, reviewed_by, reviewed_at) on public.race_results to authenticated;
grant select on public.result_review_log to authenticated;

create policy "profiles self or committee select" on public.profiles
 for select to authenticated
 using (id = (select auth.uid()) or (select public.bmk_has_role(array['committee','awards_admin','super_admin'])));

create policy "race own or committee select" on public.race_results
 for select to authenticated
 using (
   (member_id = (select auth.uid()) and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.active))
   or (select public.bmk_has_role(array['committee','awards_admin','super_admin']))
 );

create policy "member submits own pending" on public.race_results
 for insert to authenticated
 with check (
   member_id = (select auth.uid()) and status = 'Pending'
   and reviewed_by is null and reviewed_at is null
   and exists (select 1 from public.profiles p where p.id = (select auth.uid()) and p.active)
 );

create policy "committee reviews results" on public.race_results
 for update to authenticated
 using ((select public.bmk_has_role(array['committee','awards_admin','super_admin'])))
 with check (
   (select public.bmk_has_role(array['committee','awards_admin','super_admin']))
   and reviewed_by = (select auth.uid())
   and reviewed_at is not null
 );

create policy "committee reads review history" on public.result_review_log
 for select to authenticated
 using ((select public.bmk_has_role(array['committee','awards_admin','super_admin'])));

create or replace function public.bmk_review_audit()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
 if new.status is distinct from old.status then
   insert into public.result_review_log(result_id,previous_status,new_status,reviewer_id)
   values (new.id,old.status,new.status,(select auth.uid()));
 end if;
 return new;
end;
$$;
revoke all on function public.bmk_review_audit() from public, anon, authenticated;
drop trigger if exists trg_bmk_review_audit on public.race_results;
create trigger trg_bmk_review_audit after update of status on public.race_results
for each row execute function public.bmk_review_audit();

-- IMPORTANT: Create an invited auth user first, then insert a profile with
-- the exact UUID from Authentication > Users (using SQL Editor privileged role):
-- insert into public.profiles(id,display_name,member_group,role)
-- values ('REPLACE-WITH-REAL-AUTH-USER-UUID','Test Committee','ANDER','super_admin');
-- Do not create live club member records until privacy and permissions tests pass.
