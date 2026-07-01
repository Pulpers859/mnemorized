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

revoke execute on function public.handle_new_user() from public, anon, authenticated;

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
using ((select auth.uid()) = id);

create policy "profiles_insert_own"
on public.profiles
for insert
with check ((select auth.uid()) = id);

create policy "profiles_update_own"
on public.profiles
for update
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

create policy "palaces_select_own"
on public.palaces
for select
using ((select auth.uid()) = user_id);

create policy "palaces_insert_own"
on public.palaces
for insert
with check ((select auth.uid()) = user_id);

create policy "palaces_update_own"
on public.palaces
for update
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "palace_versions_select_own"
on public.palace_versions
for select
using (
  exists (
    select 1
    from public.palaces
    where public.palaces.id = palace_versions.palace_id
      and public.palaces.user_id = (select auth.uid())
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
      and public.palaces.user_id = (select auth.uid())
  )
);

create policy "usage_events_select_own"
on public.usage_events
for select
using ((select auth.uid()) = user_id);

create policy "usage_events_insert_own"
on public.usage_events
for insert
with check ((select auth.uid()) = user_id);

create policy "palaces_delete_own"
on public.palaces
for delete
using ((select auth.uid()) = user_id);

create policy "palace_versions_delete_own"
on public.palace_versions
for delete
using (
  exists (
    select 1
    from public.palaces
    where public.palaces.id = palace_versions.palace_id
      and public.palaces.user_id = (select auth.uid())
  )
);

create policy "subscriptions_select_own"
on public.subscriptions
for select
using ((select auth.uid()) = user_id);

-- Indexes on foreign keys (RLS policies query these on every request)
create index if not exists idx_palaces_user_id on public.palaces (user_id);
create index if not exists idx_palace_versions_palace_id on public.palace_versions (palace_id);
create index if not exists idx_usage_events_user_id on public.usage_events (user_id);

-- ── Shared palace catalog (public read, admin write) ──

create table if not exists public.catalog_palaces (
  id                 uuid primary key default gen_random_uuid(),
  title              text not null,
  topic              text not null,
  source_name        text,
  scene_title        text,
  tags               text[] not null default '{}',
  generation_inputs  jsonb not null default '{}'::jsonb,
  generation_outputs jsonb not null default '{}'::jsonb,
  published_by       uuid references public.profiles (id) on delete set null,
  published_at       timestamptz not null default now()
);

alter table public.catalog_palaces enable row level security;

revoke all on public.catalog_palaces from anon, authenticated;
grant select on public.catalog_palaces to anon, authenticated;

create policy "catalog_select_public"
on public.catalog_palaces
for select
to anon, authenticated
using (true);

create index if not exists idx_catalog_palaces_published_at
  on public.catalog_palaces (published_at desc);
create index if not exists idx_catalog_palaces_published_by
  on public.catalog_palaces (published_by);

-- Auto-update updated_at on palaces
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke execute on function public.set_updated_at() from public, anon, authenticated;

drop trigger if exists palaces_set_updated_at on public.palaces;
create trigger palaces_set_updated_at
before update on public.palaces
for each row execute procedure public.set_updated_at();

-- ── Private medical knowledge base (backend service-role only) ──

create extension if not exists vector with schema extensions;

create schema if not exists medical;

revoke all on schema medical from public, anon, authenticated;
grant usage on schema medical to service_role;

