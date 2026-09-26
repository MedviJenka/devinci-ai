create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    subscription text not null default 'Free',
    api_calls integer not null default 0,
    characters integer not null default 0
);

-- auth is handled entirely by Supabase (email OTP / Google OAuth) on the
-- frontend, so there is no backend signup step to hang row creation off of.
-- Provision the public.users row here instead, right when Supabase creates
-- the auth.users row.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.users (id)
    values (new.id)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
