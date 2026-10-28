-- Banco NegocioFacil Supabase - migration aplicada ao projeto tlqcpfmkneohjleiynqe.
create extension if not exists pgcrypto;
create table if not exists public.nf_businesses (
 id uuid primary key default gen_random_uuid(),
 owner_user_id uuid not null references auth.users(id) on delete cascade,
 name text not null check (length(trim(name)) between 1 and 120),
 created_at timestamptz not null default now()
);
create index if not exists nf_business_owner_idx on public.nf_businesses(owner_user_id);
alter table public.nf_businesses enable row level security;
create policy "nf_business_read_owner" on public.nf_businesses for select to authenticated using ((select auth.uid()) = owner_user_id);
create policy "nf_business_create_owner" on public.nf_businesses for insert to authenticated with check ((select auth.uid()) = owner_user_id);
create policy "nf_business_update_owner" on public.nf_businesses for update to authenticated using ((select auth.uid()) = owner_user_id) with check ((select auth.uid()) = owner_user_id);

create table if not exists public.nf_mp_oauth_states (
 state_hash text primary key check (state_hash ~ '^[0-9a-f]{64}$'),
 business_id uuid not null references public.nf_businesses(id) on delete cascade,
 code_verifier text,
 expires_at timestamptz not null,
 created_at timestamptz not null default now()
);
create index if not exists nf_mp_oauth_states_expiry_idx on public.nf_mp_oauth_states(expires_at);
alter table public.nf_mp_oauth_states enable row level security;

create table if not exists public.nf_mp_connections (
 business_id uuid primary key references public.nf_businesses(id) on delete cascade,
 mp_user_id text not null,
 access_token_enc text not null,
 refresh_token_enc text,
 expires_at timestamptz,
 connected_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists nf_mp_connections_user_idx on public.nf_mp_connections(mp_user_id);
alter table public.nf_mp_connections enable row level security;
revoke all on table public.nf_mp_oauth_states, public.nf_mp_connections from anon, authenticated;
grant all on table public.nf_mp_oauth_states, public.nf_mp_connections to service_role;
grant select, insert, update on table public.nf_businesses to authenticated;
revoke all on table public.nf_businesses from anon;
