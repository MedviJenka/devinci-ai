create table if not exists public.api_keys (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    key_hash text not null unique,
    key_prefix text not null,
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    revoked_at timestamptz
);

create index if not exists api_keys_user_id_idx on public.api_keys(user_id);

-- Only the backend's service-role client ever touches this table (see
-- core/database/api_keys/client.py) - RLS stays enabled with no policies so
-- an anon/authenticated-role request (e.g. a leaked frontend key) can't read
-- or enumerate key hashes directly through PostgREST.
alter table public.api_keys enable row level security;