create table if not exists medical.medical_sources (
  id          uuid primary key default gen_random_uuid(),
  source_key  text not null unique,
  title       text not null,
  source_path text,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists medical.medical_knowledge_chunks (
  id             uuid primary key default gen_random_uuid(),
  source_id      uuid not null references medical.medical_sources (id) on delete cascade,
  chunk_index    integer not null,
  page_start     integer,
  page_end       integer,
  section_title  text,
  chunk_text     text not null,
  token_estimate integer not null default 0,
  embedding      vector(1536) not null,
  metadata       jsonb not null default '{}'::jsonb,
  content_tsv    tsvector generated always as (
    to_tsvector('english', coalesce(section_title, '') || ' ' || chunk_text)
  ) stored,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (source_id, chunk_index)
);

alter table medical.medical_sources enable row level security;
alter table medical.medical_knowledge_chunks enable row level security;

create policy "medical_sources_no_browser_access"
on medical.medical_sources
for all
to anon, authenticated
using (false)
with check (false);

create policy "medical_chunks_no_browser_access"
on medical.medical_knowledge_chunks
for all
to anon, authenticated
using (false)
with check (false);

revoke all on medical.medical_sources from public, anon, authenticated;
revoke all on medical.medical_knowledge_chunks from public, anon, authenticated;
grant select, insert, update, delete on medical.medical_sources to service_role;
grant select, insert, update, delete on medical.medical_knowledge_chunks to service_role;

create index if not exists idx_medical_chunks_source_id
  on medical.medical_knowledge_chunks (source_id);
create index if not exists idx_medical_chunks_tsv
  on medical.medical_knowledge_chunks using gin (content_tsv);
create index if not exists idx_medical_chunks_embedding_hnsw
  on medical.medical_knowledge_chunks using hnsw (embedding vector_cosine_ops);

create or replace function public.upsert_medical_source(
  p_source_key text,
  p_title text,
  p_source_path text default null,
  p_metadata jsonb default '{}'::jsonb
) returns uuid
language plpgsql
security definer
set search_path = medical, public, extensions
as $$
declare
  v_source_id uuid;
begin
  insert into medical.medical_sources (source_key, title, source_path, metadata, updated_at)
  values (p_source_key, p_title, p_source_path, coalesce(p_metadata, '{}'::jsonb), now())
  on conflict (source_key) do update
    set title = excluded.title,
        source_path = excluded.source_path,
        metadata = excluded.metadata,
        updated_at = now()
  returning id into v_source_id;

  return v_source_id;
end;
$$;

create or replace function public.upsert_medical_knowledge_chunk(
  p_source_key text,
  p_chunk_index integer,
  p_page_start integer,
  p_page_end integer,
  p_section_title text,
  p_chunk_text text,
  p_token_estimate integer,
  p_embedding text,
  p_metadata jsonb default '{}'::jsonb
) returns uuid
language plpgsql
security definer
set search_path = medical, public, extensions
as $$
declare
  v_source_id uuid;
  v_chunk_id uuid;
begin
  select id into v_source_id
  from medical.medical_sources
  where source_key = p_source_key;

  if v_source_id is null then
    raise exception 'medical source % does not exist', p_source_key;
  end if;

  insert into medical.medical_knowledge_chunks (
    source_id,
    chunk_index,
    page_start,
    page_end,
    section_title,
    chunk_text,
    token_estimate,
    embedding,
    metadata,
    updated_at
  )
  values (
    v_source_id,
    p_chunk_index,
    p_page_start,
    p_page_end,
    p_section_title,
    p_chunk_text,
    coalesce(p_token_estimate, 0),
    p_embedding::vector,
    coalesce(p_metadata, '{}'::jsonb),
    now()
  )
  on conflict (source_id, chunk_index) do update
    set page_start = excluded.page_start,
        page_end = excluded.page_end,
        section_title = excluded.section_title,
        chunk_text = excluded.chunk_text,
        token_estimate = excluded.token_estimate,
        embedding = excluded.embedding,
        metadata = excluded.metadata,
        updated_at = now()
  returning id into v_chunk_id;

  return v_chunk_id;
end;
$$;

create or replace function public.match_medical_knowledge_chunks(
  p_query_embedding text,
  p_query_text text default '',
  p_match_count integer default 8,
  p_min_similarity double precision default 0.15
) returns table (
  chunk_id uuid,
  source_key text,
  title text,
  page_start integer,
  page_end integer,
  section_title text,
  chunk_text text,
  similarity double precision,
  keyword_rank double precision
)
language sql
stable
security definer
set search_path = medical, public, extensions
as $$
  with query_input as (
    select
      nullif(p_query_embedding, '')::vector as embedding,
      websearch_to_tsquery('english', coalesce(p_query_text, '')) as tsq
  )
  select
    chunks.id as chunk_id,
    sources.source_key,
    sources.title,
    chunks.page_start,
    chunks.page_end,
    chunks.section_title,
    chunks.chunk_text,
    case
      when query_input.embedding is null then 0
      else 1 - (chunks.embedding <=> query_input.embedding)
    end as similarity,
    case
      when coalesce(trim(p_query_text), '') = '' then 0
      else ts_rank(chunks.content_tsv, query_input.tsq)
    end as keyword_rank
  from medical.medical_knowledge_chunks as chunks
  join medical.medical_sources as sources on sources.id = chunks.source_id
  cross join query_input
  where (
      query_input.embedding is not null
      and 1 - (chunks.embedding <=> query_input.embedding) >= coalesce(p_min_similarity, 0)
    )
    or (
      coalesce(trim(p_query_text), '') <> ''
      and chunks.content_tsv @@ query_input.tsq
    )
  order by
    case
      when query_input.embedding is null then 1
      else chunks.embedding <=> query_input.embedding
    end asc,
    keyword_rank desc,
    chunks.chunk_index asc
  limit greatest(1, least(coalesce(p_match_count, 8), 20));
$$;

revoke execute on function public.upsert_medical_source(text, text, text, jsonb)
  from public, anon, authenticated;
revoke execute on function public.upsert_medical_knowledge_chunk(
  text, integer, integer, integer, text, text, integer, text, jsonb
) from public, anon, authenticated;
revoke execute on function public.match_medical_knowledge_chunks(text, text, integer, double precision)
  from public, anon, authenticated;

grant execute on function public.upsert_medical_source(text, text, text, jsonb)
  to service_role;
grant execute on function public.upsert_medical_knowledge_chunk(
  text, integer, integer, integer, text, text, integer, text, jsonb
) to service_role;
grant execute on function public.match_medical_knowledge_chunks(text, text, integer, double precision)
  to service_role;
