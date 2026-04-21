create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  email text,
  specialty text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do update
    set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create table if not exists public.palaces (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  title text not null,
  topic text not null,
  source_name text,
  scene_title text,
  status text not null default 'draft',
  latest_version_number integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.palace_versions (
  id uuid primary key default gen_random_uuid(),
  palace_id uuid not null references public.palaces (id) on delete cascade,
  version_number integer not null,
  generation_inputs jsonb not null default '{}'::jsonb,
  generation_outputs jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (palace_id, version_number)
);

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete set null,
  provider text not null default 'anthropic',
  model text,
  request_id text,
  input_tokens integer,
  output_tokens integer,
  status_code integer,
  created_at timestamptz not null default now()
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  provider text not null default 'stripe',
  provider_customer_id text,
  provider_subscription_id text,
  plan_code text not null default 'free',
  status text not null default 'inactive',
  current_period_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.palaces enable row level security;
alter table public.palace_versions enable row level security;
alter table public.usage_events enable row level security;
alter table public.subscriptions enable row level security;

create policy "profiles_select_own"
on public.profiles
for select
using (auth.uid() = id);

create policy "profiles_insert_own"
on public.profiles
for insert
with check (auth.uid() = id);

create policy "profiles_update_own"
on public.profiles
for update
using (auth.uid() = id);

create policy "palaces_select_own"
on public.palaces
for select
using (auth.uid() = user_id);

create policy "palaces_insert_own"
on public.palaces
for insert
with check (auth.uid() = user_id);

create policy "palaces_update_own"
on public.palaces
for update
using (auth.uid() = user_id);

create policy "palace_versions_select_own"
on public.palace_versions
for select
using (
  exists (
    select 1
    from public.palaces
    where public.palaces.id = palace_versions.palace_id
      and public.palaces.user_id = auth.uid()
  )
);

create policy "palace_versions_insert_own"
on public.palace_versions
for insert
with check (
  exists (
    select 1
    from public.palaces
    where public.palaces.id = palace_versions.palace_id
      and public.palaces.user_id = auth.uid()
  )
);

create policy "usage_events_select_own"
on public.usage_events
for select
using (auth.uid() = user_id);

create policy "usage_events_insert_own"
on public.usage_events
for insert
with check (auth.uid() = user_id);

create policy "palaces_delete_own"
on public.palaces
for delete
using (auth.uid() = user_id);

create policy "palace_versions_delete_own"
on public.palace_versions
for delete
using (
  exists (
    select 1
    from public.palaces
    where public.palaces.id = palace_versions.palace_id
      and public.palaces.user_id = auth.uid()
  )
);

create policy "subscriptions_select_own"
on public.subscriptions
for select
using (auth.uid() = user_id);

-- Indexes on foreign keys (RLS policies query these on every request)
create index if not exists idx_palaces_user_id on public.palaces (user_id);
create index if not exists idx_palace_versions_palace_id on public.palace_versions (palace_id);
create index if not exists idx_usage_events_user_id on public.usage_events (user_id);

-- Auto-update updated_at on palaces
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists palaces_set_updated_at on public.palaces;
create trigger palaces_set_updated_at
before update on public.palaces
for each row execute procedure public.set_updated_at();
